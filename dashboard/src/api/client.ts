const BASE_URL = (import.meta as any).env?.VITE_API_URL ?? "http://localhost:8000";

export interface MetricSummary {
  call_site: string;
  model: string;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  total_calls: number;
  total_cost_usd: number;
  error_rate: number;
}

export interface TrendPoint {
  ts: string;
  avg_latency_ms: number;
  total_calls: number;
}

export interface TrendResponse {
  call_site: string | null;
  points: TrendPoint[];
}

// OB-12/13: Alert types
export interface AlertRule {
  id: string;
  org_id: string;
  call_site: string | null;
  metric: string;
  threshold: number;
  webhook_url: string | null;
  created_at: string;
}

export interface AlertRuleCreate {
  call_site: string | null;
  metric: string;
  threshold: number;
  webhook_url: string | null;
}

export interface AlertFeedItem {
  id: string;
  rule_id: string | null;
  call_site: string | null;
  metric: string;
  current_value: number;
  threshold: number;
  fired_at: string;
}

function headers(): HeadersInit {
  const key = localStorage.getItem("observeml_api_key") ?? "";
  return { "Content-Type": "application/json", "x-api-key": key };
}

export async function fetchMetrics(callSite?: string): Promise<MetricSummary[]> {
  const url = new URL(`${BASE_URL}/v1/metrics`);
  if (callSite) url.searchParams.set("call_site", callSite);
  const res = await fetch(url.toString(), { headers: headers() });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

export async function fetchTrend(callSite?: string): Promise<TrendResponse> {
  const url = new URL(`${BASE_URL}/v1/metrics/trend`);
  if (callSite) url.searchParams.set("call_site", callSite);
  const res = await fetch(url.toString(), { headers: headers() });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

// OB-12/13: Alert rule CRUD

export async function fetchAlertRules(): Promise<AlertRule[]> {
  const res = await fetch(`${BASE_URL}/v1/alerts`, { headers: headers() });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

export async function createAlertRule(body: AlertRuleCreate): Promise<AlertRule> {
  const res = await fetch(`${BASE_URL}/v1/alerts`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

export async function deleteAlertRule(ruleId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/v1/alerts/${ruleId}`, {
    method: "DELETE",
    headers: headers(),
  });
  if (!res.ok && res.status !== 204) throw new Error(`API ${res.status}`);
}

export async function fetchAlertFeed(): Promise<AlertFeedItem[]> {
  const res = await fetch(`${BASE_URL}/v1/alerts/feed`, { headers: headers() });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

// OB-21/22/23: Comparison types + fetchers

export interface ModelComparisonRow {
  model: string;
  avg_latency_ms: number;
  total_calls: number;
  total_cost_usd: number;
  error_rate: number;
  avg_input_tokens: number;
  avg_output_tokens: number;
}

export interface RegressionFinding {
  call_site: string;
  metric: string;
  current_mean: number;
  baseline_mean: number;
  z_score: number;
  p_value: number;
  is_regression: boolean;
}

export interface CostRow {
  model: string;
  day: string;
  total_cost_usd: number;
  total_calls: number;
  avg_cost_per_call: number;
}

export async function fetchModelComparison(): Promise<ModelComparisonRow[]> {
  const res = await fetch(`${BASE_URL}/v1/compare/models`, { headers: headers() });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

export async function fetchRegressions(windowHours = 24): Promise<RegressionFinding[]> {
  const url = new URL(`${BASE_URL}/v1/compare/regression`);
  url.searchParams.set("window_hours", String(windowHours));
  const res = await fetch(url.toString(), { headers: headers() });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

export async function fetchCostBreakdown(days = 7): Promise<CostRow[]> {
  const url = new URL(`${BASE_URL}/v1/compare/cost`);
  url.searchParams.set("days", String(days));
  const res = await fetch(url.toString(), { headers: headers() });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

// OB-35: Model routing
export interface ModelRoutingRecommendation {
  model: string;
  avg_latency_ms: number;
  avg_cost_usd: number;
  error_rate: number;
  total_calls: number;
  meets_constraints: boolean;
  caveat: string;
}

export async function fetchModelRouting(
  maxLatencyMs = 5000,
  maxCostUsd = 1.0,
): Promise<ModelRoutingRecommendation[]> {
  const url = new URL(`${BASE_URL}/v1/compare/routing`);
  url.searchParams.set("max_latency_ms", String(maxLatencyMs));
  url.searchParams.set("max_cost_usd", String(maxCostUsd));
  const res = await fetch(url.toString(), { headers: headers() });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

// OB-34: Token budget
export interface TokenBudget {
  daily_avg_cost_usd: number;
  projected_monthly_cost_usd: number;
  days_in_month: number;
}

export async function fetchTokenBudget(): Promise<TokenBudget> {
  const res = await fetch(`${BASE_URL}/v1/metrics/token-budget`, { headers: headers() });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

// OB-38: CSV export
export async function downloadMetricsCsv(days = 30): Promise<void> {
  const url = new URL(`${BASE_URL}/v1/metrics/export`);
  url.searchParams.set("days", String(days));
  const res = await fetch(url.toString(), { headers: headers() });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  const blob = await res.blob();
  const href = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = href;
  a.download = `observeml-export-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(href);
}

// OB-42/OB-43: Billing & usage metering
export interface UsageStatus {
  org_id: string;
  plan: string;
  events_this_month: number;
  free_tier_limit: number;
  over_limit: boolean;
  projected_cost_usd: number;
}

export async function fetchBillingUsage(): Promise<UsageStatus> {
  const res = await fetch(`${BASE_URL}/v1/billing/usage`, { headers: headers() });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

// OB-41: Team management
export interface TeamMember {
  id: string;
  org_id: string;
  user_email: string;
  role: "owner" | "analyst" | "viewer";
  invited_at: string;
  accepted_at: string | null;
}

export async function fetchTeamMembers(): Promise<TeamMember[]> {
  const res = await fetch(`${BASE_URL}/v1/teams/members`, { headers: headers() });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

export async function inviteTeamMember(
  email: string,
  role: "owner" | "analyst" | "viewer",
): Promise<TeamMember> {
  const res = await fetch(`${BASE_URL}/v1/teams/invite`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ email, role }),
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

// OB-47: API key rotation
export async function rotateApiKey(): Promise<{ api_key: string; message: string }> {
  const res = await fetch(`${BASE_URL}/v1/org/rotate-key`, {
    method: "POST",
    headers: headers(),
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

// OB-44: Prompt hash analytics
export interface PromptHashRow {
  prompt_hash: string;
  frequency: number;
}

export async function fetchPromptHashes(limit = 10): Promise<PromptHashRow[]> {
  const url = new URL(`${BASE_URL}/v1/metrics/prompt-hashes`);
  url.searchParams.set("limit", String(limit));
  const res = await fetch(url.toString(), { headers: headers() });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

// OB-45: Session summary
export interface SessionSummary {
  session_id: string;
  call_count: number;
  avg_latency_ms: number;
  total_cost_usd: number;
  error_rate: number;
}

export async function fetchSessionSummary(sessionId: string): Promise<SessionSummary> {
  const res = await fetch(`${BASE_URL}/v1/metrics/session/${encodeURIComponent(sessionId)}`, {
    headers: headers(),
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

