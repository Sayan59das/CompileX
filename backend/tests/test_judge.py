"""The judge service and the backend's client for it (docs/scaling-plan.md, Phase 2).

No Docker and no network: the judge's executor is replaced by a fake, and the backend talks to the judge through httpx's in-memory transport.
Run from the backend folder:  python -m pytest tests/test_judge.py -q
"""

import asyncio
import importlib.util
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
import pytest
import yaml
from fastapi.testclient import TestClient

from app.services import code_executor as ce

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
TOKEN = "a-long-enough-secret-token"


def load_judge():
    spec = importlib.util.spec_from_file_location("judge_main", os.path.join(ROOT, "judge", "main.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


judge = load_judge()
GOOD = {
    "code": "print(1)", "language": "python", "time_limit_ms": 2000,
    "test_cases": [{"input_data": "1", "expected_output": "1"}, {"input_data": "2", "expected_output": "2"}],
}


@pytest.fixture
def served(monkeypatch):
    """The judge app with a token, 'Docker available', and a fake executor that records what it was asked to run."""
    monkeypatch.setenv("JUDGE_TOKEN", TOKEN)
    monkeypatch.setattr(ce, "DOCKER_AVAILABLE", True)
    monkeypatch.setattr(ce, "docker_client", object())
    seen = []

    async def fake_execute(self, code, language, test_cases, time_limit_ms=2000, function_signature=None):
        seen.append((code, language, [(t.input_data, t.expected_output) for t in test_cases], time_limit_ms, function_signature))
        return ce.SubmissionResult(
            len(test_cases), 1, 12.5,
            [ce.ExecutionResult(True, i == 0, "out", None if i == 0 else "wrong", 5.0) for i in range(len(test_cases))], score=50,
        )

    monkeypatch.setattr(ce.CodeExecutor, "execute_code", fake_execute)
    with TestClient(judge.app) as client:
        yield client, seen


# ── the judge service ───────────────────────────────────────────────────────


def test_it_refuses_to_start_without_a_real_secret(monkeypatch):
    for bad in ("", "short"):
        monkeypatch.setenv("JUDGE_TOKEN", bad)
        with pytest.raises(RuntimeError):
            with TestClient(judge.app):
                pass


def test_a_missing_or_wrong_token_is_refused_and_nothing_is_run(served):
    client, seen = served
    assert client.post("/run", json=GOOD).status_code == 401
    assert client.post("/run", json=GOOD, headers={"X-Judge-Token": "wrong-token-of-any-kind"}).status_code == 401
    assert client.post("/run", json=GOOD, headers={"X-Judge-Token": ""}).status_code == 401
    assert seen == []


def test_a_good_request_runs_and_the_verdicts_come_back(served):
    client, seen = served
    body = dict(GOOD, function_signature={"function_name": "solve", "parameters": [], "return_type": "int"})
    r = client.post("/run", json=body, headers={"X-Judge-Token": TOKEN})
    assert r.status_code == 200
    data = r.json()
    assert data["total_tests"] == 2 and data["passed_tests"] == 1 and data["score"] == 50
    assert [x["passed"] for x in data["results"]] == [True, False] and data["results"][1]["error"] == "wrong"
    assert seen == [("print(1)", "python", [("1", "1"), ("2", "2")], 2000, body["function_signature"])]


def test_an_unsupported_language_is_a_400(served):
    client, seen = served
    r = client.post("/run", json=dict(GOOD, language="brainfuck"), headers={"X-Judge-Token": TOKEN})
    assert r.status_code == 400 and seen == []


def test_without_docker_it_says_503_and_never_runs_the_code(served, monkeypatch):
    client, seen = served
    monkeypatch.setattr(ce, "DOCKER_AVAILABLE", False)
    assert client.post("/run", json=GOOD, headers={"X-Judge-Token": TOKEN}).status_code == 503
    assert seen == []
    assert client.get("/health").json() == {"status": "no-sandbox", "mode": "docker", "sandbox": False, "docker": False}


def test_requests_that_are_too_big_or_malformed_are_refused(served):
    client, seen = served
    h = {"X-Judge-Token": TOKEN}
    assert client.post("/run", json=dict(GOOD, code="x" * (judge.MAX_CODE_CHARS + 1)), headers=h).status_code == 422
    too_many = [{"input_data": "1", "expected_output": "1"}] * (judge.MAX_TESTS + 1)
    assert client.post("/run", json=dict(GOOD, test_cases=too_many), headers=h).status_code == 422
    assert client.post("/run", json=dict(GOOD, time_limit_ms=10 ** 9), headers=h).status_code == 422
    assert client.post("/run", json={"code": "x"}, headers=h).status_code == 422
    assert seen == []


def test_health_answers_get_and_head_without_a_token(served):
    client, _ = served
    assert client.get("/health").json() == {"status": "ok", "mode": "docker", "sandbox": True, "docker": True}
    assert client.head("/health").status_code == 200


def test_the_api_docs_are_not_exposed(served):
    client, _ = served
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


# ── the backend's client ────────────────────────────────────────────────────


@pytest.fixture
def remote(monkeypatch):
    """execute_code with JUDGE_URL set; `handler` is what the pretend judge does with each request."""
    monkeypatch.setattr(ce.settings, "JUDGE_URL", "https://judge.example.com/")
    monkeypatch.setattr(ce.settings, "JUDGE_TOKEN", TOKEN)
    state = {"requests": [], "handler": None}
    real_client = httpx.AsyncClient

    def handler(request):
        state["requests"].append(request)
        return state["handler"](request)

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))

    async def never(*a, **k):
        raise AssertionError("with a judge configured, nothing may run on this machine")

    monkeypatch.setattr(ce.CodeExecutor, "_execute_with_docker", never)
    monkeypatch.setattr(ce.CodeExecutor, "_execute_with_subprocess", never)
    return state


def tests_for(n=2):
    return [ce.TestCase(input_data=str(i), expected_output=str(i)) for i in range(n)]


def run_remote(**kw):
    return asyncio.run(ce.code_executor.execute_code("print(1)", "python", tests_for(), **kw))


def test_the_client_sends_the_program_and_the_token_and_maps_the_verdicts_back(remote):
    import json

    remote["handler"] = lambda req: httpx.Response(200, json={
        "total_tests": 2, "passed_tests": 1, "execution_time_ms": 9.0, "score": 50,
        "results": [
            {"success": True, "passed": True, "output": "0", "error": None, "execution_time_ms": 4.0},
            {"success": False, "passed": False, "output": "", "error": "Time limit exceeded", "execution_time_ms": 5.0},
        ],
    })
    result = run_remote(function_signature={"function_name": "solve"})
    request = remote["requests"][0]
    assert str(request.url) == "https://judge.example.com/run" and request.headers["x-judge-token"] == TOKEN
    sent = json.loads(request.content)
    assert sent["code"] == "print(1)" and sent["language"] == "python" and sent["function_signature"] == {"function_name": "solve"}
    assert sent["test_cases"] == [{"input_data": "0", "expected_output": "0"}, {"input_data": "1", "expected_output": "1"}]
    assert (result.total_tests, result.passed_tests, result.score) == (2, 1, 50)
    assert [(r.passed, r.error) for r in result.results] == [(True, None), (False, "Time limit exceeded")]


@pytest.mark.parametrize("answer", [
    lambda req: httpx.Response(503, json={"detail": "no docker"}),
    lambda req: httpx.Response(401, json={"detail": "bad token"}),
    lambda req: httpx.Response(500, text="boom"),
    lambda req: httpx.Response(200, text="not json at all"),
    lambda req: httpx.Response(200, json={"unexpected": "shape"}),
])
def test_a_judge_that_fails_gives_unavailable_for_every_test_and_nothing_runs_locally(remote, answer):
    remote["handler"] = answer
    result = run_remote()
    assert result.passed_tests == 0 and result.total_tests == 2 and len(result.results) == 2
    assert all(not r.passed and "unavailable" in r.error for r in result.results)


def test_an_unreachable_or_slow_judge_gives_unavailable(remote):
    def down(req):
        raise httpx.ConnectError("no route to host")

    remote["handler"] = down
    assert all("unavailable" in r.error for r in run_remote().results)

    def slow(req):
        raise httpx.ReadTimeout("too slow")

    remote["handler"] = slow
    assert all("unavailable" in r.error for r in run_remote().results)


def test_an_unsupported_language_never_reaches_the_judge(remote):
    remote["handler"] = lambda req: httpx.Response(200, json={})
    result = asyncio.run(ce.code_executor.execute_code("x", "brainfuck", tests_for()))
    assert remote["requests"] == [] and result.passed_tests == 0


# ── the deployment file ─────────────────────────────────────────────────────

COMPOSE = yaml.safe_load(open(os.path.join(ROOT, "docker-compose.yml"), encoding="utf-8"))


def mounts_docker_socket(service):
    return any("docker.sock" in str(v) for v in COMPOSE["services"][service].get("volumes", []))


def test_only_the_judge_has_the_docker_socket():
    assert mounts_docker_socket("judge")
    assert [name for name in COMPOSE["services"] if mounts_docker_socket(name)] == ["judge"]
    assert not any("DOCKER_HOST" in str(e) for e in COMPOSE["services"]["api"]["environment"])


def test_the_judge_is_not_reachable_from_outside_and_the_api_knows_where_it_is_and_the_secret():
    assert "ports" not in COMPOSE["services"]["judge"]
    env = COMPOSE["services"]["api"]["environment"]
    assert "JUDGE_URL=http://judge:9000" in env
    assert any(str(e).startswith("JUDGE_TOKEN=${JUDGE_TOKEN:?") for e in env)
    assert any(str(e).startswith("JUDGE_TOKEN=${JUDGE_TOKEN:?") for e in COMPOSE["services"]["judge"]["environment"])
    assert "judge" in COMPOSE["services"]["api"]["depends_on"]


def test_the_judge_image_contains_the_executor_and_the_service():
    text = open(os.path.join(ROOT, "judge", "Dockerfile"), encoding="utf-8").read()
    for needed in ("backend/app/services/code_executor.py", "backend/app/core/config.py", "judge/main.py", "judge/requirements.txt"):
        assert needed in text
