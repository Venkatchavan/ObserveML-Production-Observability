"""OB-55: ClickHouse query result caching via Redis (60s TTL, fail-open).

Fail-open contract: any Redis error returns None (cache miss); the caller
falls through to the live ClickHouse query.  The dashboard is always
correct — at worst slightly stale.

333-Line Law: this file is intentionally < 70 lines.
"""

import hashlib
import json
import logging
from typing import Any, Optional

log = logging.getLogger(__name__)

try:
    import redis.asyncio as aioredis  # type: ignore[import]

    _redis_available = True
except ImportError:
    _redis_available = False

_pool: Optional[Any] = None


def _make_key(org_id: str, route: str, params: dict) -> str:
    payload = json.dumps({"org_id": org_id, "route": route, "params": params}, sort_keys=True)
    return "observeml:cache:" + hashlib.sha256(payload.encode()).hexdigest()[:24]


async def _get_pool(redis_url: str) -> Optional[Any]:
    global _pool
    if _pool is None and _redis_available and redis_url:
        try:
            _pool = aioredis.from_url(redis_url, decode_responses=True)
        except Exception as exc:
            log.warning("Redis init failed (fail-open): %s", exc)
    return _pool


async def cache_get(redis_url: str, org_id: str, route: str, params: dict) -> Optional[Any]:
    pool = await _get_pool(redis_url)
    if pool is None:
        return None
    try:
        raw = await pool.get(_make_key(org_id, route, params))
        return json.loads(raw) if raw else None
    except Exception as exc:
        log.debug("Cache get miss (fail-open): %s", exc)
        return None


async def cache_set(
    redis_url: str,
    org_id: str,
    route: str,
    params: dict,
    value: Any,
    ttl: int = 60,
) -> None:
    pool = await _get_pool(redis_url)
    if pool is None:
        return
    try:
        await pool.set(_make_key(org_id, route, params), json.dumps(value), ex=ttl)
    except Exception as exc:
        log.debug("Cache set failed (fail-open): %s", exc)
