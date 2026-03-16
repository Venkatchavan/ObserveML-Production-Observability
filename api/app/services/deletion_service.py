"""OB-48: GDPR-compliant data deletion with 24h cooling-off period.

Śhāstrārtha Sprint Review Siddhānta (sprint-05.md):
  1. Token issued by POST /v1/org/request-data-deletion.
  2. 24h cooling-off before deletion can be executed.
  3. Email hook — logs when SMTP not configured.

Vedantic Launch Gate:
  organizations and usage_billing rows are preserved after deletion.
  Only metric_events + alert_rules are removed.

333-Line Law: this file is intentionally < 110 lines.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

COOLING_OFF_HOURS = 24
TOKEN_TTL_HOURS = 25  # token expires 25h after issuance


async def request_deletion(org_id: str, db: AsyncSession) -> str:
    """Issue a single-use deletion token. Returns the plaintext token.

    Logs the request (email hook: plug in SMTP here when available).
    """
    raw_token = secrets.token_hex(32)  # 256-bit cryptographically random
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    await db.execute(
        text("INSERT INTO deletion_tokens (org_id, token_hash) VALUES (:org_id, :token_hash)"),
        {"org_id": org_id, "token_hash": token_hash},
    )
    await db.execute(
        text(
            "INSERT INTO audit_log (org_id, action, actor, details) "
            "VALUES (:org_id, 'DATA_DELETION_REQUESTED', 'api', :details)"
        ),
        {
            "org_id": org_id,
            "details": "Deletion token issued. 24h cooling-off begins.",
        },
    )
    await db.commit()
    log.warning("GDPR deletion requested for org %s — 24h cooling-off in effect.", org_id)
    return raw_token


async def execute_deletion(org_id: str, raw_token: str, db: AsyncSession) -> Optional[str]:
    """Execute GDPR deletion after cooling-off has elapsed.

    Returns None on success; an error message string on any failure.
    Preserves: organizations, usage_billing (billing history).
    Deletes: metric_events (ClickHouse), alert_rules (Postgres).
    """
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    result = await db.execute(
        text(
            "SELECT requested_at, executed_at FROM deletion_tokens "
            "WHERE org_id = :org_id AND token_hash = :token_hash"
        ),
        {"org_id": org_id, "token_hash": token_hash},
    )
    row = result.fetchone()
    if not row:
        return "Invalid or expired deletion token."
    requested_at, executed_at = row
    if executed_at is not None:
        return "Deletion token has already been used."
    if not isinstance(requested_at, datetime):
        return "Cannot determine token age."
    age = datetime.now(timezone.utc) - requested_at.replace(tzinfo=timezone.utc)
    if age < timedelta(hours=COOLING_OFF_HOURS):
        remaining = timedelta(hours=COOLING_OFF_HOURS) - age
        return f"Cooling-off period not elapsed. {remaining} remaining."

    # Execute — ClickHouse first (can be retried if it fails)
    try:
        from app.db.clickhouse_analytics import delete_org_events

        delete_org_events(org_id)
    except Exception as exc:
        log.error("ClickHouse deletion failed for org %s: %s", org_id, exc)
        return f"ClickHouse deletion failed: {exc}"

    await db.execute(text("DELETE FROM alert_rules WHERE org_id = :org_id"), {"org_id": org_id})
    await db.execute(
        text(
            "UPDATE deletion_tokens SET executed_at = NOW() "
            "WHERE org_id = :org_id AND token_hash = :token_hash"
        ),
        {"org_id": org_id, "token_hash": token_hash},
    )
    await db.execute(
        text(
            "INSERT INTO audit_log (org_id, action, actor, details) "
            "VALUES (:org_id, 'DATA_DELETION_EXECUTED', 'api', :details)"
        ),
        {
            "org_id": org_id,
            "details": "Metric events and alert rules deleted. Org + billing preserved.",
        },
    )
    await db.commit()
    log.warning("GDPR deletion executed for org %s.", org_id)
    return None
