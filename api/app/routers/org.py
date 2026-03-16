"""OB-47/OB-48: Org management — API key rotation + GDPR data deletion.

Śhāstrārtha checkpoint (OB-48):
  Deletion is a two-step process:
    1. POST /v1/org/request-data-deletion — issues token, 24h cooling-off.
    2. DELETE /v1/org/data?token=<token> — executes after cooling-off.
  Billing history (usage_billing) is preserved.

333-Line Law: this file is intentionally < 90 lines.
"""

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_db
from app.services.api_key_service import hash_api_key, validate_api_key
from app.services.deletion_service import execute_deletion, request_deletion

router = APIRouter()


@router.post("/org/rotate-key")
async def rotate_api_key(
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """OB-47: Revoke current API key, issue a new one, write audit log.

    Old key returns 401 within one request after rotation.
    """
    org_id = await validate_api_key(x_api_key, db)
    if not org_id:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    new_raw = f"obs_live_{secrets.token_hex(24)}"
    old_hash = hash_api_key(x_api_key)
    new_hash = hash_api_key(new_raw)

    await db.execute(
        text("UPDATE api_keys SET revoked_at = NOW() WHERE key_hash = :h"),
        {"h": old_hash},
    )
    await db.execute(
        text(
            "INSERT INTO api_keys (org_id, key_hash, name) VALUES (:org_id, :key_hash, 'rotated')"
        ),
        {"org_id": org_id, "key_hash": new_hash},
    )
    await db.execute(
        text(
            "INSERT INTO audit_log (org_id, action, actor, details) "
            "VALUES (:org_id, 'API_KEY_ROTATED', 'api', 'Old key revoked; new key issued.')"
        ),
        {"org_id": org_id},
    )
    await db.commit()
    return {"api_key": new_raw, "message": "Old key revoked. Store your new key securely."}


@router.post("/org/request-data-deletion", status_code=202)
async def request_data_deletion(
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """OB-48 step 1: Issue a deletion token. Cooling-off: 24h before execution."""
    org_id = await validate_api_key(x_api_key, db)
    if not org_id:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    token = await request_deletion(org_id, db)
    return {
        "deletion_token": token,
        "cooling_off_hours": 24,
        "message": (
            "Token issued. Call DELETE /v1/org/data?token=<token> after 24h. "
            "Billing history is preserved. This action cannot be undone."
        ),
    }


@router.delete("/org/data", status_code=204)
async def execute_data_deletion(
    token: str = Query(..., description="Token from POST /v1/org/request-data-deletion"),
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """OB-48 step 2: Execute GDPR deletion after 24h cooling-off has elapsed."""
    org_id = await validate_api_key(x_api_key, db)
    if not org_id:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    error = await execute_deletion(org_id, token, db)
    if error:
        raise HTTPException(status_code=409, detail=error)
