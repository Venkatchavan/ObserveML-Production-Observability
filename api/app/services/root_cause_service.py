"""OB-51: Causal anomaly root-cause narration.

Heuristic rule-based narration grounded in observed ClickHouse metrics.
Includes confidence level and data citations (Śhāstrārtha Siddhānta):
  - narrative quotes the specific metric values it reasons from
  - confidence label: HIGH (n≥100, delta≥50%) / MEDIUM (n≥20, delta≥20%) / LOW
  - show_data_url links to the raw time series
  - caveat field always present (Vedantic Launch Gate OB-53 pattern)

333-Line Law: this file is intentionally < 90 lines.
"""

from typing import Dict, List, Optional

from app.db.clickhouse_analytics import query_anomaly_context


def _confidence(n: int, delta_pct: float) -> str:
    if n >= 100 and abs(delta_pct) >= 0.5:
        return "HIGH"
    if n >= 20 and abs(delta_pct) >= 0.2:
        return "MEDIUM"
    return "LOW"


def build_root_cause(
    org_id: str,
    call_site: Optional[str] = None,
    window_minutes: int = 60,
) -> Dict:
    """Return a structured root-cause analysis dict."""
    current: List[Dict] = query_anomaly_context(org_id, call_site, window_minutes)
    baseline: List[Dict] = query_anomaly_context(org_id, call_site, window_minutes * 2)

    if not current:
        return {
            "narrative": "No data in the selected window.",
            "confidence": "LOW",
            "contributing_factors": [],
            "data": {},
            "caveat": "Root cause is inferred from observed metrics only.",
            "show_data_url": "/v1/metrics/trend",
        }

    worst = max(current, key=lambda r: r.get("p99_latency_ms") or 0)
    cs = worst["call_site"]
    model = worst["model"]

    baseline_row = next((r for r in baseline if r["call_site"] == cs and r["model"] == model), None)

    factors: List[str] = []
    delta_pct = 0.0
    current_p99 = float(worst.get("p99_latency_ms") or 0)

    if baseline_row:
        baseline_p99 = float(baseline_row.get("p99_latency_ms") or 1) or 1
        delta_pct = (current_p99 - baseline_p99) / baseline_p99
        if delta_pct > 0.2:
            factors.append(
                f"p99 latency rose {delta_pct:.0%} vs prior window "
                f"({baseline_p99:.0f}ms → {current_p99:.0f}ms)"
            )
    elif current_p99 > 1000:
        factors.append(f"p99 latency is {current_p99:.0f}ms — above 1000ms threshold")

    err = float(worst.get("error_rate") or 0)
    if err > 0.05:
        factors.append(f"error_rate elevated at {err:.1%}")

    if not factors:
        factors.append("No significant degradation detected in the selected window.")

    narrative = (
        f"In the last {window_minutes} min, call_site '{cs}' (model: {model}) shows: "
        + "; ".join(factors)
        + "."
    )

    return {
        "narrative": narrative,
        "confidence": _confidence(int(worst.get("call_count") or 0), delta_pct),
        "contributing_factors": factors,
        "data": {"current": worst, "baseline": baseline_row},
        "caveat": (
            "Root cause is inferred from observed metrics only. "
            "Review the raw time series before taking action."
        ),
        "show_data_url": f"/v1/metrics/trend?call_site={cs}",
    }
