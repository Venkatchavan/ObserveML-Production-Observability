# Architecture â€” ObserveML
**v1.0.3 | 2026-03-12 | Backend Architect**

---

## 1. System Overview

```
Developer's LLM App
  â”‚
  â”‚ observe(llm_call)   [< 2ms overhead â€” fire and forget]
  â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  ObserveML Python SDK / JS SDK         â”‚
â”‚  â€¢ Wraps LLM call                      â”‚
â”‚  â€¢ Captures: latency, tokens, cost,    â”‚
â”‚    error, model, call_site fingerprint â”‚
â”‚  â€¢ Fire-and-forget async flush         â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                  â”‚ HTTPS batch (async, non-blocking)
                  â–¼
       â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
       â”‚  Ingest API          â”‚
       â”‚  (FastAPI)           â”‚
       â”‚  â€¢ Idempotent write  â”‚
       â”‚  â€¢ Schema validation â”‚
       â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
              â”‚
    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    â–¼                   â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”     â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ClickHouseâ”‚     â”‚  PostgreSQL   â”‚
â”‚ â€¢ metricsâ”‚     â”‚  â€¢ orgs       â”‚
â”‚ â€¢ events â”‚     â”‚  â€¢ api keys   â”‚
â”‚ â€¢ trends â”‚     â”‚  â€¢ alerts     â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜     â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
              â”‚
              â–¼
    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    â”‚  Dashboard API   â”‚
    â”‚  (FastAPI)       â”‚
    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
              â”‚
              â–¼
    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    â”‚  React Dashboard â”‚
    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## 2. Component Inventory

| Component | Technology | Responsibility |
|-----------|-----------|----------------|
| Python SDK | Python 3.9+ (httpx async) | Instrument LLM calls |
| JS SDK | TypeScript (node-fetch) | Instrument LLM calls (Node/browser) |
| Java SDK | Java 11+ (stdlib HttpClient) | Instrument LLM calls (JVM / Android) |
| Ingest API | FastAPI | Receive + validate metric events; 402 on free-tier breach |
| Analytics DB | ClickHouse | Time-series metrics storage + aggregation |
| Metadata DB | PostgreSQL | Orgs, API keys, alert rules, teams, billing, audit log |
| Dashboard API | FastAPI | Serve dashboard metrics |
| Dashboard UI | React + Recharts | Visualize metrics (Usage, Live Feed, Comparison) |
| Deploy | Fly.io | Production hosting |

---

## 3. ADR-01: ClickHouse for metrics storage

**Status**: Accepted  
**Decision**: ClickHouse (not PostgreSQL time-series) for metric events.  
**Reason**: ClickHouse columnar storage provides 10x+ query performance over PostgreSQL at > 1M events. Required to support real-time aggregation for high-volume SDK users. PostgreSQL retained for relational metadata.

---

## 4. ADR-02: Fire-and-forget SDK architecture

**Status**: Accepted  
**Decision**: SDK flushes metrics asynchronously in background thread/promise. No blocking.  
**Reason**: < 2ms overhead requirement. The LLM call must complete before any metric is sent. Buffered batch send every 5 seconds (or 100 events) with automatic retry.

---

## 5. API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/ingest` | API key | Batch metric event ingest |
| GET | `/v1/metrics` | API key | Aggregated metrics (org-scoped) |
| GET | `/v1/metrics/trend` | API key | 7-day trend data |
| POST | `/v1/alerts` | API key | Create alert rule |
| GET | `/health` | None | Health check |

---

## 6. SDK Overhead Budget

```
observe(llm_call) budget: < 2ms
  â”œâ”€â”€ Capture metadata:      ~0.1ms
  â”œâ”€â”€ Enqueue to buffer:     ~0.1ms
  â””â”€â”€ Return to caller:      ~0.1ms

Async flush (background):
  â”œâ”€â”€ Serialize batch:       ~0.5ms
  â””â”€â”€ HTTP POST (fire):      non-blocking
```

---

## 7. Security Considerations

- Prompt/response content NEVER transmitted to ObserveML (only hashes)
- API keys scoped per organization; no cross-org data access
- Ingest endpoint idempotent on `event_id` (prevents replay amplification)

---

## 8. 333-Line Law Compliance

- `sdk/python/observe.py` â€” public API surface only
- `sdk/python/_buffer.py` â€” async buffer + flush only
- `api/ingest/router.py` â€” ingest validation + write only
- `api/metrics/router.py` â€” aggregation queries only

