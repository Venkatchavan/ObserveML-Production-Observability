"""OB-52: 7-day cost forecasting via linear regression on a 14-day rolling window.

UI contract: response always includes `confidence_interval` (lower + upper bounds)
so the dashboard never shows a bare point estimate (Vedantic Launch Gate).

333-Line Law: this file is intentionally < 80 lines.
"""

import math
from datetime import date, timedelta
from typing import Dict, List

from app.db.clickhouse_analytics import query_daily_cost_14d


def _ols(xs: List[float], ys: List[float]):
    """Ordinary least-squares: returns (slope, intercept, residual_std)."""
    n = len(xs)
    if n < 2:
        return 0.0, 0.0, 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    slope = num / den if den else 0.0
    intercept = my - slope * mx
    preds = [slope * x + intercept for x in xs]
    residuals = [y - p for y, p in zip(ys, preds)]
    std = math.sqrt(sum(r**2 for r in residuals) / max(n - 2, 1))
    return slope, intercept, std


def build_forecast(org_id: str) -> Dict:
    """Return 7-day daily cost forecast with per-day confidence intervals."""
    rows = query_daily_cost_14d(org_id)

    if len(rows) < 3:
        return {
            "daily_forecast": [],
            "total_7d_usd": 0.0,
            "confidence_interval": {"lower": 0.0, "upper": 0.0},
            "model": "linear_regression_14d",
            "data_points": len(rows),
            "note": "Insufficient historical data (< 3 days) for forecasting.",
        }

    xs = list(range(len(rows)))
    ys = [float(r["daily_cost"]) for r in rows]
    slope, intercept, std = _ols(xs, ys)

    last_x = len(rows) - 1
    today = date.today()
    forecast_days: List[Dict] = []
    total = 0.0

    for i in range(1, 8):
        xi = last_x + i
        point = max(slope * xi + intercept, 0.0)
        total += point
        forecast_days.append(
            {
                "date": str(today + timedelta(days=i)),
                "projected_cost_usd": round(point, 6),
                "ci_lower": round(max(point - 1.96 * std, 0.0), 6),
                "ci_upper": round(point + 1.96 * std, 6),
            }
        )

    ci_total_margin = 1.96 * std * 7
    return {
        "daily_forecast": forecast_days,
        "total_7d_usd": round(total, 4),
        "confidence_interval": {
            "lower": round(max(total - ci_total_margin, 0.0), 4),
            "upper": round(total + ci_total_margin, 4),
        },
        "model": "linear_regression_14d",
        "data_points": len(rows),
    }
