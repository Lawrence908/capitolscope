"""
Shared, Redis-backed cache for the expensive read-only analytics/signals
computes (Scrutiny dashboard + machine-facing Signals feed).

Why this exists
---------------
Every one of these engines aggregates over the whole ``congressional_trades``
table. The API runs on a different host than the Supabase-hosted Postgres, so
each of those rows is billable *egress*. Previously each router kept its own
in-process TTL cache and a warmer loop that recomputed every 10-25 minutes; on
a single worker that is still ~1.4k full-table scans a day, and every deploy
threw the cache away and cold-recomputed everything again.

This module gives both routers **one cache, shared in Redis**:

  - values survive restarts/deploys (no cold re-warm storm),
  - a single warm populates the key for every worker and every request,
  - a process-local memo keeps hot reads off Redis entirely.

It is deliberately defensive: if Redis is unavailable the helper degrades to a
process-local cache + direct compute, so the API never breaks on a cache fault.

Stale-while-revalidate: values carry a *soft* expiry (``ttl``) and a longer Redis
*hard* expiry. Past the soft expiry the stale payload is served immediately and
a single background recompute refreshes it, so no request ever blocks on a cold
engine once the key has been warmed once.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# process-local memo:  full_key -> (soft_expires_at, data)
_LOCAL: Dict[str, Tuple[float, Any]] = {}
# collapse concurrent cold computes / background refreshes to one per key
_LOCKS: Dict[str, asyncio.Lock] = {}
_REFRESHING: Set[str] = set()

# The Redis hard TTL is a multiple of the soft TTL so a briefly-dead warmer
# still leaves a (stale but serveable) value to revalidate from.
_HARD_TTL_FACTOR = 3

_redis_client = None
_redis_disabled = False


def _get_redis():
    """Lazily build one asyncio Redis client for this process, bound to the
    running loop. Returns None if Redis is unavailable/misconfigured (the cache
    then runs process-local only)."""
    global _redis_client, _redis_disabled
    if _redis_disabled:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        import redis.asyncio as aioredis  # local import: optional dependency path
        from core.config import get_settings

        _redis_client = aioredis.from_url(
            get_settings().redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
            encoding="utf-8",
            decode_responses=True,
        )
        return _redis_client
    except Exception as exc:  # noqa: BLE001
        logger.warning("analytics cache: Redis unavailable, using local cache only: %s", exc)
        _redis_disabled = True
        return None


def _full_key(namespace: str, key: str) -> str:
    return f"{namespace}:cache:{key}"


def _serialise(soft_expires: float, data: Any) -> str:
    # default=str is a safety net for stray Decimal/UUID/date values; the
    # engines already emit isoformatted strings and rounded floats.
    return json.dumps({"exp": soft_expires, "data": data}, default=str)


async def _redis_get(rkey: str) -> Optional[Tuple[float, Any]]:
    client = _get_redis()
    if client is None:
        return None
    try:
        raw = await client.get(rkey)
    except Exception as exc:  # noqa: BLE001
        logger.warning("analytics cache: Redis GET failed for %s: %s", rkey, exc)
        return None
    if not raw:
        return None
    try:
        obj = json.loads(raw)
        return float(obj["exp"]), obj["data"]
    except Exception:  # noqa: BLE001 - poisoned/legacy value: treat as a miss
        return None


async def _redis_set(rkey: str, soft_expires: float, data: Any, ttl: int) -> None:
    client = _get_redis()
    if client is None:
        return
    try:
        await client.set(rkey, _serialise(soft_expires, data), ex=ttl * _HARD_TTL_FACTOR)
    except Exception as exc:  # noqa: BLE001
        logger.warning("analytics cache: Redis SET failed for %s: %s", rkey, exc)


async def _compute_and_store(rkey: str, fn: Callable[[], Any], ttl: int) -> Any:
    data = await asyncio.to_thread(fn)
    soft = time.time() + ttl
    _LOCAL[rkey] = (soft, data)
    await _redis_set(rkey, soft, data, ttl)
    return data


def _refresh_in_background(rkey: str, fn: Callable[[], Any], ttl: int) -> None:
    """Recompute a soft-expired key without blocking the caller (single-flight)."""
    if rkey in _REFRESHING:
        return
    _REFRESHING.add(rkey)

    async def _run():
        try:
            await _compute_and_store(rkey, fn, ttl)
        except Exception:  # noqa: BLE001
            logger.exception("analytics cache: background refresh failed for %s", rkey)
        finally:
            _REFRESHING.discard(rkey)

    asyncio.create_task(_run())


async def cached(key: str, fn: Callable[[], Any], *, ttl: int, namespace: str = "analytics") -> Any:
    """Return ``fn()``'s result, memoised in Redis (shared) and in-process.

    ``fn`` is a *synchronous* callable (it opens a sync DB session); it is run in
    a threadpool. ``ttl`` is the soft expiry in seconds; the Redis entry lives
    ``_HARD_TTL_FACTOR``x longer so stale-while-revalidate has something to serve.
    """
    rkey = _full_key(namespace, key)
    now = time.time()

    # 1. process-local fast path (fresh)
    local = _LOCAL.get(rkey)
    if local and local[0] > now:
        return local[1]

    # 2. shared Redis
    remote = await _redis_get(rkey)
    if remote is not None:
        soft, data = remote
        _LOCAL[rkey] = (soft, data)
        if soft > now:
            return data  # fresh
        # stale: serve immediately, refresh in the background
        _refresh_in_background(rkey, fn, ttl)
        return data

    # 3. cold everywhere: compute under a per-key lock so concurrent callers
    #    share one in-flight compute instead of stampeding the DB.
    lock = _LOCKS.setdefault(rkey, asyncio.Lock())
    async with lock:
        local = _LOCAL.get(rkey)
        if local and local[0] > now:
            return local[1]
        remote = await _redis_get(rkey)
        if remote is not None and remote[0] > now:
            _LOCAL[rkey] = remote
            return remote[1]
        return await _compute_and_store(rkey, fn, ttl)


async def invalidate(key: str, namespace: str = "analytics") -> None:
    """Drop a key from both tiers (e.g. after the daily import lands new data)."""
    rkey = _full_key(namespace, key)
    _LOCAL.pop(rkey, None)
    client = _get_redis()
    if client is not None:
        try:
            await client.delete(rkey)
        except Exception as exc:  # noqa: BLE001
            logger.warning("analytics cache: Redis DEL failed for %s: %s", rkey, exc)
