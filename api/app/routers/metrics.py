"""Metrics router — GET /v1/metrics and /v1/metrics/trend."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.clickhouse import query_metrics, query_trend
from app.db.postgres import get_db
from app.models.events import MetricSummary, TrendPoint, TrendResponse
from app.services.api_key_service import validate_api_key

router = APIRouter()


@router.get("/metrics", response_model=List[MetricSummary])
async def get_metrics(
    call_site: Optional[str] = Query(None),
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    org_id = await validate_api_key(x_api_key, db)
    if not org_id:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    rows = query_metrics(org_id, call_site)
    return [MetricSummary(**row) for row in rows]


@router.get("/metrics/trend", response_model=TrendResponse)
async def get_trend(
    call_site: Optional[str] = Query(None),
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    org_id = await validate_api_key(x_api_key, db)
    if not org_id:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    rows = query_trend(org_id, call_site)
    points = [
        TrendPoint(
            ts=str(row["ts"]),
            avg_latency_ms=row["avg_latency_ms"],
            total_calls=row["total_calls"],
        )
        for row in rows
    ]
    return TrendResponse(call_site=call_site, points=points)
