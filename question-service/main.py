from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import uvicorn

from model.generator import get_generator
from model.debugger_generator import get_debugger
from model.smart_debugger import smart_debug_hint

app = FastAPI(
    title="Coding Question AI",
    description="AI-powered coding question generator. Provide a topic and get a full competitive-programming-style problem.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------

class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=100, json_schema_extra={"example": "arrays"})
    difficulty: Optional[str] = Field("medium", json_schema_extra={"example": "medium"})
    exclude_titles: Optional[List[str]] = Field(default_factory=list)


class TestCase(BaseModel):
    input: str
    output: str


class QuestionResponse(BaseModel):
    title: str
    problem_statement: str
    input_format: str
    output_format: str
    sample_input: str
    sample_output: str
    test_cases: List[TestCase]
    topic: str
    difficulty: str
    source: str  # "model" or "template"


class StatusResponse(BaseModel):
    status: str
    model_loaded: bool
    message: str


# ── Debugger schemas ────────────────────────────────────────────────────────

class DebugHintRequest(BaseModel):
    problem_statement: str = Field(..., min_length=1)
    user_code: str = Field(..., min_length=1)
    language: str = Field(..., json_schema_extra={"example": "python"})
    failed_test_input: str = Field(default="")
    expected_output: str = Field(default="")
    actual_output: str = Field(default="")


class DebugHintResponse(BaseModel):
    status: str
    line: str
    message: str
    hint: str


# -----------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------

@app.get("/", response_model=StatusResponse)
def root():
    gen = get_generator()
    return StatusResponse(
        status="ok",
        model_loaded=gen.is_model_loaded,
        message=(
            "Trained model is active." if gen.is_model_loaded
            else "Using rule-based fallback. Train the model to enable AI generation."
        ),
    )


@app.get("/status", response_model=StatusResponse)
def status():
    gen = get_generator()
    return StatusResponse(
        status="ok",
        model_loaded=gen.is_model_loaded,
        message=(
            "Trained model is active." if gen.is_model_loaded
            else "Using rule-based fallback. Train the model to enable AI generation."
        ),
    )


@app.post("/generate", response_model=QuestionResponse)
def generate_question(req: GenerateRequest):
    import time
    request_start = time.time()
    
    difficulty = req.difficulty.lower() if req.difficulty else "medium"
    if difficulty not in ("easy", "medium", "hard"):
        raise HTTPException(status_code=400, detail="difficulty must be 'easy', 'medium', or 'hard'")

    gen = get_generator()
    
    gen_start = time.time()
    result = gen.generate(topic=req.topic.strip(), difficulty=difficulty, exclude_titles=req.exclude_titles)
    gen_time = time.time() - gen_start
    
    print(f"[API] Question generation took {gen_time:.3f}s")

    import json as _json

    def _to_stdin(val) -> str:
        """Convert any value to a plain-text stdin string."""
        if isinstance(val, str):
            return val
        if isinstance(val, bool):
            return str(val).lower()
        if isinstance(val, (int, float)):
            return str(val)
        if isinstance(val, (list, tuple)):
            # flat list/tuple of primitives → space-separated on one line
            if all(isinstance(x, (int, float, str, bool)) for x in val):
                return " ".join(str(x) for x in val)
            # list of pairs/triples (edges) → one "u v [w]" per line
            if all(isinstance(x, (list, tuple)) and len(x) >= 2 for x in val):
                return "\n".join(" ".join(str(e) for e in pair) for pair in val)
            # nested list (e.g. board) → one row per line
            return "\n".join(_to_stdin(row) for row in val)
        if isinstance(val, dict):
            # Special handling for graph inputs: {"nodes": n, "edges": [...], "src": s, "dst": d}
            if "edges" in val and "nodes" in val:
                edges = val["edges"]
                n_nodes = val["nodes"]
                n_edges = len(edges)
                edge_lines = "\n".join(" ".join(str(e) for e in edge) for edge in edges)
                if "src" in val and "dst" in val:
                    return f"{n_nodes} {n_edges}\n{edge_lines}\n{val['src']} {val['dst']}"
                elif "src" in val:
                    header = f"{n_nodes} {n_edges} {val['src']}"
                    return f"{header}\n{edge_lines}" if edge_lines else header
                else:
                    return f"{n_nodes} {n_edges}\n{edge_lines}" if edge_lines else f"{n_nodes} {n_edges}"
            # dict of named fields → one value per line in insertion order
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
        if isinstance(val, list):
            if all(isinstance(x, (int, float, str, bool)) for x in val):
                return " ".join(str(x) for x in val)
            return "\n".join(_to_stdout(row) for row in val)
        return str(val)

    # normalise test_cases — input/output may be lists, dicts, or strings
    test_cases = []
    for tc in result.get("test_cases", []):
        if isinstance(tc, dict):
            inp = _to_stdin(tc.get("input", ""))
            out = _to_stdout(tc.get("output", ""))
            test_cases.append(TestCase(input=inp, output=out))

    response = QuestionResponse(
        title=result.get("title", ""),
        problem_statement=result.get("problem_statement", ""),
        input_format=result.get("input_format", ""),
        output_format=result.get("output_format", ""),
        sample_input=_to_stdin(result.get("sample_input", "")),
        sample_output=_to_stdout(result.get("sample_output", "")),
        test_cases=test_cases,
        topic=result.get("topic", req.topic),
        difficulty=result.get("difficulty", difficulty),
        source=result.get("source", "template"),
    )
    
    total_time = time.time() - request_start
    print(f"[API] ✓ Total request time: {total_time:.3f}s")
    
    return response


@app.get("/topics")
def list_topics():
    """Return a list of supported topics (for UI suggestions)."""
    return {
        "topics": [
            "Arrays", "Strings", "Linked Lists", "Stacks", "Queues",
            "Trees", "Graphs", "Dynamic Programming", "Sorting", "Searching",
            "Recursion", "Backtracking", "Greedy", "Hashing", "Heaps",
            "Binary Search", "Bit Manipulation", "Math", "Two Pointers",
            "Sliding Window", "Divide and Conquer", "Trie", "Segment Tree",
        ]
    }


@app.post("/debug-hint", response_model=DebugHintResponse)
def debug_hint(req: DebugHintRequest):
    """
    Analyse a failed submission and return a short debugging hint.

    Returns JSON: { status, line, message, hint }
    """
    debugger = get_debugger()
    result = debugger.generate(
        problem_statement=req.problem_statement,
        user_code=req.user_code,
        language=req.language,
        failed_test_input=req.failed_test_input,
        expected_output=req.expected_output,
        actual_output=req.actual_output,
    )
    return DebugHintResponse(
        status=result.get("status", "No clear logic issue detected"),
        line=str(result.get("line", "")),
        message=result.get("message", ""),
        hint=result.get("hint", ""),
    )


@app.post("/smart-debug", response_model=DebugHintResponse)
def smart_debug(req: DebugHintRequest):
    """
    Smart rule-based logic analyser — identifies the single most likely
    root-cause error using AST-level pattern matching.

    Returns JSON: { status, line, message, hint }
    """
    result = smart_debug_hint(
        problem_statement=req.problem_statement,
        user_code=req.user_code,
        language=req.language,
        failed_test_input=req.failed_test_input,
        expected_output=req.expected_output,
        actual_output=req.actual_output,
    )
    return DebugHintResponse(
        status=result.get("status", "No clear logic issue detected"),
        line=str(result.get("line", "")),
        message=result.get("message", ""),
        hint=result.get("hint", ""),
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
