"""Limits on sign-in, sign-up and password-reset requests, kept in the shared state so they hold across every backend process.

Nothing used to stop a script from trying passwords or reset codes all day, or from creating accounts without end. Each attempt is a member of a
sorted set scored by its time (a sliding window), and check-then-count is one step under a short lock so parallel requests cannot all slip
under a limit that only some of them should (the same technique as services/rate_limit.py).

`client` (every function) is for tests; the app uses the process's own shared state.
"""

import secrets
import time
from typing import Tuple

from fastapi import HTTPException, Request

from app.core.config import get_settings
from app.services.shared_state import LockTimeout, get_redis, locked

settings = get_settings()


def client_ip(request: Request) -> str:
    """The address the request really came from.

    Behind a proxy (Render) every request arrives from the proxy, so `request.client.host` is the same for everybody and per-address limits would
    throttle the whole site together. With TRUSTED_PROXY_HOPS = N the Nth address from the right of X-Forwarded-For is used: the proxy adds
    what it saw to the END of that header, so the right-hand entries are the trustworthy ones, and anything a caller puts on the left is ignored.
    With 0 (the default, for local runs) the header is never read, so it cannot be used to dodge a limit."""
    hops = settings.TRUSTED_PROXY_HOPS
    if hops > 0:
        parts = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
        if len(parts) >= hops:
            return parts[-hops]
    return request.client.host if request.client else "unknown"


def _key(bucket: str, key: str) -> str:
    return f"al:{bucket}:{key}"[:200]


async def _count(r, key: str, window: float, now: float) -> Tuple[int, float]:
    """(attempts inside the window, seconds until the oldest one leaves it)."""
    await r.zremrangebyscore(key, 0, now - window)
    n = await r.zcard(key)
    oldest = await r.zrange(key, 0, 0, withscores=True) if n else []
    return n, (window - (now - oldest[0][1])) if oldest else 0.0


def _too_many(retry_after: float) -> HTTPException:
    seconds = max(1, int(retry_after) + 1)
    return HTTPException(
        status_code=429, detail=f"Too many attempts. Try again in {seconds} seconds.", headers={"Retry-After": str(seconds)},
    )


async def enforce(bucket: str, key: str, limit: int, window: float, client=None) -> None:
    """Count one attempt, or raise 429 when `limit` attempts are already inside the last `window` seconds."""
    r = client or get_redis()
    name = _key(bucket, key)
    try:
        async with locked(f"lock:{name}", timeout=5.0, wait=5.0, client=r):
            now = time.time()
            n, wait = await _count(r, name, window, now)
            if n >= limit:
                raise _too_many(wait)
            await r.zadd(name, {f"{now:.6f}:{secrets.token_hex(4)}": now})
            await r.expire(name, int(window) + 60)
    except LockTimeout:
        raise _too_many(1)


async def check(bucket: str, key: str, limit: int, window: float, client=None) -> None:
    """Raise 429 when `limit` attempts are already inside the window, without counting this one (it is counted by `record` if it fails)."""
    r = client or get_redis()
    n, wait = await _count(r, _key(bucket, key), window, time.time())
    if n >= limit:
        raise _too_many(wait)


async def record(bucket: str, key: str, window: float, client=None) -> None:
    """Count one (failed) attempt."""
    r = client or get_redis()
    name = _key(bucket, key)
    now = time.time()
    await r.zadd(name, {f"{now:.6f}:{secrets.token_hex(4)}": now})
    await r.expire(name, int(window) + 60)
