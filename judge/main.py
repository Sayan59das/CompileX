"""The judge: runs a player's code in Docker sandboxes and says which tests passed.

It is the one part of CompileX that needs Docker, so it runs on its own machine, away from the web backend. The backend sends it a program
and the tests; it runs them with the same executor the backend always used (backend/app/services/code_executor.py, copied into this image
by judge/Dockerfile) and returns the verdicts.

Safety rules:
- every request needs the shared secret in the X-Judge-Token header (JUDGE_TOKEN); with no secret set the service refuses to start;
- it never runs code unsandboxed. Mode "docker" (default): each run is a Docker container; with no Docker it answers 503. Mode "process"
  (SANDBOX_MODE=process, for hosts without Docker such as a free Render service): each run is an unprivileged throwaway user with limits and no
  internet sockets (backend/app/services/process_sandbox.py); a startup self-check proves that works, and if it does not the judge answers 503;
- request sizes are capped, and the executor's own cap on simultaneous sandboxes (MAX_CONCURRENT_EXECUTIONS) applies;
- the Docker socket gives root on the host, so run this service on a machine that holds nothing else.
"""

import asyncio
import hmac
import os
from typing import List, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from app.services import code_executor as ce

MAX_CODE_CHARS = 100_000
MAX_TESTS = 50
MAX_TEST_CHARS = 200_000

app = FastAPI(title="CompileX judge", docs_url=None, redoc_url=None, openapi_url=None)


def _token() -> str:
    return os.environ.get("JUDGE_TOKEN", "")


def _process_mode() -> bool:
    return ce.settings.SANDBOX_MODE == "process"


@app.on_event("startup")
async def _require_a_token():
    if len(_token()) < 16:
        raise RuntimeError("JUDGE_TOKEN must be set to a secret of at least 16 characters; the judge will not start without it")
    if _process_mode():
        from app.services import process_sandbox as ps

        ps.get_slots(ce.settings.MAX_CONCURRENT_EXECUTIONS)
        works, why = await asyncio.to_thread(ps.check, True)
        print(f"[Judge] process sandbox self-check: {'OK' if works else 'FAILED: ' + why}")


class TestIn(BaseModel):
    input_data: str = Field(max_length=MAX_TEST_CHARS)
    expected_output: str = Field(max_length=MAX_TEST_CHARS)


class RunRequest(BaseModel):
    code: str = Field(max_length=MAX_CODE_CHARS)
    language: str = Field(max_length=20)
    test_cases: List[TestIn] = Field(max_length=MAX_TESTS)
    time_limit_ms: int = Field(default=2000, ge=100, le=30_000)
    function_signature: Optional[dict] = None


def _docker_ready() -> bool:
    return bool(ce.DOCKER_AVAILABLE and ce.docker_client)


def _sandbox_ready() -> bool:
    if _process_mode():
        from app.services import process_sandbox as ps

        return ps.check()[0]
    return _docker_ready()


@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    """Open to anyone (it shows nothing private): is the service up, which sandbox does it use, and does that sandbox work?"""
    mode = "process" if _process_mode() else "docker"
    ready = _sandbox_ready()
    return {"status": "ok" if ready else "no-sandbox", "mode": mode, "sandbox": ready, "docker": _docker_ready()}


@app.post("/run")
async def run(body: RunRequest, x_judge_token: str = Header(default="")):
    if not hmac.compare_digest(x_judge_token.encode(), _token().encode()):
        raise HTTPException(status_code=401, detail="Bad or missing judge token")
    if body.language.lower() not in ce.LANGUAGE_CONFIG:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {body.language}")
    if not _sandbox_ready():
        raise HTTPException(status_code=503, detail="The judge has no working sandbox, so it will not run code")

    tests = [ce.TestCase(input_data=t.input_data, expected_output=t.expected_output) for t in body.test_cases]
    # `execute_code` of this process always uses Docker here: JUDGE_URL is not set, and the check above ruled out the no-Docker path.
    result = await ce.code_executor.execute_code(
        body.code, body.language, tests, time_limit_ms=body.time_limit_ms, function_signature=body.function_signature
    )
    return {
        "total_tests": result.total_tests,
        "passed_tests": result.passed_tests,
        "execution_time_ms": result.execution_time_ms,
        "score": result.score,
        "results": [
            {"success": r.success, "passed": r.passed, "output": r.output, "error": r.error, "execution_time_ms": r.execution_time_ms}
            for r in result.results
        ],
    }
