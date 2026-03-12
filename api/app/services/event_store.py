"""OB-32: In-memory SSE event store — per-org ring buffer + subscriber queues.

Observer Principle: only metadata events are stored here — never prompt content.
333-Line Law: this module is intentionally small (<50 lines).
"""

import asyncio
import collections
from typing import Any, Deque, Dict, List, Set

# Last 50 events per org (ring buffer)
_recent: Dict[str, Deque[Dict[str, Any]]] = {}
# Connected SSE subscriber queues per org
_subscribers: Dict[str, Set[asyncio.Queue]] = {}


def push(org_id: str, events: List[Dict[str, Any]]) -> None:
    """Push ingested events into the ring buffer and all live subscriber queues."""
    buf = _recent.setdefault(org_id, collections.deque(maxlen=50))
    subs = _subscribers.get(org_id, set())
    for event in events:
        buf.append(event)
        dead: Set[asyncio.Queue] = set()
        for q in subs:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.add(q)
        subs -= dead


def get_recent(org_id: str) -> List[Dict[str, Any]]:
    """Return the last ≤50 events for the org (sent to new SSE subscribers)."""
    return list(_recent.get(org_id, []))


def subscribe(org_id: str) -> asyncio.Queue:
    """Register a new SSE subscriber; returns a queue that receives live events."""
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _subscribers.setdefault(org_id, set()).add(q)
    return q


def unsubscribe(org_id: str, q: asyncio.Queue) -> None:
    """Deregister an SSE subscriber queue on disconnect."""
    _subscribers.get(org_id, set()).discard(q)
