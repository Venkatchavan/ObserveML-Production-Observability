"""
ObserveML Pydantic models.

Observer Principle: MetricEvent intentionally has NO prompt or response fields.
Only metadata is transmitted: model, latency, tokens, cost, error.
"""
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
import uuid


class MetricEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_site: str = ""
    model: str
    latency_ms: int
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    error: bool = False
    error_code: str = ""
    # reason: prompt_hash is SHA-256(prompt+response) for dedup only.
    # Raw prompt/response is NEVER transmitted. Observer Principle enforced.
    prompt_hash: str = ""


class IngestRequest(BaseModel):
    events: List[MetricEvent]


class IngestResponse(BaseModel):
    accepted: int
    rejected: int


class MetricSummary(BaseModel):
    call_site: str
    model: str
    avg_latency_ms: float
    total_calls: int
    total_cost_usd: float
    error_rate: float


class TrendPoint(BaseModel):
    ts: str
    avg_latency_ms: float
    total_calls: int


class TrendResponse(BaseModel):
    call_site: Optional[str]
    points: List[TrendPoint]


# ---------- Alert Rule models (OB-12) ----------

class AlertRuleCreate(BaseModel):
    call_site: Optional[str] = None  # None = apply to all call sites
    metric: str                       # avg_latency_ms | error_rate | cost_usd
    threshold: float
    webhook_url: Optional[str] = None


class AlertRuleResponse(BaseModel):
    id: UUID
    org_id: UUID
    call_site: Optional[str]
    metric: str
    threshold: float
    webhook_url: Optional[str]
    created_at: datetime


class AlertFeedItem(BaseModel):
    id: UUID
    rule_id: Optional[UUID]
    call_site: Optional[str]
    metric: str
    current_value: float
    threshold: float
    fired_at: datetime


# ---------- Comparison + Regression models (OB-21/22/23) ----------

class ModelComparisonRow(BaseModel):
    model: str
    avg_latency_ms: float
    total_calls: int
    total_cost_usd: float
    error_rate: float
    avg_input_tokens: float
    avg_output_tokens: float


class RegressionFinding(BaseModel):
    call_site: str
    metric: str               # latency_ms | error_rate | cost_usd
    current_mean: float
    baseline_mean: float
    z_score: float
    p_value: float
    is_regression: bool       # True if p<0.05 AND current > baseline


class CostRow(BaseModel):
    model: str
    day: str
    total_cost_usd: float
    total_calls: int
    avg_cost_per_call: float
