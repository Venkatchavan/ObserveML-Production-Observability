"""OB-22: Regression detection — Welch's z-test, no external stat libraries."""
import math
from typing import Dict, List

from app.db.clickhouse import query_regression_windows

# Minimum events per window for a statistically meaningful comparison
_MIN_SAMPLE = 5
# p < 0.05 threshold for "statistically significant regression"
_P_THRESHOLD = 0.05

_METRIC_KEYS = [
    ("latency_ms", "lat_mean", "lat_std"),
    ("error_rate", "err_mean", "err_std"),
    ("cost_usd", "cost_mean", "cost_std"),
]


def _z_to_p(z: float) -> float:
    """Two-tailed p-value from z-score using complementary error function."""
    return math.erfc(abs(z) / math.sqrt(2.0))


def detect_regressions(org_id: str, window_hours: int = 24) -> List[Dict]:
    """Compare current window vs baseline for each call_site × metric.

    Returns list of dicts compatible with RegressionFinding model.
    Only call_sites with data in both windows are evaluated.
    """
    windows = query_regression_windows(org_id, window_hours=window_hours)
    results = []

    for call_site, periods in windows.items():
        cur = periods.get("current")
        base = periods.get("baseline")
        if not cur or not base:
            continue

        cur_n = int(cur.get("n", 0))
        base_n = int(base.get("n", 0))
        if cur_n < _MIN_SAMPLE or base_n < _MIN_SAMPLE:
            continue

        for metric_label, mean_key, std_key in _METRIC_KEYS:
            cur_mean = float(cur.get(mean_key, 0.0))
            cur_std = float(cur.get(std_key, 0.0))
            base_mean = float(base.get(mean_key, 0.0))
            base_std = float(base.get(std_key, 0.0))

            se = math.sqrt((cur_std ** 2 / cur_n) + (base_std ** 2 / base_n))
            if se == 0:
                continue

            z = (cur_mean - base_mean) / se
            p_value = _z_to_p(z)

            results.append({
                "call_site": call_site,
                "metric": metric_label,
                "current_mean": cur_mean,
                "baseline_mean": base_mean,
                "z_score": z,
                "p_value": p_value,
                # regression = statistically worse performance
                "is_regression": p_value < _P_THRESHOLD and cur_mean > base_mean,
            })

    # Sort regressions first, then by p-value ascending
    results.sort(key=lambda r: (not r["is_regression"], r["p_value"]))
    return results
