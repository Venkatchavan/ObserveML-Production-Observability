"""OB-21/22/23/35: Compare router — multi-model comparison, regression detection, cost, routing."""

from typing import List
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.clickhouse import query_model_comparison, query_cost_breakdown, query_model_routing
from app.db.postgres import get_db
from app.models.events import (
    ModelComparisonRow,
    RegressionFinding,
    CostRow,
    ModelRoutingRecommendation,
)
from app.services.api_key_service import validate_api_key
from app.services.regression_detector import detect_regressions

router = APIRouter()


async def _org(
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> str:
    org_id = await validate_api_key(x_api_key, db)
    if not org_id:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return org_id


@router.get("/compare/models", response_model=List[ModelComparisonRow])
async def compare_models(org_id: str = Depends(_org)):
    """OB-21: Return per-model aggregated metrics for the last 7 days."""
    rows = query_model_comparison(org_id)
    return [ModelComparisonRow(**row) for row in rows]


@router.get("/compare/regression", response_model=List[RegressionFinding])
async def regression(
    window_hours: int = Query(24, ge=1, le=168),
    org_id: str = Depends(_org),
):
    """OB-22: Detect metric regressions comparing current vs previous window.

    window_hours: size of each comparison window in hours (default 24).
    Returns findings sorted by regression flag DESC, p-value ASC.
    """
    findings = detect_regressions(org_id, window_hours=window_hours)
    return [RegressionFinding(**f) for f in findings]


@router.get("/compare/cost", response_model=List[CostRow])
async def cost_breakdown(
    days: int = Query(7, ge=1, le=90),
    org_id: str = Depends(_org),
):
    """OB-23: Daily cost per model for the last N days."""
    rows = query_cost_breakdown(org_id, days=days)
    return [CostRow(**row) for row in rows]


@router.get("/compare/routing", response_model=List[ModelRoutingRecommendation])
async def model_routing(
    max_latency_ms: float = Query(..., description="Maximum acceptable avg latency (ms)"),
    max_cost_usd: float = Query(..., description="Maximum acceptable avg cost per call ($)"),
    org_id: str = Depends(_org),
):
    """OB-35: Recommend models meeting latency + cost constraints (last 7 days).

    Śhāstrārtha gate: every recommendation includes a caveat field clarifying
    that results are based on observed performance only.
    """
    rows = query_model_routing(org_id)
    recommendations = []
    for row in rows:
        meets = (
            float(row["avg_latency_ms"]) <= max_latency_ms
            and float(row["avg_cost_usd"]) <= max_cost_usd
        )
        recommendations.append(
            ModelRoutingRecommendation(
                model=row["model"],
                avg_latency_ms=float(row["avg_latency_ms"]),
                avg_cost_usd=float(row["avg_cost_usd"]),
                error_rate=float(row["error_rate"]),
                total_calls=int(row["total_calls"]),
                meets_constraints=meets,
            )
        )
    # Sort: models meeting constraints first, then cheapest
    recommendations.sort(key=lambda r: (not r.meets_constraints, r.avg_cost_usd))
    return recommendations
