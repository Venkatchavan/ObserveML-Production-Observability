"""In-memory sliding-window rate limiter (OB-09).

reason: Redis-backed limiter deferred to Sprint 2. In-memory is
sufficient for single-process v1 and keeps Sprint 1 scope small.
"""
import time
from collections import defaultdict, deque
from threading import Lock
from app.config import settings

_buckets: dict[str, deque] = defaultdict(deque)
_lock = Lock()
_WINDOW_SECONDS = 60.0


def is_rate_limited(org_id: str) -> bool:
    """Sliding window: True if org exceeds rate_limit_per_minute requests."""
    limit = settings.rate_limit_per_minute
    now = time.monotonic()
    cutoff = now - _WINDOW_SECONDS
    with _lock:
        bucket = _buckets[org_id]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            return True
        bucket.append(now)
        return False
