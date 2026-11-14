"""Who may run code right now (the host-independent part of Phase 2 in docs/scaling-plan.md).

`MAX_CONCURRENT_EXECUTIONS` caps the sandboxes running on one machine; the rest wait in line. Without more, one player could fill the whole line
(Run pressed in a loop, or a script) and everyone else would wait behind them, and the line could grow without limit while the sandboxes are busy.
This gate sits in front of that line and is kept in the shared state, so it holds across every backend process:

- a player may have at most `MAX_EXECUTIONS_PER_USER` submissions running or waiting; one more is refused with 429;
- at most `MAX_EXECUTION_BACKLOG` submissions may be running or waiting in all; one more is refused with 429 and a Retry-After header, which is
  better for everyone than a wait of minutes that ends in a timeout.

An entry is a member of two sorted sets scored by its time, removed when the run ends. If a process dies mid-run its entries stay, so every
check first drops entries older than `ENTRY_SECONDS`: the gate heals itself and never needs cleaning by hand.

The per-user check and the adding of an entry run under a short per-user lock, so parallel requests of one player cannot all pass a limit that
only some of them should (the same reason as in rate_limit.py). The total is checked inside that lock but is shared by every player, so it is a
soft cap: simultaneous admissions of different players can overshoot it by up to the number of players admitted in the same instant. That is
fine for a backlog limit, and a global lock on every submission would cost more than the overshoot does.

`client` is for tests that stand in for several processes; the app uses the process's own shared state.
"""

import secrets
import time
from typing import Optional

from fastapi import HTTPException

from app.core.config import get_settings
from app.services.shared_state import LockTimeout, get_redis, locked

ALL_KEY = "exec:all"
# Longer than the longest honest wait plus run (a full line of MAX_EXECUTION_BACKLOG submissions at a few seconds each, over MAX_CONCURRENT_EXECUTIONS
# sandboxes), shorter than a player's patience for a stuck process.
ENTRY_SECONDS = 300.0
USER_RETRY_SECONDS = 2
BUSY_RETRY_SECONDS = 5


def _refuse(message: str, retry_after: int) -> HTTPException:
    return HTTPException(status_code=429, detail=message, headers={"Retry-After": str(retry_after)})


class execution_slot:
    """`async with execution_slot(user_id):` around a code run. Raises HTTPException(429) when the player or the whole line is full."""

    def __init__(self, user_id, per_user: Optional[int] = None, backlog: Optional[int] = None, client=None):
        self.user_id = user_id
        settings = get_settings()
        self.per_user = max(1, settings.MAX_EXECUTIONS_PER_USER if per_user is None else per_user)
        self.backlog = max(1, settings.MAX_EXECUTION_BACKLOG if backlog is None else backlog)
        self._client = client
        self._redis = None
        self._token: Optional[str] = None

    @property
    def _user_key(self) -> str:
        return f"exec:user:{self.user_id}"

    async def __aenter__(self):
        r = self._client or get_redis()
        now = time.time()
        token = f"{now:.6f}:{secrets.token_hex(4)}"
        try:
            async with locked(f"lock:exec:{self.user_id}", timeout=5.0, wait=5.0, client=self._client):
                await r.zremrangebyscore(self._user_key, 0, now - ENTRY_SECONDS)
                await r.zremrangebyscore(ALL_KEY, 0, now - ENTRY_SECONDS)
                mine = await r.zcard(self._user_key)
                if mine >= self.per_user:
                    raise _refuse(
                        f"You already have {mine} submission{'s' if mine != 1 else ''} running. Wait for one to finish, then try again.",
                        USER_RETRY_SECONDS,
                    )
                waiting = await r.zcard(ALL_KEY)
                if waiting >= self.backlog:
                    raise _refuse(
                        f"The judges are busy: {waiting} submissions are running or waiting. Try again in a few seconds.",
                        BUSY_RETRY_SECONDS,
                    )
                await r.zadd(self._user_key, {token: now})
                await r.zadd(ALL_KEY, {token: now})
                await r.expire(self._user_key, int(ENTRY_SECONDS) + 60)
                await r.expire(ALL_KEY, int(ENTRY_SECONDS) + 60)
        except LockTimeout:
            raise _refuse("Too many requests at once. Try again in a moment.", USER_RETRY_SECONDS)
        self._redis, self._token = r, token
        return self

    async def __aexit__(self, *exc):
        # Best effort: the run is over and its result is what the player needs. An entry that is not removed here is dropped after ENTRY_SECONDS.
        try:
            await self._redis.zrem(self._user_key, self._token)
            await self._redis.zrem(ALL_KEY, self._token)
        except Exception as e:
            print(f"[ExecutionGate] could not release a slot for user {self.user_id}: {e}")
        return False


async def in_flight(user_id=None, client=None) -> int:
    """How many submissions are running or waiting (for one player, or in all), without changing anything."""
    r = client or get_redis()
    return await r.zcard(f"exec:user:{user_id}" if user_id is not None else ALL_KEY)
