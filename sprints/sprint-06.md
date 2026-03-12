# Sprint 06 — ObserveML
**Duration**: 2 weeks | **Goal**: Intelligence layer — cost forecasting, AI root cause, Grafana plugin  
**Version**: v2.0.0 | **Agent**: Sprint Prioritizer

---

## Sprint Goal

> ObserveML v2.0 stops reporting what happened and starts explaining why it happened. AI-narrated root cause analysis, 7-day cost forecasting, and a model selection assistant turn raw telemetry into actionable intelligence. The Grafana plugin makes ObserveML a first-class citizen in existing ops stacks.

---

## Tickets

| ID | Title | Points | Owner |
|----|-------|--------|-------|
| OB-51 | Causal anomaly root-cause narration: AI explains p99 spike in plain English | 5 | AI Engineer |
| OB-52 | Cost forecasting: 7-day projection using linear regression over rolling 14-day window | 5 | AI Engineer |
| OB-53 | Model selection assistant: given max_cost + max_latency constraints → recommend model | 5 | AI Engineer |
| OB-54 | Enriched Slack alerts: include sparkline chart image in Slack message (via chart-as-image API) | 3 | Backend Architect |
| OB-55 | ClickHouse query result caching: Redis, 60s TTL for dashboard aggregate queries | 3 | Backend Architect |
| OB-56 | Grafana data source plugin: ClickHouse metrics → Grafana panels (signed plugin) | 5 | DevOps Automator |
| OB-57 | SDK: Ruby gem v0.1 (`observeml` gem — background thread flush, same API contract) | 3 | Senior Developer |
| OB-58 | Multi-region ClickHouse replication setup guide + Fly.io volume migration runbook | 2 | DevOps Automator |
| OB-59 | E2E: forecasting within 20% of actual + model assistant recommendation verified | 3 | QA Engineer |
| OB-60 | v2.0.0 tag + intelligence layer release notes | 1 | Technical Writer |

**Total**: 35 points

---

## Definition of Done

- [ ] Root cause narration: tested on 3 synthetic spike scenarios; AI narrative mentions the correct contributing call_site in each
- [ ] Cost forecast: 7-day projection tested against held-out 7 days of historical data; MAPE ≤ 25%
- [ ] Model selection assistant: recommends cheapest model that satisfies latency and error_rate constraints from last 7 days of data
- [ ] Enriched Slack alert: chart image encoded and attached to Slack Block Kit message
- [ ] ClickHouse cache: second dashboard load within 60s uses cached result (verified via query count metric)
- [ ] Grafana plugin: loads in Grafana 10.x, renders avg_latency_ms and call_count panels without error
- [ ] Ruby gem: `ObserveML.configure(api_key:)` and `ObserveML.track(model:, latency_ms:)` match documented API
- [ ] Ruby gem Observer Principle: no `prompt` or `response` parameter exists — MUST PASS

---

## Vedantic Launch Gate

> *Neti Neti — The model selection assistant does not know the user's prompt workload, privacy constraints, or compliance requirements. It can only reason about the metrics it has seen. Outputs must be framed as data-driven suggestions with explicit limitations stated.*

- [ ] Model selection assistant response includes a `caveat` field: "Based on observed performance only; evaluate for your specific workload"
- [ ] Cost forecast confidence interval shown in UI (not just point estimate)
- [ ] Grafana plugin authenticates with API key — no anonymous data source access
- [ ] 333-Line Law: all intelligence modules checked

---

## Śhāstrārtha Sprint Review Checkpoint

**Viṣaya**: Does the AI root-cause narration produce reliable explanations or plausible-sounding hallucinations?  
**Saṃśaya**: An LLM narrating a p99 spike from metric data could confidently assert a wrong cause. In an on-call context this misdirects the engineer's attention at the worst moment.  
**Siddhānta**: Root cause narration must include: (1) the specific metric values it is reasoning from (quoted in the response), (2) a confidence label (HIGH / MEDIUM / LOW based on data completeness), (3) a "show data" link to the raw time series. Narration without supporting data citations is not acceptable.
