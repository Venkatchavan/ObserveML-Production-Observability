"""OB-41: Team management — invite members, list members (RBAC).

Roles: owner (full access) | analyst (read + alerts) | viewer (read-only).
333-Line Law: this file is intentionally < 80 lines.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_db
from app.models.teams import TeamInvite, TeamInviteResponse
from app.services.api_key_service import validate_api_key

router = APIRouter()

_VALID_ROLES = {"owner", "analyst", "viewer"}


@router.post("/teams/invite", response_model=TeamInviteResponse, status_code=201)
async def invite_member(
    body: TeamInvite,
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """OB-41: Invite a user to the org with the specified RBAC role."""
    org_id = await validate_api_key(x_api_key, db)
    if not org_id:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    if body.role not in _VALID_ROLES:
        raise HTTPException(status_code=422, detail=f"role must be one of {sorted(_VALID_ROLES)}")
    member_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.execute(
        text(
            "INSERT INTO team_members (id, org_id, user_email, role) "
            "VALUES (:id, :org_id, :email, :role)"
        ),
        {"id": member_id, "org_id": org_id, "email": body.email, "role": body.role},
    )
    await db.commit()
    return TeamInviteResponse(
        id=member_id,
        org_id=org_id,
        user_email=body.email,
        role=body.role,
        invited_at=now_iso,
    )


@router.get("/teams/members")
async def list_members(
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """OB-41: List all team members of the org with their roles."""
    org_id = await validate_api_key(x_api_key, db)
    if not org_id:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    result = await db.execute(
        text(
            "SELECT id::text, org_id::text, user_email, role, "
            "invited_at::text, accepted_at::text "
            "FROM team_members WHERE org_id = :org_id ORDER BY invited_at DESC"
        ),
        {"org_id": org_id},
    )
    return [
        {
            "id": r[0],
            "org_id": r[1],
            "user_email": r[2],
            "role": r[3],
            "invited_at": r[4],
            "accepted_at": r[5],
        }
        for r in result.fetchall()
    ]
