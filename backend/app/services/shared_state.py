"""State that must be shared by every backend process: one client for it, a lock, and a stand-in for when there is only one process.

With REDIS_URL set, `get_redis()` is a real redis.asyncio client and every process sees the same lobbies, limits and locks. Without it, it is a
`MemoryRedis`: the same calls, held in this process. The code that uses it is identical in both cases, so single-process mode (development,
the default) runs exactly what production runs, and the tests exercise it without a server.

`MemoryRedis` implements only the commands this app uses; tests run the same scenarios against it and against a real Redis so the two cannot drift.
"""

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Optional

from app.core.config import get_settings

settings = get_settings()


class LockTimeout(Exception):
    """A lock could not be taken within the time allowed."""


class MemoryRedis:
    """The Redis commands this app uses, with Redis's behaviour (values are strings, a key can expire, SET NX, locks that time out)."""

    def __init__(self, clock=time.time):
        self._clock = clock
        self._values: Dict[str, object] = {}
        self._expiry: Dict[str, float] = {}
        self._held: Dict[str, tuple] = {}   # lock name -> (token, expires_at or None)

    # ── keys ──
    def _live(self, key: str) -> bool:
        at = self._expiry.get(key)
        if at is not None and at <= self._clock():
            self._values.pop(key, None)
            self._expiry.pop(key, None)
        return key in self._values

    async def get(self, key):
        return self._values[key] if self._live(key) else None

    async def mget(self, keys):
        return [self._values[k] if self._live(k) else None for k in keys]

    async def set(self, key, value, ex=None, px=None, nx=False):
        if nx and self._live(key):
            return None
        self._values[key] = value if isinstance(value, str) else str(value)
        self._expiry.pop(key, None)   # SET clears any earlier expiry, as in Redis
        if ex is not None:
            self._expiry[key] = self._clock() + ex
        elif px is not None:
            self._expiry[key] = self._clock() + px / 1000.0
        return True

    async def delete(self, *keys):
        removed = 0
        for key in keys:
            if self._live(key):
                del self._values[key]
                self._expiry.pop(key, None)
                removed += 1
        return removed

    async def exists(self, *keys):
        return sum(1 for k in keys if self._live(k))

    async def expire(self, key, seconds):
        if not self._live(key):
            return False
        self._expiry[key] = self._clock() + seconds
        return True

    # ── sets ──
    async def sadd(self, key, *members):
        members = {str(m) for m in members}
        self._live(key)   # forget the key first if it has expired
        current = self._values.setdefault(key, set())
        added = len(members - current)
        current |= members
        return added

    async def srem(self, key, *members):
        if not self._live(key):
            return 0
        current = self._values[key]
        gone = {str(m) for m in members} & current
        current -= gone
        if not current:
            self._values.pop(key, None)
            self._expiry.pop(key, None)
        return len(gone)

    async def smembers(self, key):
        return set(self._values[key]) if self._live(key) else set()

    # ── sorted sets ──
    async def zadd(self, key, mapping):
        self._live(key)   # forget the key first if it has expired
        zset = self._values.setdefault(key, {})
        added = sum(1 for m in mapping if str(m) not in zset)
        zset.update({str(m): float(s) for m, s in mapping.items()})
        return added

    async def zremrangebyscore(self, key, low, high):
        if not self._live(key):
            return 0
        zset = self._values[key]
        low = float("-inf") if low == "-inf" else float(low)
        high = float("inf") if high == "+inf" else float(high)
        gone = [m for m, s in zset.items() if low <= s <= high]
        for m in gone:
            del zset[m]
        if not zset:
            self._values.pop(key, None)
            self._expiry.pop(key, None)
        return len(gone)

    async def zcard(self, key):
        return len(self._values[key]) if self._live(key) else 0

    async def zrange(self, key, start, stop, withscores=False):
        if not self._live(key):
            return []
        ordered = sorted(self._values[key].items(), key=lambda item: (item[1], item[0]))
        stop = len(ordered) if stop == -1 else stop + 1
        part = ordered[start:stop]
        return [(m, s) for m, s in part] if withscores else [m for m, _ in part]

    # ── locks ──
    def lock(self, name, timeout=None, blocking_timeout=None, sleep=0.005):
        return _MemoryLock(self, name, timeout, blocking_timeout, sleep)

    async def aclose(self):
        return None


class _MemoryLock:
    """redis.asyncio's Lock as far as this app uses it: acquire() waits up to blocking_timeout, release() only by the holder, and a lock
    that was not released within `timeout` seconds can be taken by someone else."""

    def __init__(self, store: MemoryRedis, name, timeout, blocking_timeout, sleep):
        self._store, self._name, self._timeout, self._wait, self._sleep = store, name, timeout, blocking_timeout, sleep
        self._token = uuid.uuid4().hex

    async def acquire(self):
        clock = self._store._clock
        deadline = None if self._wait is None else clock() + self._wait
        while True:
            held = self._store._held.get(self._name)
            if held is None or (held[1] is not None and held[1] <= clock()):
                self._store._held[self._name] = (self._token, None if self._timeout is None else clock() + self._timeout)
                return True
            if deadline is not None and clock() >= deadline:
                return False
            await asyncio.sleep(self._sleep)

    async def release(self):
        held = self._store._held.get(self._name)
        if held is None or held[0] != self._token:
            raise RuntimeError("cannot release a lock that is not owned (it expired and someone else took it)")
        del self._store._held[self._name]


_client = None


def shared_mode() -> bool:
    """True when REDIS_URL is set, so state is shared between backend processes."""
    return bool((settings.REDIS_URL or "").strip())


def get_redis():
    """The one client of this process: a real Redis when REDIS_URL is set, else an in-process stand-in."""
    global _client
    if _client is None:
        if shared_mode():
            import redis.asyncio as aioredis

            _client = aioredis.from_url(settings.REDIS_URL.strip(), decode_responses=True, health_check_interval=30, socket_keepalive=True)
        else:
            _client = MemoryRedis()
    return _client


def set_redis(client) -> None:
    """Use this client from now on (tests; None forgets the current one so the next get_redis() builds it again)."""
    global _client
    _client = client


@asynccontextmanager
async def locked(name: str, timeout: float = 10.0, wait: float = 10.0, client=None):
    """Hold the lock `name` for the body: waits up to `wait` seconds for it (LockTimeout after that); it frees itself after `timeout` seconds
    if the holder dies. Mutual exclusion across every process that shares the Redis."""
    lock = (client or get_redis()).lock(name, timeout=timeout, blocking_timeout=wait)
    if not await lock.acquire():
        raise LockTimeout(f"could not take the lock {name} within {wait} seconds")
    try:
        yield
    finally:
        try:
            await lock.release()
        except Exception as exc:   # the lock outlived `timeout` and was taken by someone else; nothing left to release
            print(f"[state] lock {name} was not released cleanly: {exc}")
