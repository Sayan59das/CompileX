"""
AI Question Generator Service - Dynamic Version
Uses dynamic_generator.py which requires no ML dependencies (torch-free)
Perfect for deployment on free-tier services like Render

FEATURES:
- Avoids repeats per user: callers pass the user's history as exclude_titles
- Picks randomly among questions not excluded, falling back through generators
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import random
import uvicorn

# Import generators — question_db first, then smart AI, dataset, dynamic templates as fallback
from model.dynamic_generator import generate_dynamic, NoFreshQuestion
from model.titles import normalize_title
from model.dataset_generator import (
    get_from_dataset, dataset_stats, pool_size as dataset_pool_size, clear_cache as clear_dataset_cache,
)
from model.smart_generator import generate_smart, pool_size as smart_pool_size, clear_cache as clear_smart_cache
from model.question_db import get_question as db_get_question, get_stats as db_get_stats, pool_size as db_pool_size
from model.reviewed_bank import (
    get_question as reviewed_get_question, get_stats as reviewed_stats, pool_size as reviewed_pool_size,
)

# Try to load the trained model generator
_trained_generator = None
try:
    from model.generator import get_generator
    _trained_generator = get_generator()
    if _trained_generator.is_model_loaded:
        print("[Service] Trained model loaded — available as fallback")
    else:
        print("[Service] Trained model not available — using smart AI + dataset + dynamic")
except Exception as e:
    print(f"[Service] Could not load trained generator: {e}")

app = FastAPI(
    title="Coding Question AI",
    description="AI-powered coding question generator with guaranteed uniqueness",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Repeat avoidance is per user: the backend sends each user's history as
# exclude_titles. Nothing is remembered across requests here, otherwise one
# user's questions would be withheld from everyone else.
_max_retries = 5  # Reduced from 50 — question_db/smart_generator hit on first try


# -----------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------

class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=100)
    difficulty: Optional[str] = Field("medium")
    num_test_cases: Optional[int] = Field(6, ge=1, le=20)
    exclude_titles: Optional[List[str]] = Field(default_factory=list)  # titles to avoid


class TestCase(BaseModel):
    input: str
    output: str


class QuestionResponse(BaseModel):
    title: str
    base_title: str
    problem_statement: str
    input_format: str
    output_format: str
    sample_input: str
    sample_output: str
    test_cases: List[TestCase]
    topic: str
    difficulty: str
    source: str


# -----------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------

@app.get("/")
async def root():
    stats = dataset_stats()
    return {
        "message": "Coding Question AI Service",
        "status": "running",
        "version": "3.0.0",
        "generator": "dataset-first + dynamic fallback",
        "dataset_questions": stats["total_questions"],
        "dataset_topics": list(stats["topics"].keys()),
    }


@app.get("/health")
async def health():
    stats = dataset_stats()
    return {
        "status": "healthy",
        "generator": "dataset + dynamic",
        "dataset_loaded": stats["total_questions"] > 0,
        "dataset_questions": stats["total_questions"],
    }


@app.get("/stats")
async def stats():
    ds = dataset_stats()
    return {
        "dataset_questions": ds["total_questions"],
        "dataset_topics": ds["topics"],
        "reviewed_questions": sum(sum(by_difficulty.values()) for by_difficulty in reviewed_stats().values()),
        "deduplication": "per-user, via exclude_titles",
    }


@app.post("/clear_cache")
async def clear_cache():
    clear_dataset_cache()
    clear_smart_cache()
    return {"message": "All caches cleared"}


@app.get("/topics")
async def get_topics():
    """Return all available topics with question counts."""
    import model.smart_generator as sg
    import model.dataset_generator as dg
    sg._load_questions()
    dg._load()

    # Merge smart + dataset topics
    all_topics = set()
    if sg._by_topic:
        all_topics.update(sg._by_topic.keys())
    if dg._dataset_by_topic:
        all_topics.update(dg._dataset_by_topic.keys())

    # Always include the core DSA topics even if not in dataset
    core = [
        "arrays", "strings", "graphs", "trees", "dynamic programming",
        "sorting", "hashing", "stacks", "queues", "greedy",
        "backtracking", "recursion", "linked lists", "searching",
        "bit manipulation", "math", "two pointers", "sliding window",
    ]
    for t in core:
        all_topics.add(t)

    # Build response with counts
    topic_list = []
    for t in sorted(all_topics):
        smart_count = len(sg._by_topic.get(t, [])) if sg._by_topic else 0
        ds_count    = len(dg._dataset_by_topic.get(t, [])) if dg._dataset_by_topic else 0
        topic_list.append({
            "topic": t,
            "total": smart_count + ds_count,
        })

    return {
        "topics": [t["topic"] for t in topic_list],
        "details": topic_list,
    }


def _bank_order(topic: str, difficulty: str) -> List[str]:
    """Banks holding this topic and difficulty, in random order weighted by pool size.

    Empty banks are skipped: they would answer with a different difficulty.
    """
    pools = {
        "question_db": db_pool_size(topic, difficulty),
        "smart": smart_pool_size(topic, difficulty),
        "dataset": dataset_pool_size(topic, difficulty),
    }
    remaining = [name for name, size in pools.items() if size > 0]
    # Reviewed questions are verified end to end and ship with real starter code, so they are tried first.
    order: List[str] = ["reviewed"] if reviewed_pool_size(topic, difficulty) > 0 else []
    while remaining:
        pick = random.choices(remaining, weights=[pools[n] for n in remaining])[0]
        order.append(pick)
        remaining.remove(pick)
    return order


@app.post("/generate")
def generate_question(req: GenerateRequest):
    """
    Generate a unique coding question using dynamic templates.
    Guarantees that the same question is never generated twice.
    """
    import time
    request_start = time.time()
    
    difficulty = req.difficulty.lower() if req.difficulty else "medium"
    if difficulty not in ("easy", "medium", "hard"):
        raise HTTPException(
            status_code=400, 
            detail="difficulty must be 'easy', 'medium', or 'hard'"
        )

    topic = req.topic.strip().lower()
    
    # Try to generate a unique question (with retries)
    attempts = 0
    result = None
    accepted = False
    exhausted = False
    client_exclude = set(normalize_title(t) for t in (req.exclude_titles or []))
    exclude_list = list(client_exclude)

    while attempts < _max_retries:
        attempts += 1

        try:
            gen_start = time.time()
            candidate = None

            # Question banks, in a random order weighted by how many questions each
            # holds for this topic and difficulty, so a small bank is not served
            # to everyone before the large ones are touched.
            for bank in _bank_order(topic, difficulty):
                if bank == "reviewed":
                    candidate = reviewed_get_question(topic=topic, difficulty=difficulty, exclude_titles=exclude_list)
                elif bank == "question_db":
                    candidate = db_get_question(topic=topic, difficulty=difficulty, exclude_titles=exclude_list)
                    if candidate:
                        candidate.setdefault("source", "question_db")
                elif bank == "smart":
                    candidate = generate_smart(
                        topic=topic,
                        difficulty=difficulty,
                        exclude_titles=exclude_list,
                        num_test_cases=req.num_test_cases or 6,
                    )
                else:
                    candidate = get_from_dataset(
                        topic=topic,
                        difficulty=difficulty,
                        exclude_titles=exclude_list,
                        num_test_cases=req.num_test_cases or 6,
                    )
                if candidate:
                    print(f"[API] {bank}: '{candidate['title']}' [{difficulty}]")
                    break

            # Trained model (if every bank is exhausted for this user)
            if candidate is None and _trained_generator and _trained_generator.is_model_loaded and attempts <= 3:
                try:
                    candidate = _trained_generator.generate(topic, difficulty)
                    if (
                        candidate
                        and candidate.get("title", "").strip()
                        and len(candidate.get("problem_statement", "")) > 50
                        and candidate.get("source") not in ("error_fallback",)
                    ):
                        print(f"[API] Trained model: '{candidate['title']}'")
                    else:
                        candidate = None
                except Exception as e:
                    print(f"[API] Trained model failed: {e}")
                    candidate = None

            # Template generator: each template is one real problem, and a player gets each at most once
            if candidate is None:
                try:
                    candidate = generate_dynamic(
                        topic, difficulty,
                        exclude_titles=exclude_list,
                    )
                except NoFreshQuestion:
                    exhausted = True
                    break
                print(f"[API] Dynamic template: '{candidate['title']}'")

            gen_time = time.time() - gen_start
            result = candidate

            # Reject anything the caller excluded (generators such as the trained
            # model or templates may ignore exclude_titles)
            title = result["title"]
            identities = {normalize_title(title), normalize_title(result.get("base_title") or title)}

            if not identities & client_exclude:
                accepted = True
                source = result.get("source", "unknown")
                print(f"[API] ✓ '{title}' [{source}] in {gen_time:.3f}s (attempt {attempts})")
                break
            print(f"[API] ✗ Rejected '{title}' (excluded by caller), retrying... (attempt {attempts})")

        except Exception as e:
            print(f"[API] Error in attempt {attempts}: {e}")
            if attempts >= _max_retries:
                raise

    if exhausted:
        # Not an error: this player has had every question we hold for this topic and difficulty.
        # The caller decides what to do (the backend falls back to its own pool).
        raise HTTPException(
            status_code=404,
            detail=f"No unseen {difficulty} {topic} question is left for this player"
        )

    if not accepted:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate a question outside the exclusion list after {_max_retries} attempts"
        )

    try:
        
        # Convert test cases to proper format
        def _to_stdin(val) -> str:
            """Convert any value to plain-text stdin string."""
            if isinstance(val, str):
                return val
            if isinstance(val, bool):
                return str(val).lower()
            if isinstance(val, (int, float)):
                return str(val)
            if isinstance(val, (list, tuple)):
                # flat list/tuple of scalars → space-separated
                if all(isinstance(x, (int, float, str, bool)) for x in val):
                    return " ".join(str(x) for x in val)
                # list of pairs (edges) → one "u v" per line
                if all(isinstance(x, (list, tuple)) and len(x) >= 2 for x in val):
                    return "\n".join(" ".join(str(e) for e in pair) for pair in val)
                # nested list → one row per line
                return "\n".join(_to_stdin(row) for row in val)
            if isinstance(val, dict):
                # Special handling for graph inputs: {"nodes": n, "edges": [...], "src": s, "dst": d}
                # and weighted graphs: {"nodes": n, "edges": [(u,v,w),...], "src": s}
                if "edges" in val and "nodes" in val:
                    edges = val["edges"]
                    n_nodes = val["nodes"]
                    n_edges = len(edges)
                    # Format edges as "u v" or "u v w" per line
                    edge_lines = "\n".join(" ".join(str(e) for e in edge) for edge in edges)
                    # Check for src/dst (BFS) or just src (Dijkstra)
                    if "src" in val and "dst" in val:
                        return f"{n_nodes} {n_edges}\n{edge_lines}\n{val['src']} {val['dst']}"
                    elif "src" in val:
                        header = f"{n_nodes} {n_edges} {val['src']}"
                        return f"{header}\n{edge_lines}" if edge_lines else header
                    else:
                        return f"{n_nodes} {n_edges}\n{edge_lines}" if edge_lines else f"{n_nodes} {n_edges}"
                # Generic dict → one value per line
                lines = []
                for v in val.values():
                    lines.append(_to_stdin(v))
                return "\n".join(lines)
            return str(val)

        def _to_stdout(val) -> str:
            """Convert output value to expected stdout string."""
            if isinstance(val, str):
                return val
            if isinstance(val, bool):
                return str(val).lower()
            if isinstance(val, (int, float)):
                return str(val)
            if isinstance(val, list):
                if all(isinstance(x, (int, float, str, bool)) for x in val):
                    return " ".join(str(x) for x in val)
                return "\n".join(_to_stdout(row) for row in val)
            return str(val)

        # Format test cases
        formatted_tcs = []
        for tc in result.get("test_cases", []):
            formatted_tcs.append({
                "input": _to_stdin(tc["input"]),
                "output": _to_stdout(tc["output"])
            })

        response = {
            "title": result["title"],
            "base_title": result.get("base_title") or result["title"],
            "problem_statement": result["problem_statement"],
            "input_format": result["input_format"],
            "output_format": result["output_format"],
            "sample_input": _to_stdin(result["sample_input"]),
            "sample_output": _to_stdout(result["sample_output"]),
            "test_cases": formatted_tcs,
            "topic": result.get("topic", topic),
            "difficulty": difficulty,
            "source": "dynamic"
        }
        # Reviewed questions carry a real signature and starter code; everything else keeps the old response.
        if result.get("starter_code"):
            for key in ("constraints", "function_name", "parameters", "return_type", "return_description",
                        "starter_code", "input_schema", "output_schema"):
                if result.get(key):
                    response[key] = result[key]

        total_time = time.time() - request_start
        print(f"[API] Total request time: {total_time:.3f}s")
        
        return response
        
    except Exception as e:
        print(f"[API] Error generating question: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate question: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
