"""
Tests for the in-process TTL + single-flight cache (core.cache, Phase 7d).
"""

import asyncio
import time

import pytest

import schemas  # noqa: F401  (resolve circular-import ordering)
from core import cache

pytestmark = pytest.mark.unit


class TestCached:
    @pytest.mark.asyncio
    async def test_computes_once_within_ttl(self):
        calls = {"n": 0}

        async def fn():
            calls["n"] += 1
            return {"v": calls["n"]}

        cache.invalidate("t:")
        r1 = await cache.cached("t:k", fn, ttl=60)
        r2 = await cache.cached("t:k", fn, ttl=60)
        assert r1 == r2 == {"v": 1}
        assert calls["n"] == 1

    @pytest.mark.asyncio
    async def test_expired_key_recomputes(self):
        calls = {"n": 0}

        async def fn():
            calls["n"] += 1
            return calls["n"]

        cache.invalidate("t2:")
        await cache.cached("t2:k", fn, ttl=0)  # ttl=0 -> already expired
        await asyncio.sleep(0.01)
        await cache.cached("t2:k", fn, ttl=0)
        assert calls["n"] == 2

    @pytest.mark.asyncio
    async def test_single_flight_under_concurrency(self):
        calls = {"n": 0}

        async def slow():
            calls["n"] += 1
            await asyncio.sleep(0.05)
            return "x"

        cache.invalidate("t3:")
        results = await asyncio.gather(*[cache.cached("t3:k", slow, ttl=60) for _ in range(10)])
        assert all(r == "x" for r in results)
        assert calls["n"] == 1  # 10 concurrent callers, computed once


def test_invalidate_by_prefix():
    now = time.time() + 100
    cache._CACHE["p:a"] = (now, 1)
    cache._CACHE["p:b"] = (now, 2)
    cache._CACHE["q:c"] = (now, 3)
    assert cache.invalidate("p:") == 2
    assert "q:c" in cache._CACHE
    assert "p:a" not in cache._CACHE
