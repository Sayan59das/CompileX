"""Who may run code right now: the per-player and total limits in front of the sandboxes (docs/scaling-plan.md, Phase 2, host-independent part).

Every scenario runs against the in-process stand-in for Redis and, when COMPILEX_TEST_REDIS_URL is set (CI always sets it), against a real Redis.
The last tests call the real route functions (with the code runner faked) to prove the gate is in front of every place that runs a player's code.

Run from the backend folder:  python -m pytest tests/test_execution_gate.py -q
"""

import ast
import asyncio
import os
import sys
from contextlib import AsyncExitStack

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi import HTTPException

from app.api.v1 import routes
from app.services import execution_gate as eg
from app.services.shared_state import get_redis
from state_helpers import KINDS, run
from test_hidden_tests import fakes, run_with_db, seed_question_and_player   # noqa: F401  (fakes is a fixture)


class Clock:
    def __init__(self, start=2_000_000.0):
        self.now = start

    def time(self):
        return self.now


def slot(r, user, per_user=2, backlog=50):
    return eg.execution_slot(user, per_user=per_user, backlog=backlog, client=r)


# ── the limits ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize("kind", KINDS)
def test_a_player_may_have_two_runs_going_and_the_third_is_refused_until_one_ends(kind):
    async def scenario(r):
        async with AsyncExitStack() as stack:
            first = await stack.enter_async_context(slot(r, 1))
            await stack.enter_async_context(slot(r, 1))
            with pytest.raises(HTTPException) as e:
                await slot(r, 1).__aenter__()
            assert e.value.status_code == 429 and e.value.headers["Retry-After"] == str(eg.USER_RETRY_SECONDS)
            assert "already have 2 submissions" in e.value.detail
            assert await eg.in_flight(1, client=r) == 2            # a refused request is not counted

            await first.__aexit__(None, None, None)
            assert await eg.in_flight(1, client=r) == 1
            async with slot(r, 1):                                  # one ended, so one more may start
                assert await eg.in_flight(1, client=r) == 2
        assert await eg.in_flight(1, client=r) == 0 and await eg.in_flight(client=r) == 0

    run(kind, scenario)


@pytest.mark.parametrize("kind", KINDS)
def test_one_players_full_line_does_not_stop_another_player(kind):
    async def scenario(r):
        async with slot(r, 1, per_user=1):
            with pytest.raises(HTTPException):
                await slot(r, 1, per_user=1).__aenter__()
            async with slot(r, 2, per_user=1):
                assert await eg.in_flight(client=r) == 2

    run(kind, scenario)


@pytest.mark.parametrize("kind", KINDS)
def test_when_the_whole_line_is_full_the_next_player_is_told_so_and_gets_in_once_a_run_ends(kind):
    async def scenario(r):
        async with AsyncExitStack() as stack:
            held = [await stack.enter_async_context(slot(r, user, backlog=3)) for user in (1, 2, 3)]
            with pytest.raises(HTTPException) as e:
                await slot(r, 4, backlog=3).__aenter__()
            assert e.value.status_code == 429 and e.value.headers["Retry-After"] == str(eg.BUSY_RETRY_SECONDS)
            assert "3 submissions are running or waiting" in e.value.detail
            assert await eg.in_flight(4, client=r) == 0

            await held[0].__aexit__(None, None, None)
            async with slot(r, 4, backlog=3):
                assert await eg.in_flight(client=r) == 3

    run(kind, scenario)


@pytest.mark.parametrize("kind", KINDS)
def test_the_slot_is_given_back_when_the_run_raises(kind):
    async def scenario(r):
        with pytest.raises(RuntimeError):
            async with slot(r, 1, per_user=1):
                raise RuntimeError("the sandbox failed")
        assert await eg.in_flight(1, client=r) == 0
        async with slot(r, 1, per_user=1):                          # and the player is not locked out afterwards
            pass

    run(kind, scenario)


@pytest.mark.parametrize("kind", KINDS)
def test_entries_of_a_process_that_died_are_dropped_after_a_while(kind, monkeypatch):
    clock = Clock()
    monkeypatch.setattr(eg, "time", clock)

    async def scenario(r):
        await slot(r, 1, per_user=1, backlog=1).__aenter__()        # never released: its process died
        with pytest.raises(HTTPException):
            await slot(r, 1, per_user=1, backlog=1).__aenter__()
        clock.now += eg.ENTRY_SECONDS - 1
        with pytest.raises(HTTPException):
            await slot(r, 2, per_user=1, backlog=1).__aenter__()
        clock.now += 2                                              # now older than ENTRY_SECONDS, for the player and for the whole line
        async with slot(r, 1, per_user=1, backlog=1):
            assert await eg.in_flight(client=r) == 1                # the dead entry is gone, not just ignored

    run(kind, scenario)


# ── parallel requests and several processes ─────────────────────────────────


@pytest.mark.parametrize("kind", KINDS)
def test_thirty_parallel_requests_of_one_player_across_two_processes_admit_exactly_two(kind):
    async def scenario(a, b):
        release = asyncio.Event()

        async def worker(i):
            try:
                async with slot((a, b)[i % 2], 7, per_user=2, backlog=500):
                    await release.wait()
                    return "ran"
            except HTTPException as e:
                return e.status_code

        tasks = [asyncio.create_task(worker(i)) for i in range(30)]
        for _ in range(500):                                        # wait until every request that is going to be refused has been
            if sum(t.done() for t in tasks) >= 28:
                break
            await asyncio.sleep(0.01)
        assert await eg.in_flight(7, client=a) == 2
        release.set()
        results = await asyncio.gather(*tasks)
        assert results.count("ran") == 2 and results.count(429) == 28
        assert await eg.in_flight(7, client=b) == 0

    run(kind, scenario, clients=2)


@pytest.mark.parametrize("kind", KINDS)
def test_the_total_is_shared_by_every_process(kind):
    async def scenario(a, b):
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(slot(a, 1, backlog=2))
            await stack.enter_async_context(slot(b, 2, backlog=2))
            with pytest.raises(HTTPException):
                await slot(a, 3, backlog=2).__aenter__()
            with pytest.raises(HTTPException):
                await slot(b, 4, backlog=2).__aenter__()

    run(kind, scenario, clients=2)


def test_the_settings_give_the_limits_when_none_are_passed(monkeypatch):
    from app.core.config import get_settings

    s = get_settings()
    monkeypatch.setattr(s, "MAX_EXECUTIONS_PER_USER", 3)
    monkeypatch.setattr(s, "MAX_EXECUTION_BACKLOG", 9)
    gate = eg.execution_slot(1)
    assert (gate.per_user, gate.backlog) == (3, 9)
    assert (get_settings().MAX_EXECUTIONS_PER_USER, get_settings().MAX_EXECUTION_BACKLOG) == (3, 9)


# ── the routes ──────────────────────────────────────────────────────────────


def calls_to_execute_code_and_whether_each_is_gated():
    """Every `code_executor.execute_code(...)` call in routes.py, with whether an `async with execution_slot(...)` encloses it."""
    path = os.path.join(os.path.dirname(routes.__file__), "routes.py")
    tree = ast.parse(open(path, encoding="utf-8").read())
    found = []

    def is_slot(item):
        call = item.context_expr
        return isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "execution_slot"

    def visit(node, gated):
        for child in ast.iter_child_nodes(node):
            inner = gated or (isinstance(child, ast.AsyncWith) and any(is_slot(i) for i in child.items))
            if (
                isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute) and child.func.attr == "execute_code"
                and isinstance(child.func.value, ast.Name) and child.func.value.id == "code_executor"
            ):
                found.append((child.lineno, gated))
            visit(child, inner)

    visit(tree, False)
    return found


def test_every_place_that_runs_a_players_code_goes_through_the_gate():
    calls = calls_to_execute_code_and_whether_each_is_gated()
    assert len(calls) >= 4, f"expected the 4 known call sites, found {calls}"
    assert [line for line, gated in calls if not gated] == [], "a run of the player's code is not inside `async with execution_slot(...)`"


def test_submit_and_run_tests_are_refused_while_the_player_has_two_runs_going_and_run_nothing(tmp_path, fakes, monkeypatch):
    ran = []
    original = routes.code_executor.execute_code

    async def counting(*args, **kwargs):
        ran.append(1)
        return await original(*args, **kwargs)

    monkeypatch.setattr(routes.code_executor, "execute_code", counting)

    async def scenario(db, alice, bob):
        qid = await seed_question_and_player(db, alice)
        req = routes.SubmissionCreate(code="def solve(n):\n    return n\n", language="python", question_id=qid)
        async with AsyncExitStack() as stack:
            for _ in range(2):
                await stack.enter_async_context(eg.execution_slot(alice.id))
            for call in (routes.submit_code, routes.run_tests):
                with pytest.raises(HTTPException) as e:
                    await call(req, db=db, current_user=alice)
                assert e.value.status_code == 429
            assert ran == []

        # once the two runs end the same requests go through, and each gives its slot back
        out = await routes.submit_code(req, db=db, current_user=alice)
        await routes.run_tests(req, db=db, current_user=alice)
        assert ran == [1, 1] and out["total_tests"] == 6
        assert await eg.in_flight(alice.id) == 0 and await eg.in_flight() == 0

    run_with_db(tmp_path, scenario)
    assert asyncio.run(get_redis().zcard(eg.ALL_KEY)) == 0
