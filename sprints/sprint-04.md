# Sprint 04 — ObserveML
**Duration**: 2 weeks | **Goal**: Sampling, streaming, and long-tail latency analytics  
**Version**: v1.1.0 | **Agent**: Sprint Prioritizer

---

## Sprint Goal

> ObserveML v1.1 introduces head-based sampling to reduce high-volume SDK overhead, a live SSE dashboard panel for real-time monitoring, and deep percentile analytics. Token budget alerting closes the loop between usage and cost governance.

---

## Tickets

| ID | Title | Points | Owner |
|----|-------|--------|-------|
| OB-31 | Head-based sampling: `sample_rate` param in SDK (0.0–1.0, default 1.0) | 3 | Senior Developer |
| OB-32 | Real-time SSE endpoint: `GET /v1/stream/events` (Server-Sent Events, last 50 events) | 5 | Backend Architect |
| OB-33 | Long-tail latency: p50/p95/p99 per call_site in metrics endpoint | 3 | Backend Architect |
| OB-34 | Token budget alerting: monthly projected spend threshold alert | 3 | Backend Architect |
| OB-35 | Model routing recommendations: cheapest model within target latency constraint | 5 | AI Engineer |
| OB-36 | SDK: OpenTelemetry trace integration (inject `trace_id` into metric events) | 5 | Senior Developer |
| OB-37 | Dashboard: live feed panel (SSE-driven, auto-scrolling, last 50 events) | 3 | Frontend Developer |
| OB-38 | Data export: 30-day CSV download from dashboard | 2 | Frontend Developer |
| OB-39 | E2E: sampling rate + SSE live feed + token budget alert fires | 3 | QA Engineer |
| OB-40 | v1.1.0 CHANGELOG + release notes | 1 | Technical Writer |

**Total**: 33 points

---

## Definition of Done

- [ ] `sample_rate=0.1` results in approximately 10% of events being tracked (tested with 1000-call fixture, ±5%)
- [ ] SSE endpoint streams new events within 500ms of ingest
- [ ] p99 latency reported correctly (validated against pre-computed reference using ClickHouse quantile function)
- [ ] Token budget alert fires when projected monthly cost (current_daily_avg × days_remaining) > threshold
- [ ] Model routing recommendation computed correctly for 3 test scenarios
- [ ] OTel trace_id propagated: call `track(trace_id=span.context.trace_id)` — stored + exposed in API
- [ ] Live feed panel renders in dashboard; reconnects automatically on SSE disconnect
- [ ] CSV download exports all columns including new p99 and trace_id fields
- [ ] Sampling does not violate Observer Principle — no content captured regardless of sample_rate

---

## Vedantic Launch Gate

> *Vairagya — The sampling feature changes the data contract. An org that switches from sample_rate=1.0 to 0.1 is no longer monitoring every call. This must be surfaced prominently in the dashboard — not hidden in settings.*

- [ ] Dashboard shows active sample rate in the header bar with a warning if < 1.0
- [ ] Observer Principle: `track_async` does not capture prompt content even when trace_id is set — MUST PASS
- [ ] SSE endpoint requires API key authentication — no unauthenticated streaming — MUST PASS
- [ ] 333-Line Law: all new modules checked

---

## Śhāstrārtha Sprint Review Checkpoint

**Viṣaya**: Is CSP/CORS configured to allow SSE connections from the dashboard domain only?  
**Saṃśaya**: SSE connections are long-lived. An improperly scoped CORS policy could allow a malicious page to read another org's event stream.  
**Siddhānta**: SSE endpoint must validate `Origin` header and enforce org-scoped API key before opening stream. `Access-Control-Allow-Origin` must not be wildcard.
