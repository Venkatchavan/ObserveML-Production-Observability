# Sprint 01 — ObserveML
**Duration**: 2 weeks | **Goal**: Python + JS SDKs track a metric and dashboard displays it  
**Version**: v0.1.0 | **Agent**: Sprint Prioritizer

---

## Sprint Goal

> A developer installs the Python or JS SDK, calls `track()`, and can see the metric in the ObserveML dashboard within 5 seconds.

---

## Tickets

| ID | Title | Points | Owner |
|----|-------|--------|-------|
| OB-01 | FastAPI ingest endpoint + API key validation | 3 | Backend Architect |
| OB-02 | ClickHouse schema: metric_events with 90-day TTL | 3 | Database Architect |
| OB-03 | PostgreSQL schema: orgs, api_keys (hashed) | 2 | Database Architect |
| OB-04 | Python SDK: `track()` async fire-and-forget (no prompt content) | 5 | Senior Developer |
| OB-05 | JS/TS SDK: `track()` async fire-and-forget (no prompt content) | 5 | Senior Developer |
| OB-06 | Dashboard: basic time-series chart per metric name | 3 | Frontend Developer |
| OB-07 | SDK overhead benchmark: p99 < 1ms (pytest-benchmark) | 2 | QA Engineer |
| OB-08 | SDK content-leak test: no prompt/response in payload | 2 | QA Engineer |
| OB-09 | Ingest rate limiter: 100 req/min per API key | 2 | Backend Architect |
| OB-10 | CI pipeline + Docker Compose dev environment | 2 | DevOps Automator |

**Total**: 29 points

---

## Daily Targets

| Day | Focus |
|-----|-------|
| 1–2 | OB-01, OB-02, OB-03 (foundation) |
| 3–5 | OB-04, OB-05 (SDK development — parallel) |
| 6–7 | OB-06 (dashboard) |
| 8–9 | OB-07, OB-08 (overhead + content-leak tests) |
| 10 | OB-09, OB-10 (rate limiter + CI) |

---

## Definition of Done

- [ ] Python SDK `track()` call captured in ClickHouse within 5s
- [ ] JS SDK `track()` call captured in ClickHouse within 5s
- [ ] SDK overhead p99 < 1ms (benchmark passes)
- [ ] Content-leak test: zero `prompt`/`response` keys in payload
- [ ] Org isolation verified: Org A events not visible to Org B
- [ ] All modules ≤ 333 lines (333-Line Law)
- [ ] CI passes: lint + test (≥80%) + security scan

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| ClickHouse testcontainers setup complex | MEDIUM | MEDIUM | Use ClickHouse test instance; add to Docker Compose |
| SDK async overhead exceeds 1ms | LOW | HIGH | Profile early (Day 5); use background thread, not asyncio |
| npm/PyPI publish pipeline complex | LOW | LOW | Defer to Sprint 2 |

---

## Śhāstrārtha Sprint Review Checkpoint

**Viṣaya**: Did we ship an SDK that captures metrics without capturing prompt content?  
**Saṃśaya**: Was the content-leak test actually run, or just assumed to pass?  
**Siddhānta**: Ship only if content-leak test passes AND SDK overhead p99 < 1ms. No exceptions.
