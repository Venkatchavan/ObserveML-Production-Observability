"""OB-19: Integration test — events → anomaly detection → alert fired.

Requires a running PostgreSQL and ClickHouse (use docker-compose for local dev).
Run with: pytest api/tests/test_integration.py -v

Environment variables (with defaults matching docker-compose.yml):
  DATABASE_URL, CLICKHOUSE_HOST, CLICKHOUSE_PORT, CLICKHOUSE_USER,
  CLICKHOUSE_PASSWORD, CLICKHOUSE_DATABASE
"""
import os
import pytest
import httpx
import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# ---- helpers ---------------------------------------------------------------

DB_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://observeml:observeml@localhost:5432/observeml")


async def _get_session() -> AsyncSession:
    engine = create_async_engine(DB_URL, echo=False)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return factory()


async def _create_org_and_key(db: AsyncSession) -> tuple[str, str]:
    """Seed: insert a test org + api_key. Returns (org_id, raw_key_hash)."""
    import hashlib
    import uuid

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


async def _create_alert_rule(
    db: AsyncSession, org_id: str, metric: str, threshold: float
) -> str:
    result = await db.execute(
        text(
            "INSERT INTO alert_rules (org_id, metric, threshold) "
            "VALUES (:org_id, :metric, :threshold) RETURNING id"
        ),
        {"org_id": org_id, "metric": metric, "threshold": threshold},
    )
    await db.commit()
    return str(result.fetchone()[0])


# ---- fixtures --------------------------------------------------------------

BASE_URL = os.getenv("OBSERVEML_API_URL", "http://localhost:8000")


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def test_credentials():
    """Create a fresh org + API key for the test module."""
    db = await _get_session()
    try:
        org_id, raw_key = await _create_org_and_key(db)
        yield org_id, raw_key
    finally:
        await db.close()


# ---- tests -----------------------------------------------------------------

@pytest.mark.asyncio
async def test_ingest_returns_accepted(test_credentials):
    """POST /v1/ingest with valid key returns accepted count."""
    _, raw_key = test_credentials
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
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


@pytest.mark.asyncio
async def test_alert_rule_crud(test_credentials):
    """Create, fetch, and delete an alert rule via the API."""
    _, raw_key = test_credentials
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Create
        create_resp = await client.post(
            "/v1/alerts",
            json={"metric": "avg_latency_ms", "threshold": 1000.0},
            headers={"x-api-key": raw_key},
        )
        assert create_resp.status_code == 201
        rule_id = create_resp.json()["id"]

        # List
        list_resp = await client.get("/v1/alerts", headers={"x-api-key": raw_key})
        assert list_resp.status_code == 200
        assert any(r["id"] == rule_id for r in list_resp.json())

        # Delete
        del_resp = await client.delete(
            f"/v1/alerts/{rule_id}", headers={"x-api-key": raw_key}
        )
        assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_anomaly_fires_alert(test_credentials):
    """Full flow: ingest high-latency events → anomaly check → alert_fired row created."""
    org_id, raw_key = test_credentials

    # Create a low threshold (50 ms) so any real event triggers it
    db = await _get_session()
    try:
        rule_id = await _create_alert_rule(
            db, org_id, "avg_latency_ms", threshold=50.0
        )
    finally:
        await db.close()

    # Ingest events with latency far above threshold
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.post(
            "/v1/ingest",
            json={
                "events": [
                    {"model": "gpt-4o", "latency_ms": 5000, "call_site": ""}
                    for _ in range(5)
                ]
            },
            headers={"x-api-key": raw_key},
        )
    assert resp.status_code == 200

    # Wait briefly for background anomaly task to complete
    await asyncio.sleep(2)

    # Verify alert_fired row exists
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


@pytest.mark.asyncio
async def test_alert_feed_returns_fired_alert(test_credentials):
    """GET /v1/alerts/feed must include the alert from the previous test."""
    _, raw_key = test_credentials
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.get("/v1/alerts/feed", headers={"x-api-key": raw_key})
    assert resp.status_code == 200
    feed = resp.json()
    assert len(feed) >= 1
    assert any(item["metric"] == "avg_latency_ms" for item in feed)


@pytest.mark.asyncio
async def test_ingest_rejects_invalid_key():
    """POST /v1/ingest with a bad API key must return 401."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.post(
            "/v1/ingest",
            json={"events": [{"model": "gpt-4o", "latency_ms": 100}]},
            headers={"x-api-key": "totally-invalid-key"},
        )
    assert resp.status_code == 401


# ---- OB-29: Regression endpoint E2E tests ---------------------------------


@pytest.mark.asyncio
async def test_regression_endpoint_returns_list(test_credentials):
    """GET /v1/compare/regression must return HTTP 200 with a JSON array."""
    _, raw_key = test_credentials
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.get(
            "/v1/compare/regression",
            params={"window_hours": 24},
            headers={"x-api-key": raw_key},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list), "Expected a JSON array"
    if body:
        first = body[0]
        assert "call_site" in first
        assert "metric" in first
        assert "is_regression" in first
        assert isinstance(first["is_regression"], bool)


@pytest.mark.asyncio
async def test_regression_stable_data_produces_no_regression(test_credentials):
    """Ingest low-variance uniform latencies; regression endpoint should
    report no regressions (all is_regression == False).

    This is a best-effort test — if the data window is insufficient for
    Welch's z-test, the endpoint still returns 200 with an empty or stable list.
    """
    _, raw_key = test_credentials
    stable_latency = 200

    # Ingest 20 identical calls to saturate both comparison windows
    events = [
        {
            "model": "gpt-3.5-turbo",
            "latency_ms": stable_latency,
            "input_tokens": 40,
            "output_tokens": 20,
            "cost_usd": 0.0002,
            "call_site": "regression-stability-test",
        }
        for _ in range(20)
    ]
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        ingest_resp = await client.post(
            "/v1/ingest",
            json={"events": events},
            headers={"x-api-key": raw_key},
        )
        assert ingest_resp.status_code == 200

        # Short wait to allow ClickHouse eventual consistency
        await asyncio.sleep(1)

        reg_resp = await client.get(
            "/v1/compare/regression",
            params={"window_hours": 24},
            headers={"x-api-key": raw_key},
        )
    assert reg_resp.status_code == 200
    findings = reg_resp.json()
    regressions = [f for f in findings if f.get("is_regression") is True]
    assert regressions == [], (
        f"Expected no regressions for stable data, found: {regressions}"
    )


@pytest.mark.asyncio
async def test_compare_models_returns_list(test_credentials):
    """GET /v1/compare/models must return 200 with a well-formed list."""
    _, raw_key = test_credentials
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.get(
            "/v1/compare/models", headers={"x-api-key": raw_key}
        )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    if body:
        row = body[0]
        assert "model" in row
        assert "avg_latency_ms" in row
        assert "error_rate" in row
        assert "total_cost_usd" in row


@pytest.mark.asyncio
async def test_compare_cost_returns_list(test_credentials):
    """GET /v1/compare/cost must return 200 with day-level cost rows."""
    _, raw_key = test_credentials
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
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
