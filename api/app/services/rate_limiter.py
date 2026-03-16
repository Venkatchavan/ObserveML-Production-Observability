"""In-memory sliding-window rate limiter.

- is_rate_limited(org_id)  — per-org cap on authenticated requests (post-auth)
- is_ip_rate_limited(ip)   — per-IP cap on ALL requests (pre-auth brute-force guard)

Both use the same sliding-window algorithm with a shared Lock.
Redis-backed distributed limiting can replace this for multi-process deploys.
"""

import time
from collections import defaultdict, deque
from threading import Lock
from app.config import settings

_buckets: dict[str, deque] = defaultdict(deque)
_ip_buckets: dict[str, deque] = defaultdict(deque)
_lock = Lock()
_WINDOW_SECONDS = 60.0


def _sliding_window(buckets: dict, key: str, limit: int) -> bool:
    """Return True (i.e. rate-limit) if key exceeds `limit` requests in the last 60 s."""
    now = time.monotonic()
    cutoff = now - _WINDOW_SECONDS
    with _lock:
        bucket = buckets[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            return True
        bucket.append(now)
        return False


def is_rate_limited(org_id: str) -> bool:
    """Per-org rate limit (post-auth). True if org exceeds rate_limit_per_minute."""
    return _sliding_window(_buckets, org_id, settings.rate_limit_per_minute)


def is_ip_rate_limited(ip: str) -> bool:
    """Per-IP rate limit (pre-auth). True if IP exceeds ip_rate_limit_per_minute.

    Protects every endpoint against brute-force API-key guessing and DDoS.
    /health is exempt (handled by the middleware caller).
    """
    return _sliding_window(_ip_buckets, ip, settings.ip_rate_limit_per_minute)
