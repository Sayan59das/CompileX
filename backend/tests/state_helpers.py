"""Run a scenario against the in-process stand-in for Redis and against a real Redis, so the two cannot drift apart.

The real Redis is the one in COMPILEX_TEST_REDIS_URL. Its database is emptied before and after every scenario, so the URL must name database 15
(redis://host:6379/15): a URL for any other database is refused rather than flushed. CI starts a Redis service; locally start one and set it.
"""

import asyncio
import os

import pytest

from app.services.shared_state import MemoryRedis

REDIS_URL = os.environ.get("COMPILEX_TEST_REDIS_URL", "")

KINDS = [
    "memory",
    pytest.param("redis", marks=pytest.mark.skipif(not REDIS_URL, reason="set COMPILEX_TEST_REDIS_URL (a redis URL ending in /15) to run against a real Redis")),
]


def run(kind, scenario, clients=1):
    """Run `scenario(client, ...)` in a fresh event loop with `clients` clients that share one store (like `clients` backend processes do)."""
    async def main():
        if kind == "memory":
            shared = MemoryRedis()
            return await scenario(*([shared] * clients))
        assert REDIS_URL.rstrip("/").endswith("/15"), "COMPILEX_TEST_REDIS_URL must name database 15: the tests empty it"
        import redis.asyncio as aioredis

        made = [aioredis.from_url(REDIS_URL, decode_responses=True) for _ in range(clients)]
        await made[0].flushdb()
        try:
            return await scenario(*made)
        finally:
            await made[0].flushdb()
            for client in made:
                await client.aclose()

    return asyncio.run(main())
