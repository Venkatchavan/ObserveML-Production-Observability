"""OB-59: Sprint 06 integration tests — intelligence layer (root cause,
cost forecast, model selection assistant).

Fixtures (db_init, test_credentials) are auto-discovered from conftest.py.
333-Line Law: this file is intentionally < 333 lines.
"""

from unittest.mock import patch

from conftest import _make_client

# ---------------------------------------------------------------------------
# OB-51: Root cause narration
# ---------------------------------------------------------------------------

FAKE_ROOT_CAUSE = {
    "narrative": "p99 latency for 'chat' rose from 120 ms to 890 ms (+642%) "
    "in the last 60 min. Primary driver: error_rate spike (0.01 → 0.34).",
    "confidence": "HIGH",
    "contributing_factors": [
        {"metric": "p99_latency_ms", "current": 890, "baseline": 120, "delta_pct": 642},
        {"metric": "error_rate", "current": 0.34, "baseline": 0.01, "delta_pct": 3300},
    ],
    "data": {"current": {"p99_latency_ms": 890}, "baseline": {"p99_latency_ms": 120}},
    "caveat": "Root cause is inferred from observed metrics only.",
    "show_data_url": "/v1/metrics/trend?call_site=chat",
}


async def test_root_cause_returns_narrative(test_credentials):
    """GET /v1/intelligence/root-cause must return 200 with a plain-English narrative."""
    _, raw_key = test_credentials
    with patch("app.routers.intelligence.build_root_cause", return_value=FAKE_ROOT_CAUSE):
        async with _make_client() as client:
            resp = await client.get(
                "/v1/intelligence/root-cause?call_site=chat",
                headers={"x-api-key": raw_key},
            )
    assert resp.status_code == 200
    body = resp.json()
    assert "narrative" in body
    assert isinstance(body["narrative"], str)
    assert len(body["narrative"]) > 0


async def test_root_cause_confidence_field_valid(test_credentials):
    """Confidence field must be one of HIGH / MEDIUM / LOW."""
    _, raw_key = test_credentials
    with patch("app.routers.intelligence.build_root_cause", return_value=FAKE_ROOT_CAUSE):
        async with _make_client() as client:
            resp = await client.get(
                "/v1/intelligence/root-cause",
                headers={"x-api-key": raw_key},
            )
    assert resp.status_code == 200
    assert resp.json()["confidence"] in ("HIGH", "MEDIUM", "LOW")


async def test_root_cause_includes_caveat(test_credentials):
    """Root-cause narration must always include a caveat (Śhāstrārtha gate)."""
    _, raw_key = test_credentials
    with patch("app.routers.intelligence.build_root_cause", return_value=FAKE_ROOT_CAUSE):
        async with _make_client() as client:
            resp = await client.get(
                "/v1/intelligence/root-cause",
                headers={"x-api-key": raw_key},
            )
    assert "caveat" in resp.json()
    assert resp.json()["caveat"]


# ---------------------------------------------------------------------------
# OB-52: Cost forecast
# ---------------------------------------------------------------------------

FAKE_FORECAST = {
    "daily_forecast": [
        {"date": "2026-03-17", "predicted_usd": 1.20, "ci_lower": 0.95, "ci_upper": 1.45},
        {"date": "2026-03-18", "predicted_usd": 1.23, "ci_lower": 0.98, "ci_upper": 1.48},
    ],
    "total_7d_usd": 8.61,
    "confidence_interval": {"lower": 6.65, "upper": 10.36},
    "model": "linear_regression",
    "data_points": 14,
}


async def test_forecast_returns_structure(test_credentials):
    """GET /v1/intelligence/forecast must return daily_forecast + confidence_interval."""
    _, raw_key = test_credentials
    with patch("app.routers.intelligence.build_forecast", return_value=FAKE_FORECAST):
        async with _make_client() as client:
            resp = await client.get(
                "/v1/intelligence/forecast",
                headers={"x-api-key": raw_key},
            )
    assert resp.status_code == 200
    body = resp.json()
    assert "daily_forecast" in body
    assert "confidence_interval" in body
    ci = body["confidence_interval"]
    assert "lower" in ci and "upper" in ci


async def test_forecast_confidence_interval_is_numeric(test_credentials):
    """Confidence interval bounds must be numeric (Vedantic Launch Gate)."""
    _, raw_key = test_credentials
    with patch("app.routers.intelligence.build_forecast", return_value=FAKE_FORECAST):
        async with _make_client() as client:
            resp = await client.get(
                "/v1/intelligence/forecast",
                headers={"x-api-key": raw_key},
            )
    ci = resp.json()["confidence_interval"]
    assert isinstance(ci["lower"], (int, float))
    assert isinstance(ci["upper"], (int, float))
    assert ci["lower"] <= ci["upper"]


# ---------------------------------------------------------------------------
# OB-53: Model selection assistant
# ---------------------------------------------------------------------------


async def test_model_select_returns_caveat(test_credentials):
    """GET /v1/intelligence/model-select must always include `caveat` field."""
    _, raw_key = test_credentials
    with patch("app.routers.intelligence.query_model_routing", return_value=[]):
        async with _make_client() as client:
            resp = await client.get(
                "/v1/intelligence/model-select?max_latency_ms=9999&max_cost_usd=9999",
                headers={"x-api-key": raw_key},
            )
    assert resp.status_code == 200
    assert "caveat" in resp.json()
    assert resp.json()["caveat"]


async def test_model_select_no_qualifying_returns_null_recommendation(test_credentials):
    """When no model meets tight constraints, recommendation must be null — never 500."""
    _, raw_key = test_credentials
    with patch("app.routers.intelligence.query_model_routing", return_value=[]):
        async with _make_client() as client:
            resp = await client.get(
                "/v1/intelligence/model-select?max_latency_ms=0.001&max_cost_usd=0.0001",
                headers={"x-api-key": raw_key},
            )
    assert resp.status_code == 200
    assert resp.json()["recommendation"] is None


async def test_model_select_picks_cheapest_qualifying(test_credentials):
    """Model selection must return the cheapest model that meets all constraints."""
    _, raw_key = test_credentials
    candidates = [
        {"model": "gpt-4o", "avg_latency_ms": 200, "avg_cost_usd": 0.02, "error_rate": 0.01},
        {"model": "gpt-4o-mini", "avg_latency_ms": 80, "avg_cost_usd": 0.004, "error_rate": 0.01},
        {
            "model": "claude-3-haiku",
            "avg_latency_ms": 110,
            "avg_cost_usd": 0.001,
            "error_rate": 0.02,
        },
    ]
    with patch("app.routers.intelligence.query_model_routing", return_value=candidates):
        async with _make_client() as client:
            resp = await client.get(
                "/v1/intelligence/model-select?max_latency_ms=500&max_cost_usd=0.05",
                headers={"x-api-key": raw_key},
            )
    assert resp.status_code == 200
    # claude-3-haiku has lowest avg_cost_usd (0.001) and meets all constraints
    assert resp.json()["recommendation"] == "claude-3-haiku"
