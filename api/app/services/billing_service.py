"""OB-42: Billing — free tier enforcement and usage status.

Free tier: 10,000 events/month. After limit, ingest returns 402.
Stripe metering is activated when STRIPE_API_KEY env var is set.
Fail-open: if ClickHouse is unavailable, usage count defaults to 0
(never block ingestion due to billing check failures).
333-Line Law: this file is intentionally small.
"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

log = logging.getLogger(__name__)


def _count_events_this_month(org_id: str) -> int:
    """Query ClickHouse for event count in the current calendar month."""
    try:
        from app.db.clickhouse import count_events_this_month

        return count_events_this_month(org_id)
    except Exception as exc:
        log.warning("Billing: ClickHouse count failed for org %s: %s", org_id, exc)
        return 0  # Fail open — never block ingestion due to billing check failure


async def is_over_free_tier(org_id: str, db: AsyncSession) -> bool:
    """Return True if org is on free plan and has reached the monthly event limit."""
    result = await db.execute(
        text("SELECT plan FROM organizations WHERE id = :org_id"),
        {"org_id": org_id},
    )
    row = result.fetchone()
    if not row or row[0] != "free":
        return False  # Pro / enterprise — no cap
    count = _count_events_this_month(org_id)
    return count >= settings.billing_free_tier_limit


async def get_usage_status(org_id: str, db: AsyncSession) -> dict:
    """Return full usage status for the org (OB-43 dashboard data)."""
    result = await db.execute(
        text("SELECT plan FROM organizations WHERE id = :org_id"),
        {"org_id": org_id},
    )
    row = result.fetchone()
    plan = row[0] if row else "free"
    count = _count_events_this_month(org_id)
    limit = settings.billing_free_tier_limit
    projected = round(count * 0.000001, 6)  # $1 per 1M events (stub rate)
    return {
        "org_id": org_id,
        "plan": plan,
        "events_this_month": count,
        "free_tier_limit": limit,
        "over_limit": (plan == "free" and count >= limit),
        "projected_cost_usd": projected,
    }
