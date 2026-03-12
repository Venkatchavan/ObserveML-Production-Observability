"""OB-19: Integration tests — FastAPI app via ASGI transport (no live server).

Helpers and fixtures live in conftest.py (auto-discovered by pytest).
Sprint 04 endpoint tests live in test_sprint04.py.
"""

import asyncio

from sqlalchemy import text

from conftest import _create_alert_rule, _get_session, _make_client

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_ingest_returns_accepted(test_credentials):
    """POST /v1/ingest with a valid key returns accepted count."""
    _, raw_key = test_credentials
    async with _make_client() as client:
        resp = await client.post(
            "/v1/ingest",
            json={
                "events": [
                    {
                        "model": "gpt-4o",
                        "latency_ms": 120,
                        "input_tokens": 50,
                        "output_tokens": 30,
                        "cost_usd": 0.001,
                        "call_site": "integration-test",
                    }
                ]
            },
            headers={"x-api-key": raw_key},
        )
    assert resp.status_code == 200
    assert resp.json()["accepted"] == 1
    assert resp.json()["rejected"] == 0


async def test_ingest_rejects_invalid_key():
    """POST /v1/ingest with a bad API key must return 401."""
    async with _make_client() as client:
        resp = await client.post(
            "/v1/ingest",
            json={"events": [{"model": "gpt-4o", "latency_ms": 100}]},
            headers={"x-api-key": "totally-invalid-key"},
        )
    assert resp.status_code == 401


async def test_alert_rule_crud(test_credentials):
    """Create, list, and delete an alert rule via the API."""
    _, raw_key = test_credentials
    async with _make_client() as client:
        create_resp = await client.post(
            "/v1/alerts",
            json={"metric": "avg_latency_ms", "threshold": 1000.0},
            headers={"x-api-key": raw_key},
        )
        assert create_resp.status_code == 201
        rule_id = create_resp.json()["id"]

        list_resp = await client.get("/v1/alerts", headers={"x-api-key": raw_key})
        assert list_resp.status_code == 200
        assert any(r["id"] == rule_id for r in list_resp.json())

        del_resp = await client.delete(f"/v1/alerts/{rule_id}", headers={"x-api-key": raw_key})
        assert del_resp.status_code == 204


async def test_anomaly_fires_alert(test_credentials):
    """Full flow: ingest high-latency events -> anomaly check -> alert_fired row."""
    org_id, raw_key = test_credentials

    db = await _get_session()
    try:
        await _create_alert_rule(db, org_id, "avg_latency_ms", threshold=50.0)
    finally:
        await db.close()

    async with _make_client() as client:
        resp = await client.post(
            "/v1/ingest",
            json={
                "events": [
                    {"model": "gpt-4o", "latency_ms": 5000, "call_site": ""} for _ in range(5)
                ]
            },
            headers={"x-api-key": raw_key},
        )
    assert resp.status_code == 200

    await asyncio.sleep(0.2)  # background task runs in-process; 0.2s is sufficient

    db = await _get_session()
    try:
        result = await db.execute(
            text(
                "SELECT COUNT(*) FROM alert_fired "
                "WHERE org_id = :org_id AND metric = 'avg_latency_ms'"
            ),
            {"org_id": org_id},
        )
        count = result.scalar()
    finally:
        await db.close()

    assert count >= 1, "Expected at least one alert_fired row after threshold breach"


async def test_alert_feed_returns_fired_alert(test_credentials):
    """GET /v1/alerts/feed must include the alert from test_anomaly_fires_alert."""
    _, raw_key = test_credentials
    async with _make_client() as client:
        resp = await client.get("/v1/alerts/feed", headers={"x-api-key": raw_key})
    assert resp.status_code == 200
    feed = resp.json()
    assert len(feed) >= 1
    assert any(item["metric"] == "avg_latency_ms" for item in feed)


async def test_regression_endpoint_returns_list(test_credentials):
    """GET /v1/compare/regression must return HTTP 200 with a JSON array."""
    _, raw_key = test_credentials
    async with _make_client() as client:
        resp = await client.get(
            "/v1/compare/regression",
            params={"window_hours": 24},
            headers={"x-api-key": raw_key},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    if body:
        first = body[0]
        assert "call_site" in first
        assert "metric" in first
        assert "is_regression" in first
        assert isinstance(first["is_regression"], bool)


async def test_regression_stable_data_produces_no_regression(test_credentials):
    """Ingest stable latencies; regression endpoint should report no regressions."""
    _, raw_key = test_credentials
    events = [
        {
            "model": "gpt-3.5-turbo",
            "latency_ms": 200,
            "input_tokens": 40,
            "output_tokens": 20,
            "cost_usd": 0.0002,
            "call_site": "regression-stability-test",
        }
        for _ in range(20)
    ]
    async with _make_client() as client:
        ingest_resp = await client.post(
            "/v1/ingest",
            json={"events": events},
            headers={"x-api-key": raw_key},
        )
        assert ingest_resp.status_code == 200

        await asyncio.sleep(0.1)  # ClickHouse write is synchronous via clickhouse-connect

        reg_resp = await client.get(
            "/v1/compare/regression",
            params={"window_hours": 24},
            headers={"x-api-key": raw_key},
        )
    assert reg_resp.status_code == 200
    findings = reg_resp.json()
    regressions = [f for f in findings if f.get("is_regression") is True]
    assert regressions == [], f"Unexpected regressions for stable data: {regressions}"


async def test_compare_models_returns_list(test_credentials):
    """GET /v1/compare/models must return 200 with a well-formed list."""
    _, raw_key = test_credentials
    async with _make_client() as client:
        resp = await client.get("/v1/compare/models", headers={"x-api-key": raw_key})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    if body:
        row = body[0]
        assert "model" in row
        assert "avg_latency_ms" in row
        assert "error_rate" in row
        assert "total_cost_usd" in row


async def test_compare_cost_returns_list(test_credentials):
    """GET /v1/compare/cost must return 200 with day-level cost rows."""
    _, raw_key = test_credentials
    async with _make_client() as client:
        resp = await client.get(
            "/v1/compare/cost",
            params={"days": 7},
            headers={"x-api-key": raw_key},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    if body:
        row = body[0]
        assert "model" in row
        assert "day" in row
        assert "total_cost_usd" in row
