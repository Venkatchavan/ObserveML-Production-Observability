"""OB-41: Pydantic models for team management (RBAC).

Observer Principle: no prompt/response fields anywhere.
333-Line Law: this file is intentionally small.
"""

from typing import Literal, Optional
from pydantic import BaseModel


class TeamInvite(BaseModel):
    email: str
    role: Literal["owner", "analyst", "viewer"] = "viewer"


class TeamInviteResponse(BaseModel):
    id: str
    org_id: str
    user_email: str
    role: str
    invited_at: str
    accepted_at: Optional[str] = None


class TeamMember(BaseModel):
    id: str
    org_id: str
    user_email: str
    role: str
    invited_at: str
    accepted_at: Optional[str] = None
