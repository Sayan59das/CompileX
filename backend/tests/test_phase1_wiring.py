"""Phase 1 wiring (docs/scaling-plan.md): the app boots, the question service is told who will see a question, and no request state is kept in a process.

The first version of Phase 1 broke the import of routes.py (a shared import was removed with the block that used it) and no test noticed, because
no pytest file imported routes.py or main.py. These do, and a static check looks for undefined names in every module of the app.

Run from the backend folder:  python -m pytest tests/test_phase1_wiring.py -q
"""

import ast
import asyncio
import builtins
import importlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
import pytest
import socketio

from app.models.models import DifficultyLevel
from app.services import ai_generator as ag

APP = os.path.join(os.path.dirname(__file__), "..", "app")


# ── the app boots ───────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_the_app_imports_and_answers_its_health_check():
    from starlette.testclient import TestClient

    main = importlib.import_module("app.main")
    assert TestClient(main.app_http).get("/health").json() == {"status": "healthy"}
    assert TestClient(main.app_http).head("/health").status_code == 200       # uptime monitors check with HEAD
    paths = {route.path for route in main.app_http.routes}
    assert "/api/v1/lobbies" in paths and "/api/v1/questions/generate" in paths and "/api/v1/lobbies/{lobby_id}/leaderboard" in paths


def test_without_redis_the_socket_server_has_its_own_manager_and_with_redis_it_shares_through_redis(monkeypatch):
    from app.core.config import get_settings

    settings = get_settings()
    main = importlib.import_module("app.main")
    try:
        monkeypatch.setattr(settings, "REDIS_URL", "")
        main = importlib.reload(main)
        assert not isinstance(main.sio.manager, socketio.AsyncRedisManager)
        monkeypatch.setattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        main = importlib.reload(main)
        assert isinstance(main.sio.manager, socketio.AsyncRedisManager)
    finally:
        monkeypatch.undo()
        importlib.reload(main)


# ── no undefined names ──────────────────────────────────────────────────────────────────────────────────────────────────────

def undefined_names(path):
    """Names a module reads that it never defines, imports or gets from builtins (a coarse check: it ignores scopes, so it finds the missing
    import and the typo, not a name that exists elsewhere in the file)."""
    tree = ast.parse(open(path, encoding="utf-8").read(), path)
    defined = set(dir(builtins)) | {"__file__", "__name__"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                defined.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            defined.add(node.id)
        elif isinstance(node, ast.arg):
            defined.add(node.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            defined.add(node.name)
        elif isinstance(node, ast.Global):
            defined.update(node.names)
    return sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)} - defined)


def modules():
    for folder, _, files in os.walk(APP):
        if "__pycache__" in folder:
            continue
        for name in files:
            if name.endswith(".py"):
                yield os.path.join(folder, name)


@pytest.mark.parametrize("path", sorted(modules()), ids=lambda p: os.path.relpath(p, APP).replace(os.sep, "/"))
def test_no_module_of_the_app_reads_a_name_it_never_defines(path):
    assert undefined_names(path) == []


def test_the_undefined_name_check_does_catch_the_bug_it_was_written_for(tmp_path):
    broken = tmp_path / "broken.py"
    broken.write_text("_locks = defaultdict(asyncio.Lock)\n")
    assert undefined_names(str(broken)) == ["asyncio", "defaultdict"]


# ── nothing about a request is kept in this process ─────────────────────────────────────────────────────────────────────────

def test_the_routes_keep_no_per_process_state_for_limits_or_locks():
    source = open(os.path.join(APP, "api", "v1", "routes.py"), encoding="utf-8").read()
    for leftover in ("_request_counts", "_generation_locks", "_assessment_locks", "defaultdict(asyncio.Lock)"):
        assert leftover not in source, leftover


def test_lobbies_are_not_a_dict_of_the_process_any_more():
    source = open(os.path.join(APP, "services", "lobby_manager.py"), encoding="utf-8").read()
    for leftover in ("self._lobbies", "self._lobby_codes", "self._player_sessions", "self._sid_to_lobby"):
        assert leftover not in source, leftover


# ── the question service is told who will see the question ──────────────────────────────────────────────────────────────────

def test_the_players_are_sent_to_the_question_service_as_text(monkeypatch):
    seen = {}

    def answer(request):
        seen["json"] = json.loads(request.content)
        return httpx.Response(200, json={"title": "T"})

    class Client(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, transport=httpx.MockTransport(answer), **kwargs)

    monkeypatch.setattr(ag.httpx, "AsyncClient", Client)
    generator = ag.AIQuestionGenerator()
    asyncio.run(generator._call_ai_service("arrays", "easy", 5, exclude_titles=["a"], player_ids=[7, 9]))
    assert seen["json"] == {"topic": "arrays", "difficulty": "easy", "num_test_cases": 5, "exclude_titles": ["a"], "player_ids": ["7", "9"]}
    asyncio.run(generator._call_ai_service("arrays", "easy", 5))
    assert seen["json"]["player_ids"] is None


def test_generate_question_hands_the_players_on(monkeypatch):
    got = {}
    question = {"title": "Add", "topic": "math", "description": "Print the sum.", "input_format": "Two integers.", "output_format": "One integer.",
                "sample_input": "1 2", "sample_output": "3", "test_cases": [{"input": "1 2", "output": "3"}, {"input": "2 2", "output": "4"}, {"input": "0 5", "output": "5"}]}

    async def call(self, topic, difficulty, num_test_cases, exclude_titles=None, player_ids=None):
        got["player_ids"] = player_ids
        return dict(question)

    monkeypatch.setattr(ag.AIQuestionGenerator, "_call_ai_service", call)
    ag._DIAGRAM_CACHE.clear()
    result = asyncio.run(ag.AIQuestionGenerator().generate_question(DifficultyLevel.EASY, "math", 3, None, exclude_titles=[], player_ids=[1, 2]))
    assert got["player_ids"] == [1, 2] and result["title"] == "Add"
