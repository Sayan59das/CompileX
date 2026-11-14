"""Question-generation limits and the one-at-a-time lock, kept in the shared state so they hold across every backend process.

The limits are the ones the app has always had: AI_RATE_LIMIT_PER_MINUTE requests in any 60 seconds and DAILY_LIMIT in any 24 hours, per user,
with the same messages. Each request is a member of two sorted sets scored by its time, and checking-then-counting is done under a short per-user
lock so that parallel requests (from one client or from several processes) cannot all pass a limit that only one of them should.

`client` (every function) is for tests that stand in for several processes; the app uses the process's own shared state.
"""

import secrets
import time
from typing import Optional, Tuple

from fastapi import HTTPException

from app.services.shared_state import LockTimeout, get_redis, locked

DAILY_LIMIT = 100          # questions per user per day
MINUTE = 60.0
DAY = 86400.0
# A generation takes at most the AI service's timeout plus the building of the question; the lock frees itself after this if the holder dies.
GENERATION_LOCK_SECONDS = 90.0
GENERATION_WAIT_EXTRA = 5.0   # a second request waits for the first for this much longer than the lock lasts, then is told to try again


async def _prune(user_id: int, now: float, client=None):
    r = client or get_redis()
    await r.zremrangebyscore(f"rl:min:{user_id}", 0, now - MINUTE)
    await r.zremrangebyscore(f"rl:day:{user_id}", 0, now - DAY)
    return r


async def check_rate_limit(user_id: int, limit_per_minute: int = 10, client=None) -> Tuple[bool, str]:
    """(allowed, message). An allowed call is counted.

    Checking and counting must be one step: with a real Redis every command is a round trip, so 40 simultaneous requests would all read the
    count before any had added itself, and a burst of parallel requests would go straight past the limit. A short lock per user makes the
    step atomic across requests and processes."""
    try:
        async with locked(f"lock:rl:{user_id}", timeout=5.0, wait=5.0, client=client):
            return await _check_and_count(user_id, limit_per_minute, client)
    except LockTimeout:
        return False, "Too many requests at once. Try again in a moment."


async def _check_and_count(user_id: int, limit_per_minute: int, client) -> Tuple[bool, str]:
    now = time.time()
    r = await _prune(user_id, now, client)
    minute_key, day_key = f"rl:min:{user_id}", f"rl:day:{user_id}"

    if await r.zcard(day_key) >= DAILY_LIMIT:
        return False, f"Daily limit reached ({DAILY_LIMIT}/day). Try again tomorrow."
    if await r.zcard(minute_key) >= limit_per_minute:
        oldest = await r.zrange(minute_key, 0, 0, withscores=True)
        wait_seconds = MINUTE - (now - oldest[0][1]) if oldest else MINUTE
        return False, f"Rate limit exceeded. Try again in {int(wait_seconds)} seconds."

    member = f"{now:.6f}:{secrets.token_hex(4)}"
    await r.zadd(minute_key, {member: now})
    await r.zadd(day_key, {member: now})
    await r.expire(minute_key, int(MINUTE) * 2)
    await r.expire(day_key, int(DAY) + 60)
    return True, ""


async def usage(user_id: int, client=None) -> Tuple[int, int]:
    """(requests in the last day, requests in the last minute), without counting anything."""
    r = await _prune(user_id, time.time(), client)
    return await r.zcard(f"rl:day:{user_id}"), await r.zcard(f"rl:min:{user_id}")


class _UserLock:
    """One request of a kind at a time for a user, across every process. A second request waits for the first (as it always did); if that takes
    longer than `wait` seconds, it is told to try again."""

    KIND = ""
    MESSAGE = ""

    def __init__(self, user_id: int, wait: Optional[float] = None, client=None):
        self._cm = locked(
            f"lock:{self.KIND}:{user_id}", timeout=GENERATION_LOCK_SECONDS,
            wait=GENERATION_LOCK_SECONDS + GENERATION_WAIT_EXTRA if wait is None else wait, client=client,
        )

    async def __aenter__(self):
        try:
            await self._cm.__aenter__()
        except LockTimeout:
            raise HTTPException(status_code=429, detail=self.MESSAGE)
        return self

    async def __aexit__(self, *exc):
        return await self._cm.__aexit__(*exc)


class generation_lock(_UserLock):
    """`async with generation_lock(user_id):` lets one question be generated at a time for a user."""

    KIND = "gen"
    MESSAGE = "Your previous question is still being generated. Try again in a moment."


class assessment_lock(_UserLock):
    """`async with assessment_lock(user_id):` handles one skill-assessment request at a time for a player, so a double click cannot grade a
    question twice."""

    KIND = "assess"
    MESSAGE = "Your previous assessment request is still being handled. Try again in a moment."
