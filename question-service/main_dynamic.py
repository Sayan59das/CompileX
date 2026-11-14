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
from model.dynamic_generator import generate_dynamic, has_topic, NoFreshQuestion
from model.titles import normalize_title
from model.legacy_typing import type_question
from model.quality import served_formats
from model.stdio import to_stdin as _to_stdin, to_stdout as _to_stdout
from model.scaffold import served_starter
from pool.api import build_router
from pool.history import MemorySeenStore, RedisSeenStore
from pool.repository import SqlRepository
from pool.service import NoQuestion, QuestionService, ReviewedBank
import os
from model.dataset_generator import (
    get_from_dataset, dataset_stats, pool_size as dataset_pool_size, clear_cache as clear_dataset_cache,
)
from model.smart_generator import generate_smart, pool_size as smart_pool_size, clear_cache as clear_smart_cache
from model.question_db import get_question as db_get_question, get_stats as db_get_stats, pool_size as db_pool_size
from model.reviewed_bank import (
    get_question as reviewed_get_question, get_stats as reviewed_stats, pool_size as reviewed_pool_size,
)

# The old transformer is retired from the serving path: no language model and no torch runs here. New questions are
# written offline by qgen/worker.py and served from the pool (pool/service.py).

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
_MAX_UNTYPED_SKIPS = 80  # questions skipped for lack of a verified starter in one request, before it gives up
_max_retries = 5  # Reduced from 50 — question_db/smart_generator hit on first try


# -----------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------

class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=100)
    difficulty: Optional[str] = Field("medium")
    num_test_cases: Optional[int] = Field(6, ge=1, le=20)
    exclude_titles: Optional[List[str]] = Field(default_factory=list)  # titles to avoid
    player_ids: Optional[List[str]] = None  # when given, the pool also remembers what these players were served (Redis history)
    skip_pool: bool = False  # internal: the legacy fallback of the pool must not ask the pool again


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


def _typed_fields(result: dict) -> Optional[dict]:
    """What a question needs so the editor can lock everything except the function body.

    A question that already carries its own starter code has what it needs ({}). An older-bank question gets a starter
    worked out from its own stored tests and checked against all of them; None when that cannot be done, and such a
    question is not served (see model/legacy_typing.py)."""
    if result.get("starter_code"):
        return {}
    try:
        tests = [(_to_stdin(tc["input"]), _to_stdout(tc["output"])) for tc in result.get("test_cases", [])]
        return type_question(tests, _to_stdin(result["sample_input"]), _to_stdout(result["sample_output"]),
                             input_format=str(result.get("input_format") or ""))
    except (KeyError, TypeError):
        return None


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
    typed = None
    templates_used_up = False
    served_from = "unknown"
    untyped_skipped = 0
    client_exclude = set(normalize_title(t) for t in (req.exclude_titles or []))
    exclude_list = list(client_exclude)

    # Pool first (live generated questions, then the reviewed bank). It never repeats: when it has nothing unseen,
    # the older banks below are tried exactly as before.
    if _pool_service is not None and not req.skip_pool:
        try:
            pooled = _pool_service.generate(topic, difficulty, req.player_ids or [], req.exclude_titles or [])
            print(f"[API] pool: '{pooled['title']}' [{difficulty}] ({pooled['source']})")
            return pooled
        except NoQuestion:
            pass

    while attempts < _max_retries:
        attempts += 1

        try:
            gen_start = time.time()
            candidate = None

            # Best first. 1: reviewed questions (read by a person, two solutions agree on every test). 2: templates (the tests
            # and their answers are computed by the template's own solver, and a player gets each problem at most once).
            # 3: the collected contest banks, which nobody has read: they are typed from their tests and filtered by
            # model/quality.py, but a statement there can still be unclear, so they come last. Among those banks the order is
            # random, weighted by how many questions each holds, so a small bank is not used up for everyone first.
            # For a topic the templates do not know they would answer with a random topic, so there they stay the last resort.
            order = _bank_order(topic, difficulty)
            collected = [b for b in order if b != "reviewed"]
            templates = [] if templates_used_up else ["templates"]
            rest = templates + collected if has_topic(topic) else collected + templates
            for bank in [b for b in order if b == "reviewed"] + rest:
                if bank == "reviewed":
                    candidate = reviewed_get_question(topic=topic, difficulty=difficulty, exclude_titles=exclude_list)
                elif bank == "templates":
                    try:
                        candidate = generate_dynamic(topic, difficulty, exclude_titles=exclude_list)
                    except NoFreshQuestion:
                        templates_used_up = True   # this player has had every template of this topic and difficulty
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
                    served_from = bank
                    break

            if candidate is None:
                exhausted = True
                break

            gen_time = time.time() - gen_start
            result = candidate

            # Reject anything the caller excluded (generators such as the trained
            # model or templates may ignore exclude_titles)
            title = result["title"]
            identities = {normalize_title(title), normalize_title(result.get("base_title") or title)}

            if not identities & client_exclude:
                typed = _typed_fields(result)
                if typed is not None:
                    accepted = True
                    source = result.get("source", "unknown")
                    print(f"[API] ✓ '{title}' [{source}] in {gen_time:.3f}s (attempt {attempts})")
                    break
                # Verified only: the editor locks everything but the function body, so a question whose reader cannot be
                # derived from its own tests and checked against all of them is not served. It is skipped without using
                # up a retry and not offered again by this request.
                untyped_skipped += 1
                exclude_list.extend(identities)
                print(f"[API] ✗ Skipped '{title}': no verified starter code (skipped {untyped_skipped})")
                if untyped_skipped < _MAX_UNTYPED_SKIPS:
                    attempts -= 1
                continue
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
            "source": f"dynamic-{served_from}",   # which source it came from: reviewed, templates, question_db, smart or dataset
        }
        # Reviewed questions carry a real signature and starter code (a C entry is added when they predate C); an
        # older-bank question gets the ones worked out from its own tests by _typed_fields.
        if result.get("starter_code"):
            for key in ("constraints", "function_name", "parameters", "return_type", "return_description",
                        "starter_code", "input_schema", "output_schema"):
                if result.get(key):
                    response[key] = result[key]
            response["starter_code"] = served_starter(response)
        elif typed:
            response.update(typed)
            # typing describes how the values arrive; a contest statement's own Input and Output sections say what they mean
            response["input_format"], response["output_format"] = served_formats(
                result["problem_statement"], typed["input_format"], typed["output_format"],
                str(result.get("input_format") or ""), str(result.get("output_format") or ""))

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


def _legacy_question(topic, difficulty, blocked_title_keys):
    """The older banks and templates, for a topic that has no pool or reviewed questions at all (None when they have nothing unseen)."""
    try:
        return generate_question(GenerateRequest(topic=topic, difficulty=difficulty, exclude_titles=list(blocked_title_keys), skip_pool=True))
    except HTTPException:
        return None


def _build_pool_service():
    """The pool service from the environment: POOL_DATABASE_URL (PostgreSQL url or SQLite path; default data/pool.db when that
    file exists, otherwise an empty in-memory pool, so the reviewed bank and the legacy generators still serve), REDIS_URL for
    per-player history (default: in this process only), SEEN_TTL_SECONDS for how long history is kept."""
    url = os.environ.get("POOL_DATABASE_URL")
    default_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "pool.db")
    if not url:
        url = default_db if os.path.exists(default_db) else ":memory:"
    ttl = int(os.environ.get("SEEN_TTL_SECONDS", 30 * 24 * 3600))
    redis_url = os.environ.get("REDIS_URL")
    seen = RedisSeenStore.from_url(redis_url, ttl) if redis_url else MemorySeenStore(ttl)
    service = QuestionService(SqlRepository.from_url(url), seen, ReviewedBank(), legacy=_legacy_question)
    print(f"[Service] pool database: {url if '@' not in url else 'postgres'}; history: {'redis' if redis_url else 'memory'}")
    return service


_pool_service = _build_pool_service()
app.include_router(build_router(_pool_service, os.environ.get("INTERNAL_TOKEN")))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
