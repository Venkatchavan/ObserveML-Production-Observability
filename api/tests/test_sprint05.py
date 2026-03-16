"""OB-41 to OB-49: Sprint 05 integration tests — teams, billing, session,
prompt hashes, key rotation, GDPR deletion.

Fixtures (db_init, test_credentials) are auto-discovered from conftest.py.
333-Line Law: this file is intentionally < 333 lines.
"""

from unittest.mock import patch


from conftest import _make_client


# ---------------------------------------------------------------------------
# OB-41: Team management
# ---------------------------------------------------------------------------


async def test_team_invite_returns_member(test_credentials):
    """POST /v1/teams/invite must create a member with the specified role."""
    _, raw_key = test_credentials
    async with _make_client() as client:
        resp = await client.post(
            "/v1/teams/invite",
            json={"email": "analyst@example.com", "role": "analyst"},
            headers={"x-api-key": raw_key},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["user_email"] == "analyst@example.com"
    assert body["role"] == "analyst"
    assert "id" in body


async def test_team_list_members(test_credentials):
    """GET /v1/teams/members must return the invited member."""
    _, raw_key = test_credentials
    # Invite one first
    async with _make_client() as client:
        await client.post(
            "/v1/teams/invite",
            json={"email": "viewer@example.com", "role": "viewer"},
            headers={"x-api-key": raw_key},
        )
        resp = await client.get("/v1/teams/members", headers={"x-api-key": raw_key})
    assert resp.status_code == 200
    members = resp.json()
    assert isinstance(members, list)
    emails = [m["user_email"] for m in members]
    assert "viewer@example.com" in emails


# ---------------------------------------------------------------------------
# OB-43: Usage metering
# ---------------------------------------------------------------------------


async def test_billing_usage_returns_status(test_credentials):
    """GET /v1/billing/usage must include plan and free_tier_limit."""
    _, raw_key = test_credentials
    with patch("app.services.billing_service._count_events_this_month", return_value=42):
        async with _make_client() as client:
            resp = await client.get("/v1/billing/usage", headers={"x-api-key": raw_key})
    assert resp.status_code == 200
    body = resp.json()
    assert "plan" in body
    assert "events_this_month" in body
    assert "free_tier_limit" in body
    assert body["free_tier_limit"] == 10_000
    assert body["events_this_month"] == 42


# ---------------------------------------------------------------------------
# OB-42: Free tier enforcement
# ---------------------------------------------------------------------------


async def test_ingest_over_free_tier_returns_402(test_credentials):
    """POST /v1/ingest must return 402 when free tier is exceeded."""
    _, raw_key = test_credentials
    with patch(
        "app.services.billing_service._count_events_this_month",
        return_value=10_001,
    ):
        async with _make_client() as client:
            resp = await client.post(
                "/v1/ingest",
                json={
                    "events": [
                        {
                            "model": "gpt-4o",
                            "latency_ms": 100,
                            "input_tokens": 10,
                            "output_tokens": 5,
                            "cost_usd": 0.0001,
                            "call_site": "billing-test",
                        }
                    ]
                },
                headers={"x-api-key": raw_key},
            )
    assert resp.status_code == 402, f"Expected 402, got {resp.status_code}"


# ---------------------------------------------------------------------------
# OB-44: Prompt hash analytics
# ---------------------------------------------------------------------------


async def test_prompt_hash_analytics_returns_list(test_credentials):
    """GET /v1/metrics/prompt-hashes must return a list (may be empty)."""
    _, raw_key = test_credentials
    async with _make_client() as client:
        resp = await client.get(
            "/v1/metrics/prompt-hashes",
            params={"limit": 5},
            headers={"x-api-key": raw_key},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    # If data is present, confirm no prompt text leaks — only hash + frequency
    for row in body:
        assert "prompt_hash" in row
        assert "frequency" in row
        assert "prompt" not in row
        assert "response" not in row


# ---------------------------------------------------------------------------
# OB-45: Session grouping
# ---------------------------------------------------------------------------


async def test_session_summary_after_ingest(test_credentials):
    """Ingest with session_id → GET /v1/metrics/session/{id} returns summary."""
    _, raw_key = test_credentials
    session = "sprint05-test-session"
    async with _make_client() as client:
        ingest_resp = await client.post(
            "/v1/ingest",
            json={
                "events": [
                    {
                        "model": "gpt-4o",
                        "latency_ms": 150,
                        "input_tokens": 40,
                        "output_tokens": 20,
                        "cost_usd": 0.0008,
                        "call_site": "session-test",
                        "session_id": session,
                    }
                ]
            },
            headers={"x-api-key": raw_key},
        )
    assert ingest_resp.status_code == 200
    assert ingest_resp.json()["accepted"] == 1
    # ClickHouse session query may return empty in CI (no real CH),
    # but the endpoint must not 500.
    async with _make_client() as client:
        resp = await client.get(f"/v1/metrics/session/{session}", headers={"x-api-key": raw_key})
    assert resp.status_code in (200, 404)


# ---------------------------------------------------------------------------
# OB-47: API key rotation
# ---------------------------------------------------------------------------


async def test_rotate_api_key_revokes_old_key(test_credentials):
    """POST /v1/org/rotate-key must return a new key; old key returns 401."""
    _, raw_key = test_credentials
    async with _make_client() as client:
        rotate_resp = await client.post("/v1/org/rotate-key", headers={"x-api-key": raw_key})
    assert rotate_resp.status_code == 200
    body = rotate_resp.json()
    assert "api_key" in body
    new_key = body["api_key"]
    assert new_key != raw_key
    assert new_key.startswith("obs_live_")

    # Old key must now be revoked
    async with _make_client() as client:
        old_resp = await client.get("/v1/metrics", headers={"x-api-key": raw_key})
    assert old_resp.status_code == 401

    # New key must work
    async with _make_client() as client:
        new_resp = await client.get("/v1/metrics", headers={"x-api-key": new_key})
    assert new_resp.status_code == 200


# ---------------------------------------------------------------------------
# OB-48: GDPR data deletion request
# ---------------------------------------------------------------------------


async def test_data_deletion_request_returns_token(test_credentials):
    """POST /v1/org/request-data-deletion must return a deletion token."""
    _, raw_key = test_credentials
    async with _make_client() as client:
        resp = await client.post("/v1/org/request-data-deletion", headers={"x-api-key": raw_key})
    assert resp.status_code == 202
    body = resp.json()
    assert "deletion_token" in body
    assert body["cooling_off_hours"] == 24
    assert len(body["deletion_token"]) == 64  # 32-byte hex = 64 chars


async def test_data_deletion_cooling_off_enforced(test_credentials):
    """DELETE /v1/org/data must refuse execution before 24h cooling-off."""
    _, raw_key = test_credentials
    # Request a token
    async with _make_client() as client:
        req_resp = await client.post(
            "/v1/org/request-data-deletion", headers={"x-api-key": raw_key}
        )
    token = req_resp.json()["deletion_token"]
    # Immediately try to execute — should be refused (< 24h)
    async with _make_client() as client:
        del_resp = await client.delete(
            f"/v1/org/data?token={token}", headers={"x-api-key": raw_key}
        )
    assert del_resp.status_code == 409
    assert "Cooling-off" in del_resp.json()["detail"]
