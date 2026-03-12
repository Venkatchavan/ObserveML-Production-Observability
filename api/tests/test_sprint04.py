"""OB-39: Sprint 04 endpoint tests — percentiles, CSV, token budget, routing, SSE.

Fixtures (db_init, test_credentials) are auto-discovered from conftest.py.
Helpers are imported directly from conftest.
333-Line Law: this file is intentionally < 333 lines.
"""

from conftest import _make_client


# ---------------------------------------------------------------------------
# OB-33: Latency percentiles
# ---------------------------------------------------------------------------


async def test_metrics_includes_percentiles(test_credentials):
    """GET /v1/metrics must include p50/p95/p99 latency fields."""
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


# ---------------------------------------------------------------------------
# OB-38: CSV export
# ---------------------------------------------------------------------------


async def test_metrics_export_returns_csv(test_credentials):
    """GET /v1/metrics/export must return text/csv with a header row."""
    _, raw_key = test_credentials
    async with _make_client() as client:
        resp = await client.get(
            "/v1/metrics/export",
            params={"days": 7},
            headers={"x-api-key": raw_key},
        )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    first_line = resp.text.splitlines()[0] if resp.text.strip() else ""
    if first_line:
        assert "event_id" in first_line
        assert "trace_id" in first_line


# ---------------------------------------------------------------------------
# OB-34: Token budget
# ---------------------------------------------------------------------------


async def test_token_budget_returns_projection(test_credentials):
    """GET /v1/metrics/token-budget must include projected_monthly_cost_usd."""
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


# ---------------------------------------------------------------------------
# OB-35: Model routing
# ---------------------------------------------------------------------------


async def test_compare_routing_returns_recommendations(test_credentials):
    """GET /v1/compare/routing must return a list where each row has a caveat."""
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
        assert "caveat" in row, "Vedantic gate: caveat field must always be present"
        assert "meets_constraints" in row
        assert isinstance(row["meets_constraints"], bool)


# ---------------------------------------------------------------------------
# OB-32: SSE stream
# ---------------------------------------------------------------------------


async def test_stream_events_requires_auth():
    """GET /v1/stream/events without API key must return 422."""
    async with _make_client() as client:
        resp = await client.get("/v1/stream/events")
    assert resp.status_code == 422


async def test_stream_events_returns_event_stream(test_credentials):
    """GET /v1/stream/events with valid key returns 200 + text/event-stream.

    stream.py's event_gen calls request.is_disconnected() at the top of each
    loop iteration.  With httpx ASGITransport the ASGI receive() callable
    returns {"type": "http.disconnect"} immediately once the request body has
    been consumed, so is_disconnected() returns True on the first check and the
    generator exits cleanly.  handle_async_request() can then return a complete
    Response and client.get() resolves normally — no task-cancel gymnastics.
    In production (uvicorn) receive() blocks; anyio.move_on_after(0) inside
    is_disconnected() fires, returns False, and streaming continues as usual.
    """
    _, raw_key = test_credentials
    async with _make_client() as client:
        resp = await client.get("/v1/stream/events", headers={"x-api-key": raw_key})
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# OB-36: trace_id ingestion
# ---------------------------------------------------------------------------


async def test_ingest_with_trace_id_accepted(test_credentials):
    """Ingest must accept and store an optional trace_id without error."""
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
