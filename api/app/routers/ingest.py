"""Ingest router — OB-01: POST /v1/ingest with API key auth + rate limiting."""

from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.clickhouse import insert_events
from app.db.postgres import get_db
from app.models.events import IngestRequest, IngestResponse
from app.services.api_key_service import validate_api_key
from app.services.rate_limiter import is_rate_limited
from app.services.anomaly_detector import run_anomaly_check
from app.services import event_store

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    payload: IngestRequest,
    background_tasks: BackgroundTasks,
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    # Constitutional law: org_id always comes from server-side key lookup.
    org_id = await validate_api_key(x_api_key, db)
    if not org_id:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    if is_rate_limited(org_id):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {100} requests/minute",
        )

    now_ts = datetime.now(timezone.utc)
    events_data = [{**event.model_dump(), "ts": now_ts} for event in payload.events]
    insert_events(org_id, events_data)
    # OB-32: push to SSE event store for connected dashboard clients
    event_store.push(org_id, events_data)
    # OB-11: check for anomalies in background after response is sent
    background_tasks.add_task(run_anomaly_check, org_id)
    return IngestResponse(accepted=len(events_data), rejected=0)
