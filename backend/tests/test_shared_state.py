"""The shared-state layer: the stand-in for Redis behaves like Redis, and the lock really excludes (Phase 1 of docs/scaling-plan.md).

Every scenario runs against MemoryRedis and, when COMPILEX_TEST_REDIS_URL is set (CI always sets it), against a real Redis.

Run from the backend folder:  python -m pytest tests/test_shared_state.py -q
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.services import shared_state as ss
from state_helpers import KINDS, run


@pytest.mark.parametrize("kind", KINDS)
def test_values_expire_and_set_clears_an_earlier_expiry(kind):
    async def scenario(r):
        await r.set("a", "1", px=60)
        assert await r.get("a") == "1" and await r.exists("a") == 1
        await asyncio.sleep(0.12)
        assert await r.get("a") is None and await r.exists("a") == 0
        await r.set("b", "x", px=60)
        await r.set("b", "y")                 # a plain SET removes the expiry
        await asyncio.sleep(0.12)
        assert await r.get("b") == "y"
        await r.set("c", 5)                   # values come back as text
        assert await r.get("c") == "5"

    run(kind, scenario)


@pytest.mark.parametrize("kind", KINDS)
def test_set_nx_only_sets_a_missing_key_and_delete_counts_what_it_removed(kind):
    async def scenario(r):
        assert await r.set("k", "first", nx=True) is True
        assert not await r.set("k", "second", nx=True)
        assert await r.get("k") == "first"
        assert await r.delete("k", "never-existed") == 1
        assert await r.delete("k") == 0
        assert await r.mget(["k", "nope"]) == [None, None]
        await r.set("x", "1")
        await r.set("y", "2")
        assert await r.mget(["x", "missing", "y"]) == ["1", None, "2"]

    run(kind, scenario)


@pytest.mark.parametrize("kind", KINDS)
def test_expire_applies_to_an_existing_key_only(kind):
    async def scenario(r):
        assert await r.expire("ghost", 10) is False
        await r.set("k", "v")
        assert await r.expire("k", 1) is True

    run(kind, scenario)


@pytest.mark.parametrize("kind", KINDS)
def test_sets(kind):
    async def scenario(r):
        assert await r.sadd("s", 1, 2, 3) == 3
        assert await r.sadd("s", 3, 4) == 1
        assert await r.smembers("s") == {"1", "2", "3", "4"}
        assert await r.srem("s", 1, 99) == 1
        assert await r.smembers("s") == {"2", "3", "4"}
        assert await r.srem("s", 2, 3, 4) == 3
        assert await r.smembers("s") == set() and await r.exists("s") == 0
        assert await r.smembers("never") == set() and await r.srem("never", 1) == 0

    run(kind, scenario)


@pytest.mark.parametrize("kind", KINDS)
def test_sorted_sets(kind):
    async def scenario(r):
        assert await r.zadd("z", {"a": 1.0, "b": 3.0, "c": 2.0}) == 3
        assert await r.zadd("z", {"b": 5.0, "d": 4.0}) == 1            # b is moved, d is new
        assert await r.zcard("z") == 4
        assert await r.zrange("z", 0, -1) == ["a", "c", "d", "b"]
        assert await r.zrange("z", 0, 0, withscores=True) == [("a", 1.0)]
        assert await r.zremrangebyscore("z", 0, 2.5) == 2
        assert await r.zrange("z", 0, -1) == ["d", "b"]
        assert await r.zremrangebyscore("z", 0, 100) == 2
        assert await r.zcard("z") == 0 and await r.exists("z") == 0
        assert await r.zrange("never", 0, 0, withscores=True) == []

    run(kind, scenario)


# ── the lock ────────────────────────────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("kind", KINDS)
def test_the_lock_keeps_read_modify_write_from_losing_updates_across_clients(kind):
    """Two clients (two backend processes) each add 1 to a counter 30 times with a pause between the read and the write. Without mutual
    exclusion updates are lost; with the lock the total is exact."""
    async def scenario(a, b):
        await a.set("counter", 0)

        async def bump(client):
            async with ss.locked("lock:counter", timeout=5, wait=20, client=client):
                value = int(await client.get("counter"))
                await asyncio.sleep(0.001)
                await client.set("counter", value + 1)

        await asyncio.gather(*([bump(a) for _ in range(30)] + [bump(b) for _ in range(30)]))
        return int(await a.get("counter"))

    assert run(kind, scenario, clients=2) == 60


@pytest.mark.parametrize("kind", KINDS)
def test_the_unlocked_version_does_lose_updates(kind):
    """The control for the test above: the same code without the lock loses updates, so that test really measures the lock."""
    async def scenario(a, b):
        await a.set("counter", 0)

        async def bump(client):
            value = int(await client.get("counter"))
            await asyncio.sleep(0.001)
            await client.set("counter", value + 1)

        await asyncio.gather(*([bump(a) for _ in range(30)] + [bump(b) for _ in range(30)]))
        return int(await a.get("counter"))

    assert run(kind, scenario, clients=2) < 60


@pytest.mark.parametrize("kind", KINDS)
def test_a_lock_that_cannot_be_taken_in_time_raises_lock_timeout(kind):
    async def scenario(a, b):
        async with ss.locked("lock:busy", timeout=5, wait=1, client=a):
            with pytest.raises(ss.LockTimeout):
                async with ss.locked("lock:busy", timeout=5, wait=0.1, client=b):
                    pass
        async with ss.locked("lock:busy", timeout=5, wait=0.5, client=b):   # free again once the holder left
            return "taken"

    assert run(kind, scenario, clients=2) == "taken"


@pytest.mark.parametrize("kind", KINDS)
def test_a_lock_whose_holder_died_frees_itself(kind):
    async def scenario(a, b):
        dead = a.lock("lock:orphan", timeout=0.15, blocking_timeout=1)
        assert await dead.acquire()          # taken and never released: the process that held it is gone
        async with ss.locked("lock:orphan", timeout=5, wait=2, client=b):
            return "taken after expiry"

    assert run(kind, scenario, clients=2) == "taken after expiry"


@pytest.mark.parametrize("kind", KINDS)
def test_the_lock_is_released_when_the_body_raises(kind):
    async def scenario(a, b):
        with pytest.raises(ValueError):
            async with ss.locked("lock:err", timeout=5, wait=1, client=a):
                raise ValueError("boom")
        async with ss.locked("lock:err", timeout=5, wait=0.2, client=b):
            return "free"

    assert run(kind, scenario, clients=2) == "free"


@pytest.mark.parametrize("kind", KINDS)
def test_locks_with_different_names_do_not_wait_for_each_other(kind):
    async def scenario(r):
        async with ss.locked("lock:one", timeout=5, wait=1, client=r):
            async with ss.locked("lock:two", timeout=5, wait=0.1, client=r):
                return "both held"

    assert run(kind, scenario) == "both held"


# ── choosing the client ─────────────────────────────────────────────────────────────────────────────────────────────────────

def test_without_redis_url_the_state_is_held_in_this_process(monkeypatch):
    monkeypatch.setattr(ss.settings, "REDIS_URL", "")
    ss.set_redis(None)
    try:
        assert not ss.shared_mode() and isinstance(ss.get_redis(), ss.MemoryRedis) and ss.get_redis() is ss.get_redis()
    finally:
        ss.set_redis(None)


def test_with_redis_url_the_state_is_a_real_redis_client(monkeypatch):
    import redis.asyncio as aioredis

    monkeypatch.setattr(ss.settings, "REDIS_URL", "redis://localhost:6379/0")
    ss.set_redis(None)
    try:
        assert ss.shared_mode() and isinstance(ss.get_redis(), aioredis.Redis)
    finally:
        ss.set_redis(None)


def test_memory_redis_expiry_follows_its_clock():
    now = [1000.0]
    store = ss.MemoryRedis(clock=lambda: now[0])

    async def main():
        await store.set("k", "v", ex=10)
        now[0] += 9
        assert await store.get("k") == "v"
        now[0] += 2
        assert await store.get("k") is None

    asyncio.run(main())
