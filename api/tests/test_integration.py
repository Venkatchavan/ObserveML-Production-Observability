"""OB-19: Integration tests — FastAPI app via ASGI transport (no live server).

Uses httpx.ASGITransport so all requests go in-process through the FastAPI app.
PostgreSQL and ClickHouse services must be reachable (provided by CI docker
services or local docker-compose).

Environment variables (with defaults matching docker-compose.yml):
  DATABASE_URL, CLICKHOUSE_HOST, CLICKHOUSE_PORT, CLICKHOUSE_USER,
  CLICKHOUSE_PASSWORD, CLICKHOUSE_DATABASE
"""

import asyncio
import hashlib
import os
import uuid

import anyio
import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.clickhouse import ensure_table
from app.db.postgres import init_db
from app.main import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://observeml:observeml@localhost:5432/observeml",
)


def _make_client() -> httpx.AsyncClient:
    """Return an AsyncClient that talks directly to the ASGI app — no TCP."""
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        timeout=10.0,
    )


async def _get_session() -> AsyncSession:
    engine = create_async_engine(DB_URL, echo=False)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return factory()


async def _create_org_and_key(db: AsyncSession) -> tuple[str, str]:
    org_id = str(uuid.uuid4())
    raw_key = f"test-{uuid.uuid4().hex}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    await db.execute(
        text("INSERT INTO organizations (id, name) VALUES (:id, :name)"),
        {"id": org_id, "name": "integration-test-org"},
    )
    await db.execute(
        text("INSERT INTO api_keys (org_id, key_hash) VALUES (:org_id, :key_hash)"),
        {"org_id": org_id, "key_hash": key_hash},
    )
    await db.commit()
    return org_id, raw_key


async def _create_alert_rule(db: AsyncSession, org_id: str, metric: str, threshold: float) -> str:
    result = await db.execute(
        text(
            "INSERT INTO alert_rules (org_id, metric, threshold) "
            "VALUES (:org_id, :metric, :threshold) RETURNING id"
        ),
        {"org_id": org_id, "metric": metric, "threshold": threshold},
    )
    await db.commit()
    return str(result.fetchone()[0])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
async def db_init():
    """Create all DB tables once for the whole test module."""
    await init_db()
    ensure_table()


@pytest.fixture(scope="module")
async def test_credentials(db_init):
    """Seed a fresh org + API key; shared across the module."""
    db = await _get_session()
    try:
        org_id, raw_key = await _create_org_and_key(db)
        yield org_id, raw_key
    finally:
        await db.close()


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


# ---------------------------------------------------------------------------
# OB-39: Sprint 04 — new endpoint tests
# ---------------------------------------------------------------------------


async def test_metrics_includes_percentiles(test_credentials):
    """OB-33: GET /v1/metrics must include p50/p95/p99 latency fields."""
    _, raw_key = test_credentials
    async with _make_client() as client:
        resp = await client.get("/v1/metrics", headers={"x-api-key": raw_key})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    if body:
        row = body[0]
        assert "p50_latency_ms" in row, "missing p50_latency_ms"
        assert "p95_latency_ms" in row, "missing p95_latency_ms"
        assert "p99_latency_ms" in row, "missing p99_latency_ms"


async def test_metrics_export_returns_csv(test_credentials):
    """OB-38: GET /v1/metrics/export must return text/csv with headers row."""
    _, raw_key = test_credentials
    async with _make_client() as client:
        resp = await client.get(
            "/v1/metrics/export",
            params={"days": 7},
            headers={"x-api-key": raw_key},
        )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    # First line must be the CSV header row
    first_line = resp.text.splitlines()[0] if resp.text.strip() else ""
    if first_line:
        assert "event_id" in first_line
        assert "trace_id" in first_line


async def test_token_budget_returns_projection(test_credentials):
    """OB-34: GET /v1/metrics/token-budget must include projected_monthly_cost_usd."""
    _, raw_key = test_credentials
    async with _make_client() as client:
        resp = await client.get("/v1/metrics/token-budget", headers={"x-api-key": raw_key})
    assert resp.status_code == 200
    body = resp.json()
    assert "daily_avg_cost_usd" in body
    assert "projected_monthly_cost_usd" in body
    assert "days_in_month" in body
    assert isinstance(body["projected_monthly_cost_usd"], float)
    assert body["days_in_month"] in range(28, 32)


async def test_compare_routing_returns_recommendations(test_credentials):
    """OB-35: GET /v1/compare/routing must return list with caveat field."""
    _, raw_key = test_credentials
    async with _make_client() as client:
        resp = await client.get(
            "/v1/compare/routing",
            params={"max_latency_ms": 9999, "max_cost_usd": 99.0},
            headers={"x-api-key": raw_key},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    if body:
        row = body[0]
        assert "model" in row
        assert "caveat" in row, "Vedantic gate: caveat field must be present"
        assert "meets_constraints" in row
        assert isinstance(row["meets_constraints"], bool)


async def test_stream_events_requires_auth():
    """OB-32: GET /v1/stream/events without API key must return 422 (missing header)."""
    async with _make_client() as client:
        resp = await client.get("/v1/stream/events")
    assert resp.status_code == 422


async def test_stream_events_returns_event_stream(test_credentials):
    """OB-32: GET /v1/stream/events with valid key returns text/event-stream.

    The SSE generator runs forever, so we capture response headers then park
    with anyio.sleep_forever() inside a 4-second cancel scope.  move_on_after
    cleanly cancels the scope without triggering the 30 s pytest-timeout.
    """
    _, raw_key = test_credentials
    captured_status: list[int] = []
    captured_ct: list[str] = []

    async def _grab_headers() -> None:
        async with _make_client() as client:
            async with client.stream(
                "GET", "/v1/stream/events", headers={"x-api-key": raw_key}
            ) as resp:
                captured_status.append(resp.status_code)
                captured_ct.append(resp.headers.get("content-type", ""))
                # Park until the cancel scope fires — avoids reading the
                # infinite SSE body and triggering the pytest-timeout.
                await anyio.sleep_forever()

    with anyio.move_on_after(4.0):
        await _grab_headers()

    assert captured_status == [200], f"SSE status: {captured_status}"
    assert "text/event-stream" in captured_ct[0], f"SSE content-type: {captured_ct}"


async def test_ingest_with_trace_id_accepted(test_credentials):
    """OB-36: Ingest accepts trace_id field and stores it without error."""
    _, raw_key = test_credentials
    async with _make_client() as client:
        resp = await client.post(
            "/v1/ingest",
            json={
                "events": [
                    {
                        "model": "gpt-4o",
                        "latency_ms": 80,
                        "input_tokens": 20,
                        "output_tokens": 10,
                        "cost_usd": 0.0005,
                        "call_site": "trace-test",
                        "trace_id": "abc123def456abc7",
                    }
                ]
            },
            headers={"x-api-key": raw_key},
        )
    assert resp.status_code == 200
    assert resp.json()["accepted"] == 1
