"""
Small in-process TTL cache with single-flight (Phase 7d).

Generalizes the pattern already used in api/analytics.py so the expensive
mirror/portfolio reconstructions (O(trades) per request) aren't recomputed on
every view. Values are plain dicts (no DB/session references), so caching the
result is safe across requests. Per-key locking prevents a thundering herd when
a hot key expires.

In-process (not Redis) on purpose: it's dependency-free and each API worker
gets its own cache; a stale entry is at most `ttl` old, which is fine because
congressional trades ingest on a daily cadence.
"""

import asyncio
import time
from typing import Any, Awaitable, Callable, Dict, Tuple

_CACHE: Dict[str, Tuple[float, Any]] = {}
_LOCKS: Dict[str, asyncio.Lock] = {}


async def cached(key: str, fn: Callable[[], Awaitable[Any]], ttl: int = 900) -> Any:
    """Return the cached value for ``key`` or compute it via ``fn`` (single-flight)."""
    hit = _CACHE.get(key)
    if hit and hit[0] > time.time():
        return hit[1]

    lock = _LOCKS.setdefault(key, asyncio.Lock())
    async with lock:
        # Re-check: another coroutine may have filled it while we waited.
        hit = _CACHE.get(key)
        if hit and hit[0] > time.time():
            return hit[1]
        data = await fn()
        _CACHE[key] = (time.time() + ttl, data)
        return data


def invalidate(prefix: str = "") -> int:
    """Drop cache entries whose key starts with ``prefix`` (all if empty). Returns count."""
    keys = [k for k in _CACHE if k.startswith(prefix)]
    for k in keys:
        _CACHE.pop(k, None)
    return len(keys)
