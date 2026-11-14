"""Question limits and the one-at-a-time lock in shared state (Phase 1 of docs/scaling-plan.md).

The limits and messages are the ones the app has always had; what is new is that two backend processes share them.
Every scenario runs against MemoryRedis and, when COMPILEX_TEST_REDIS_URL is set (CI always sets it), against a real Redis.

Run from the backend folder:  python -m pytest tests/test_rate_limit.py -q
"""

import asyncio
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi import HTTPException

from app.services import rate_limit as rl
from state_helpers import KINDS, run


class Clock:
    """A clock the test moves (rate_limit reads time.time through its own `time` name)."""

    def __init__(self, start=1_000_000.0):
        self.now = start

    def time(self):
        return self.now


@pytest.fixture
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(rl, "time", c)
    return c


@pytest.mark.parametrize("kind", KINDS)
def test_ten_requests_a_minute_then_the_message_the_app_always_gave(kind, clock):
    async def scenario(r):
        for _ in range(10):
            assert await rl.check_rate_limit(1, 10, client=r) == (True, "")
            clock.now += 1
        allowed, message = await rl.check_rate_limit(1, 10, client=r)
        assert allowed is False
        # the first request was 10 seconds ago, so it falls out of the minute in 50 seconds
        assert re.fullmatch(r"Rate limit exceeded\. Try again in (\d+) seconds\.", message) and int(re.search(r"\d+", message).group()) in (49, 50)
        assert await rl.usage(1, client=r) == (10, 10)             # a refused request is not counted

    run(kind, scenario)


@pytest.mark.parametrize("kind", KINDS)
def test_the_minute_window_slides(kind, clock):
    async def scenario(r):
        for _ in range(3):
            await rl.check_rate_limit(1, 3, client=r)
        assert (await rl.check_rate_limit(1, 3, client=r))[0] is False
        clock.now += 59
        assert (await rl.check_rate_limit(1, 3, client=r))[0] is False
        clock.now += 2                                              # all three are now more than a minute old
        assert (await rl.check_rate_limit(1, 3, client=r))[0] is True
        assert await rl.usage(1, client=r) == (4, 1)               # the day still remembers them, the minute does not

    run(kind, scenario)


@pytest.mark.parametrize("kind", KINDS)
def test_the_daily_limit(kind, clock, monkeypatch):
    monkeypatch.setattr(rl, "DAILY_LIMIT", 5)

    async def scenario(r):
        for _ in range(5):
            assert (await rl.check_rate_limit(1, 100, client=r))[0] is True
            clock.now += 120
        assert await rl.check_rate_limit(1, 100, client=r) == (False, "Daily limit reached (5/day). Try again tomorrow.")
        clock.now += 86400                                          # a day on, the earlier requests no longer count
        assert (await rl.check_rate_limit(1, 100, client=r))[0] is True

    run(kind, scenario)


@pytest.mark.parametrize("kind", KINDS)
def test_users_have_their_own_limits(kind, clock):
    async def scenario(r):
        for _ in range(3):
            await rl.check_rate_limit(1, 3, client=r)
        assert (await rl.check_rate_limit(1, 3, client=r))[0] is False
        assert (await rl.check_rate_limit(2, 3, client=r))[0] is True
        assert await rl.usage(2, client=r) == (1, 1) and await rl.usage(3, client=r) == (0, 0)

    run(kind, scenario)


@pytest.mark.parametrize("kind", KINDS)
def test_two_processes_share_one_limit(kind, clock):
    async def scenario(a, b):
        for i in range(6):
            assert (await rl.check_rate_limit(1, 10, client=a if i % 2 else b))[0] is True
        for i in range(4):
            assert (await rl.check_rate_limit(1, 10, client=a if i % 2 else b))[0] is True
        assert (await rl.check_rate_limit(1, 10, client=a))[0] is False and (await rl.check_rate_limit(1, 10, client=b))[0] is False
        assert await rl.usage(1, client=b) == (10, 10)

    run(kind, scenario, clients=2)


@pytest.mark.parametrize("kind", KINDS)
def test_a_burst_of_parallel_requests_cannot_get_past_the_limit(kind):
    """40 requests at the same instant, from two processes: exactly 10 pass. (Without the per-user lock, a real Redis let all 40 through,
    because every request read the count before any of them had added itself.)"""
    async def scenario(a, b):
        results = await asyncio.gather(*[rl.check_rate_limit(1, 10, client=a if i % 2 else b) for i in range(40)])
        return sum(allowed for allowed, _ in results), await rl.usage(1, client=a)

    assert run(kind, scenario, clients=2) == (10, (10, 10))


@pytest.mark.parametrize("kind", KINDS)
def test_a_burst_cannot_pass_the_daily_limit_either(kind, monkeypatch):
    monkeypatch.setattr(rl, "DAILY_LIMIT", 7)

    async def scenario(a, b):
        results = await asyncio.gather(*[rl.check_rate_limit(1, 100, client=a if i % 2 else b) for i in range(30)])
        return sum(allowed for allowed, _ in results)

    assert run(kind, scenario, clients=2) == 7


@pytest.mark.parametrize("kind", KINDS)
def test_a_user_who_cannot_get_the_check_lock_in_time_is_turned_away_not_let_through(kind, monkeypatch):
    async def scenario(a, b):
        async with rl.locked("lock:rl:1", timeout=5, wait=1, client=a):
            real_locked = rl.locked
            monkeypatch.setattr(rl, "locked", lambda name, **kw: real_locked(name, **{**kw, "wait": 0.1}))
            return await rl.check_rate_limit(1, 10, client=b)

    assert run(kind, scenario, clients=2) == (False, "Too many requests at once. Try again in a moment.")


# ── the generation lock ─────────────────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("kind", KINDS)
def test_a_second_request_waits_for_the_first_and_runs_after_it(kind):
    async def scenario(a, b):
        order = []

        async def generate(name, client, pause):
            async with rl.generation_lock(5, client=client):
                order.append(f"{name} start")
                await asyncio.sleep(pause)
                order.append(f"{name} end")

        first = asyncio.create_task(generate("first", a, 0.15))
        await asyncio.sleep(0.03)
        await generate("second", b, 0)                              # arrives from another process while the first is running
        await first
        return order

    assert run(kind, scenario, clients=2) == ["first start", "first end", "second start", "second end"]


@pytest.mark.parametrize("kind", KINDS)
def test_a_request_that_waits_too_long_is_told_to_try_again(kind):
    async def scenario(a, b):
        async with rl.generation_lock(5, client=a):
            with pytest.raises(HTTPException) as caught:
                async with rl.generation_lock(5, wait=0.1, client=b):
                    pass
        assert caught.value.status_code == 429 and "still being generated" in caught.value.detail
        async with rl.generation_lock(5, wait=0.5, client=b):      # and it works again once the first is done
            return "ok"

    assert run(kind, scenario, clients=2) == "ok"


@pytest.mark.parametrize("kind", KINDS)
def test_different_users_generate_at_the_same_time(kind):
    async def scenario(r):
        running, most = [0], [0]

        async def generate(user):
            async with rl.generation_lock(user, client=r):
                running[0] += 1
                most[0] = max(most[0], running[0])
                await asyncio.sleep(0.05)
                running[0] -= 1

        await asyncio.gather(*[generate(u) for u in range(6)])
        return most[0]

    assert run(kind, scenario) == 6


@pytest.mark.parametrize("kind", KINDS)
def test_the_lock_is_given_back_when_generation_fails(kind):
    async def scenario(r):
        with pytest.raises(RuntimeError):
            async with rl.generation_lock(5, client=r):
                raise RuntimeError("the AI service failed")
        async with rl.generation_lock(5, wait=0.2, client=r):
            return "free"

    assert run(kind, scenario) == "free"
