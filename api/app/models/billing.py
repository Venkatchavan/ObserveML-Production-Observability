"""OB-42/OB-43: Pydantic models for billing and usage metering.

333-Line Law: this file is intentionally small.
"""

from pydantic import BaseModel


class UsageStatus(BaseModel):
    org_id: str
    plan: str
    events_this_month: int
    free_tier_limit: int
    over_limit: bool
    projected_cost_usd: float
