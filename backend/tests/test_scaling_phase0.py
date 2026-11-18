"""The first scaling fixes (docs/scaling-plan.md, Phase 0): the changes that make one backend process survive many players at once.

* the table that holds issued questions is indexed on the column its clean-up filters on, in new and in existing databases;
* at most MAX_CONCURRENT_EXECUTIONS submissions run in sandboxes at once, the rest wait;
* a diagram is drawn on its own threads (never on the event loop) and is remembered, so a question served to many players is drawn once;
* the compose file starts the question service that is really deployed, on the port the backend calls.

Run from the backend folder:  python -m pytest tests/test_scaling_phase0.py -q
"""

import asyncio
import os
import re
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import inspect, text

from app.db.database import Base, _ensure_indexes, build_engine
from app.models import models  # noqa: F401  (registers every table on Base)
from app.services import ai_generator as ag
from app.services import code_executor as ce
from app.services import diagram_generator as dgm


# ── the index ───────────────────────────────────────────────────────────────────────────────────────────────────────────────

def index_names(conn):
    return {i["name"] for i in inspect(conn).get_indexes("issued_questions")}


def test_a_new_database_has_the_index_on_issued_at(tmp_path):
    async def main():
        engine = build_engine(f"sqlite+aiosqlite:///{tmp_path / 't.db'}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            assert {"ix_issued_at", "ix_issued_user"} <= await conn.run_sync(index_names)
        await engine.dispose()

    asyncio.run(main())


def test_an_existing_database_gets_the_index_without_losing_rows(tmp_path):
    """create_all never adds an index to a table that already exists, so the startup migration has to."""
    async def main():
        engine = build_engine(f"sqlite+aiosqlite:///{tmp_path / 't.db'}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(text("INSERT INTO issued_questions (ref, user_id, question_json, issued_at) VALUES ('r', 1, '{}', 5.0)"))
            await conn.execute(text("DROP INDEX ix_issued_at"))
            assert "ix_issued_at" not in await conn.run_sync(index_names)
            await conn.run_sync(_ensure_indexes)
            await conn.run_sync(_ensure_indexes)   # a second start must not fail
            assert "ix_issued_at" in await conn.run_sync(index_names)
            assert (await conn.execute(text("SELECT COUNT(*) FROM issued_questions"))).scalar() == 1
        await engine.dispose()

    asyncio.run(main())


def test_the_expiry_delete_uses_the_index(tmp_path):
    async def main():
        engine = build_engine(f"sqlite+aiosqlite:///{tmp_path / 't.db'}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            plan = (await conn.execute(text("EXPLAIN QUERY PLAN DELETE FROM issued_questions WHERE issued_at < 10"))).fetchall()
        await engine.dispose()
        return " ".join(str(row) for row in plan)

    assert "ix_issued_at" in asyncio.run(main())


# ── code execution is capped ────────────────────────────────────────────────────────────────────────────────────────────────

def fake_docker(monkeypatch, limit, pause=0.02):
    """Make the executor think Docker is there, and replace the sandbox with a coroutine that records how many run together."""
    seen = {"now": 0, "most": 0, "done": 0}

    async def sandbox(self, code, language, test_cases, function_signature=None):
        seen["now"] += 1
        seen["most"] = max(seen["most"], seen["now"])
        await asyncio.sleep(pause)
        seen["now"] -= 1
        seen["done"] += 1
        return ce.SubmissionResult(0, 0, 0.0, [], 0)

    monkeypatch.setattr(ce.settings, "MAX_CONCURRENT_EXECUTIONS", limit)
    monkeypatch.setattr(ce, "DOCKER_AVAILABLE", True)
    monkeypatch.setattr(ce, "docker_client", object())
    monkeypatch.setattr(ce.CodeExecutor, "_execute_with_docker", sandbox)
    return seen


def submit_many(count):
    async def main():
        await asyncio.gather(*(ce.code_executor.execute_code("print(1)", "python", []) for _ in range(count)))

    asyncio.run(main())


@pytest.mark.parametrize("limit", [1, 3, 8])
def test_no_more_than_the_limit_run_at_once_and_every_submission_still_runs(monkeypatch, limit):
    seen = fake_docker(monkeypatch, limit)
    submit_many(40)
    assert seen["most"] == limit and seen["done"] == 40


def test_the_limit_applies_to_the_subprocess_path_too(monkeypatch):
    seen = {"now": 0, "most": 0}

    async def sandbox(self, code, language, test_cases, function_signature=None):
        seen["now"] += 1
        seen["most"] = max(seen["most"], seen["now"])
        await asyncio.sleep(0.01)
        seen["now"] -= 1
        return ce.SubmissionResult(0, 0, 0.0, [], 0)

    monkeypatch.setattr(ce.settings, "MAX_CONCURRENT_EXECUTIONS", 2)
    monkeypatch.setattr(ce, "DOCKER_AVAILABLE", False)
    monkeypatch.setattr(ce.CodeExecutor, "_execute_with_subprocess", sandbox)
    submit_many(12)
    assert seen["most"] == 2


def test_a_failing_submission_gives_its_slot_back(monkeypatch):
    calls = {"n": 0}

    async def sandbox(self, code, language, test_cases, function_signature=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("sandbox crashed")
        return ce.SubmissionResult(0, 0, 0.0, [], 0)

    monkeypatch.setattr(ce.settings, "MAX_CONCURRENT_EXECUTIONS", 1)
    monkeypatch.setattr(ce, "DOCKER_AVAILABLE", True)
    monkeypatch.setattr(ce, "docker_client", object())
    monkeypatch.setattr(ce.CodeExecutor, "_execute_with_docker", sandbox)

    async def main():
        first = await asyncio.gather(ce.code_executor.execute_code("x", "python", []), return_exceptions=True)
        second = await asyncio.wait_for(ce.code_executor.execute_code("x", "python", []), timeout=2)   # would hang if the slot leaked
        return first, second

    first, second = asyncio.run(main())
    assert isinstance(first[0], RuntimeError) and second.total_tests == 0


def test_without_docker_the_executor_falls_back_instead_of_failing(monkeypatch):
    """DOCKER_AVAILABLE used to be defined only when Docker answered at import, so without Docker the first submission raised NameError."""
    assert isinstance(ce.DOCKER_AVAILABLE, bool)
    used = []

    async def subprocess_path(self, code, language, test_cases, function_signature=None):
        used.append("subprocess")
        return ce.SubmissionResult(0, 0, 0.0, [], 0)

    monkeypatch.setattr(ce, "DOCKER_AVAILABLE", False)
    monkeypatch.setattr(ce, "docker_client", None)
    monkeypatch.setattr(ce.CodeExecutor, "_execute_with_subprocess", subprocess_path)
    asyncio.run(ce.code_executor.execute_code("print(1)", "python", []))
    assert used == ["subprocess"]


def test_an_unsupported_language_does_not_take_a_slot(monkeypatch):
    seen = fake_docker(monkeypatch, 1)
    result = asyncio.run(ce.code_executor.execute_code("x", "brainfuck", []))
    assert result.passed_tests == 0 and seen["done"] == 0


# ── diagrams are drawn off the event loop, once ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def drawing(monkeypatch):
    """A stand-in for the real drawing that records which thread did the work and how often."""
    record = {"threads": [], "questions": []}

    def draw(question):
        record["threads"].append(threading.get_ident())
        record["questions"].append(question["title"])
        return f"data:image/png;base64,{question['title']}"

    monkeypatch.setattr(dgm.diagram_generator, "diagram_for_question", draw)
    ag._DIAGRAM_CACHE.clear()
    yield record
    ag._DIAGRAM_CACHE.clear()


def test_a_diagram_is_not_drawn_on_the_event_loop_thread(drawing):
    async def main():
        return threading.get_ident(), await ag._draw_diagram({"title": "A"})

    loop_thread, picture = asyncio.run(main())
    assert picture == "data:image/png;base64,A"
    assert drawing["threads"] and loop_thread not in drawing["threads"]


def test_the_event_loop_keeps_running_while_a_diagram_is_drawn(monkeypatch):
    """While a slow drawing runs, other coroutines (every other player's request and socket) must still get their turn."""
    release = threading.Event()
    started = threading.Event()

    def slow_draw(question):
        started.set()
        release.wait(5)
        return "data:image/png;base64,slow"

    monkeypatch.setattr(dgm.diagram_generator, "diagram_for_question", slow_draw)
    ag._DIAGRAM_CACHE.clear()

    async def main():
        ticks = []

        async def other_players():
            while not started.is_set():
                await asyncio.sleep(0.001)
            for i in range(20):
                ticks.append(i)
                await asyncio.sleep(0.001)
            release.set()

        drawing_task = asyncio.create_task(ag._draw_diagram({"title": "slow"}))
        await other_players()
        return ticks, await asyncio.wait_for(drawing_task, 5)

    ticks, picture = asyncio.run(main())
    assert len(ticks) == 20 and picture.endswith("slow")


def test_the_same_question_is_drawn_once_however_many_players_get_it(drawing):
    async def main():
        pictures = [await ag._draw_diagram({"title": "A", "x": 1}) for _ in range(50)]
        await ag._draw_diagram({"title": "B"})
        return pictures

    pictures = asyncio.run(main())
    assert set(pictures) == {"data:image/png;base64,A"} and drawing["questions"].count("A") == 1 and drawing["questions"].count("B") == 1


def test_a_question_with_no_diagram_is_remembered_as_having_none(monkeypatch):
    calls = []
    monkeypatch.setattr(dgm.diagram_generator, "diagram_for_question", lambda question: calls.append(1))
    ag._DIAGRAM_CACHE.clear()

    async def main():
        return [await ag._draw_diagram({"title": "no graph here"}) for _ in range(5)]

    assert asyncio.run(main()) == [None] * 5 and len(calls) == 1
    ag._DIAGRAM_CACHE.clear()


def test_a_failure_is_raised_and_not_remembered(monkeypatch):
    attempts = []

    def flaky(question):
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("renderer crashed")
        return "data:image/png;base64,ok"

    monkeypatch.setattr(dgm.diagram_generator, "diagram_for_question", flaky)
    ag._DIAGRAM_CACHE.clear()

    async def main():
        with pytest.raises(RuntimeError):
            await ag._draw_diagram({"title": "A"})
        return await ag._draw_diagram({"title": "A"})

    assert asyncio.run(main()) == "data:image/png;base64,ok"
    ag._DIAGRAM_CACHE.clear()


def test_the_memory_of_diagrams_is_bounded_and_forgets_the_least_recently_used(monkeypatch, drawing):
    monkeypatch.setattr(ag, "_DIAGRAM_CACHE_SIZE", 3)

    async def main():
        for title in ("A", "B", "C"):
            await ag._draw_diagram({"title": title})
        await ag._draw_diagram({"title": "A"})   # A is used again, so B is now the oldest
        await ag._draw_diagram({"title": "D"})   # evicts B
        for title in ("A", "C", "D", "B"):
            await ag._draw_diagram({"title": title})

    asyncio.run(main())
    assert len(ag._DIAGRAM_CACHE) <= 3
    assert drawing["questions"].count("B") == 2 and drawing["questions"].count("A") == 1


def test_a_changed_question_is_a_different_picture(drawing):
    async def main():
        return await ag._draw_diagram({"title": "A", "sample_input": "1"}), await ag._draw_diagram({"title": "A", "sample_input": "2"})

    asyncio.run(main())
    assert drawing["questions"] == ["A", "A"]


def test_the_diagram_threads_are_their_own_and_bounded(monkeypatch):
    monkeypatch.setattr(ag, "_DIAGRAM_POOL", None)
    monkeypatch.setattr(ag.settings, "DIAGRAM_WORKERS", 2)
    pool = ag._diagram_pool()
    assert pool is ag._diagram_pool() and pool._max_workers == 2 and pool._thread_name_prefix == "diagram"
    pool.shutdown(wait=False)


def test_building_a_graph_question_still_gives_its_diagram():
    """End to end through the real drawing: a graph question comes back with a picture, and a plain one without."""
    from app.models.models import DifficultyLevel

    graph = {"title": "Shortest road", "topic": "graphs", "description": "A graph with n vertices (numbered 1 to n) and m undirected edges.",
             "input_format": "First line: n and m. Then m lines: u v.", "output_format": "One integer.",
             "sample_input": "3 2\n1 2\n2 3", "sample_output": "2",
             "test_cases": [{"input": "3 2\n1 2\n2 3", "output": "2"}, {"input": "2 1\n1 2", "output": "1"}, {"input": "4 3\n1 2\n2 3\n3 4", "output": "3"}]}
    plain = {"title": "Add two numbers", "topic": "math", "description": "Print the sum of two integers.", "input_format": "Two integers.",
             "output_format": "One integer.", "sample_input": "1 2", "sample_output": "3",
             "test_cases": [{"input": "1 2", "output": "3"}, {"input": "5 5", "output": "10"}, {"input": "0 0", "output": "0"}]}
    ag._DIAGRAM_CACHE.clear()
    with_picture = asyncio.run(ag._build_result(dict(graph), DifficultyLevel.EASY, "graphs"))
    without = asyncio.run(ag._build_result(dict(plain), DifficultyLevel.EASY, "math"))
    assert with_picture["diagram"].startswith("data:image/png;base64,") and without["diagram"] is None


# ── the compose file ────────────────────────────────────────────────────────────────────────────────────────────────────────

COMPOSE = os.path.join(os.path.dirname(__file__), "..", "..", "docker-compose.yml")


def service_block(name):
    text_ = open(COMPOSE, encoding="utf-8").read().replace("\r\n", "\n")
    match = re.search(rf"^  {name}:\n(.*?)(?=^  [a-z_]+:\n|^[a-z]+:)", text_, re.S | re.M)
    assert match, f"no service called {name}"
    return match.group(1)


def test_the_compose_file_runs_the_deployed_question_service_on_the_port_the_backend_calls():
    ai, api = service_block("ai"), service_block("api")
    assert "main_dynamic:app" in ai, "the mounted folder's own main.py is the retired transformer service"
    port = re.search(r"AI_SERVICE_URL=http://ai:(\d+)", api).group(1)
    assert re.search(rf'"--port", "{port}"', ai) and re.search(rf'"(127\.0\.0\.1:)?{port}:{port}"', ai)
