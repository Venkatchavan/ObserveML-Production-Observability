"""OB-21/22/23: Compare router — multi-model comparison, regression detection, cost."""

from typing import List
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.clickhouse import query_model_comparison, query_cost_breakdown
from app.db.postgres import get_db
from app.models.events import ModelComparisonRow, RegressionFinding, CostRow
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
