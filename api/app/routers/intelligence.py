"""OB-51/52/53: Intelligence layer — root cause narration, cost forecasting,
model selection assistant.

Śhāstrārtha gate (OB-51): all narrations include data citations + confidence label.
Vedantic Launch Gate (OB-53): model selection always includes `caveat` field.
333-Line Law: this file is intentionally < 120 lines.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.clickhouse import query_model_routing
from app.db.postgres import get_db
from app.services.api_key_service import validate_api_key
from app.services.forecast_service import build_forecast
from app.services.root_cause_service import build_root_cause

router = APIRouter()

_MODEL_SELECT_CAVEAT = (
    "Based on observed performance only; evaluate for your specific workload, "
    "privacy requirements, and compliance constraints."
)


@router.get("/intelligence/root-cause")
async def root_cause_narration(
    call_site: Optional[str] = Query(None, description="Filter to a specific call_site"),
    window_minutes: int = Query(60, ge=5, le=1440, description="Look-back window in minutes"),
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """OB-51: Causal anomaly root-cause narration for p99 latency spikes.

    Response always includes:
    - narrative  — plain-English explanation quoting observed metric values
    - confidence — HIGH / MEDIUM / LOW (based on sample size and delta magnitude)
    - contributing_factors — list of metric observations that drove the narrative
    - data        — raw current and baseline metric dicts for transparency
    - show_data_url — link to raw time series
    - caveat       — explicit limitations statement
    """
    org_id = await validate_api_key(x_api_key, db)
    if not org_id:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    try:
        return build_root_cause(org_id, call_site, window_minutes)
    except Exception:
        return {
            "narrative": "Analysis unavailable — ClickHouse unreachable.",
            "confidence": "LOW",
            "contributing_factors": [],
            "data": {},
            "caveat": "Root cause is inferred from observed metrics only.",
            "show_data_url": "/v1/metrics/trend",
        }


@router.get("/intelligence/forecast")
async def cost_forecast(
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """OB-52: 7-day cost projection using linear regression on 14-day rolling window.

    Response always includes `confidence_interval` (lower + upper bounds) —
    never a bare point estimate (Vedantic Launch Gate).
    """
    org_id = await validate_api_key(x_api_key, db)
    if not org_id:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    try:
        return build_forecast(org_id)
    except Exception:
        return {
            "daily_forecast": [],
            "total_7d_usd": 0.0,
            "confidence_interval": {"lower": 0.0, "upper": 0.0},
            "note": "Forecasting unavailable — ClickHouse unreachable.",
        }


@router.get("/intelligence/model-select")
async def model_selection_assistant(
    max_latency_ms: float = Query(..., description="Maximum acceptable avg latency in ms"),
    max_cost_usd: float = Query(..., description="Maximum acceptable avg cost per call"),
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """OB-53: Recommend cheapest model meeting latency + error_rate constraints.

    Vedantic Launch Gate: always includes `caveat` field.
    Data source: last 7 days of observed metric_events — not a general benchmark.
    """
    org_id = await validate_api_key(x_api_key, db)
    if not org_id:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    try:
        rows = query_model_routing(org_id)
    except Exception:
        return {"recommendation": None, "candidates": [], "caveat": _MODEL_SELECT_CAVEAT}

    qualifying = sorted(
        [
            r
            for r in rows
            if (r.get("avg_latency_ms") or 0) <= max_latency_ms
            and (r.get("avg_cost_usd") or 0) <= max_cost_usd
            and (r.get("error_rate") or 0) < 0.05
        ],
        key=lambda r: r.get("avg_cost_usd") or 0,
    )

    return {
        "recommendation": qualifying[0]["model"] if qualifying else None,
        "candidates": qualifying,
        "constraints": {"max_latency_ms": max_latency_ms, "max_cost_usd": max_cost_usd},
        "caveat": _MODEL_SELECT_CAVEAT,
    }
