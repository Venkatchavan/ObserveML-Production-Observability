"""OB-12: Alert rules CRUD and fired-alert feed endpoints."""
from typing import List
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.postgres import get_db
from app.models.events import AlertRuleCreate, AlertRuleResponse, AlertFeedItem
from app.services.api_key_service import validate_api_key

router = APIRouter()


async def _resolve_org(
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> str:
    """Shared auth dependency — returns org_id or raises 401."""
    org_id = await validate_api_key(x_api_key, db)
    if not org_id:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return org_id


@router.post("/alerts", response_model=AlertRuleResponse, status_code=201)
async def create_alert_rule(
    body: AlertRuleCreate,
    org_id: str = Depends(_resolve_org),
    db: AsyncSession = Depends(get_db),
):
    """Create a threshold-based alert rule for this org."""
    result = await db.execute(
        text("""
            INSERT INTO alert_rules (org_id, call_site, metric, threshold, webhook_url)
            VALUES (:org_id, :call_site, :metric, :threshold, :webhook_url)
            RETURNING id, org_id, call_site, metric, threshold, webhook_url, created_at
        """),
        dict(
            org_id=org_id,
            call_site=body.call_site,
            metric=body.metric,
            threshold=body.threshold,
            webhook_url=body.webhook_url,
        ),
    )
    await db.commit()
    row = result.fetchone()
    return AlertRuleResponse(**dict(row._mapping))


@router.get("/alerts", response_model=List[AlertRuleResponse])
async def list_alert_rules(
    org_id: str = Depends(_resolve_org),
    db: AsyncSession = Depends(get_db),
):
    """List all alert rules for this org."""
    result = await db.execute(
        text(
            "SELECT id, org_id, call_site, metric, threshold, webhook_url, created_at "
            "FROM alert_rules WHERE org_id = :org_id ORDER BY created_at DESC"
        ),
        {"org_id": org_id},
    )
    return [AlertRuleResponse(**dict(r._mapping)) for r in result.fetchall()]


@router.delete("/alerts/{rule_id}", status_code=204)
async def delete_alert_rule(
    rule_id: str,
    org_id: str = Depends(_resolve_org),
    db: AsyncSession = Depends(get_db),
):
    """Delete an alert rule; silently succeeds if rule_id not found."""
    await db.execute(
        text("DELETE FROM alert_rules WHERE id = :id AND org_id = :org_id"),
        {"id": rule_id, "org_id": org_id},
    )
    await db.commit()


@router.get("/alerts/feed", response_model=List[AlertFeedItem])
async def alert_feed(
    org_id: str = Depends(_resolve_org),
    db: AsyncSession = Depends(get_db),
):
    """Return the 50 most recent fired alerts for this org."""
    result = await db.execute(
        text("""
            SELECT id, rule_id, call_site, metric, current_value, threshold, fired_at
            FROM alert_fired
            WHERE org_id = :org_id
            ORDER BY fired_at DESC
            LIMIT 50
        """),
        {"org_id": org_id},
    )
    return [AlertFeedItem(**dict(r._mapping)) for r in result.fetchall()]
