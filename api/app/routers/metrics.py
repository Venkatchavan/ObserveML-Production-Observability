"""Metrics router — GET /v1/metrics, /v1/metrics/trend, /v1/metrics/export, /v1/metrics/token-budget."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.clickhouse import (
    query_metrics,
    query_trend,
    query_export,
    query_monthly_cost,
    query_session_summary,
    query_prompt_hashes,
)
from app.db.postgres import get_db
from app.models.events import MetricSummary, TrendPoint, TrendResponse
from app.services.api_key_service import validate_api_key
import calendar
from datetime import datetime, timezone

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


@router.get("/metrics/export")
async def export_metrics_csv(
    days: int = Query(30, ge=1, le=90),
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """OB-38: Stream all metric events as a CSV download (last N days)."""
    org_id = await validate_api_key(x_api_key, db)
    if not org_id:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    rows = query_export(org_id, days=days)
    cols = [
        "event_id",
        "call_site",
        "model",
        "latency_ms",
        "input_tokens",
        "output_tokens",
        "cost_usd",
        "error",
        "error_code",
        "trace_id",
        "ts",
    ]

    def generate():
        yield ",".join(cols) + "\n"
        for row in rows:
            yield ",".join(str(row.get(c, "")) for c in cols) + "\n"

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=observeml-export.csv"},
    )


@router.get("/metrics/token-budget")
async def token_budget_status(
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """OB-34: Return projected monthly cost vs any configured budget thresholds."""
    org_id = await validate_api_key(x_api_key, db)
    if not org_id:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    now = datetime.now(timezone.utc)
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    daily_avg = query_monthly_cost(org_id)
    projected = daily_avg * days_in_month

    return {
        "daily_avg_cost_usd": round(daily_avg, 6),
        "projected_monthly_cost_usd": round(projected, 4),
        "days_in_month": days_in_month,
    }


@router.get("/metrics/session/{session_id}")
async def get_session_summary(
    session_id: str,
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """OB-45: Per-session cost, call count, avg latency."""
    org_id = await validate_api_key(x_api_key, db)
    if not org_id:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    summary = query_session_summary(org_id, session_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Session not found")
    return summary


@router.get("/metrics/prompt-hashes")
async def get_prompt_hash_analytics(
    limit: int = Query(10, ge=1, le=100),
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """OB-44: Top-N repeated prompt hashes — frequency only, no prompt text."""
    org_id = await validate_api_key(x_api_key, db)
    if not org_id:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    return query_prompt_hashes(org_id, limit)
