"""OB-43: Billing router — GET /v1/billing/usage (usage metering dashboard).

333-Line Law: this file is intentionally < 30 lines.
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_db
from app.services.api_key_service import validate_api_key
from app.services.billing_service import get_usage_status

router = APIRouter()


@router.get("/billing/usage")
async def get_billing_usage(
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """OB-43: Monthly event count + cost info for the usage metering dashboard."""
    org_id = await validate_api_key(x_api_key, db)
    if not org_id:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    return await get_usage_status(org_id, db)
