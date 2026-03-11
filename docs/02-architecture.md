# Architecture — ObserveML
**v0.1.0 | 2026-03-11 | Backend Architect**

---

## 1. System Overview

```
Developer's LLM App
  │
  │ observe(llm_call)   [< 2ms overhead — fire and forget]
  ▼
┌────────────────────────────────────────┐
│  ObserveML Python SDK / JS SDK         │
│  • Wraps LLM call                      │
│  • Captures: latency, tokens, cost,    │
│    error, model, call_site fingerprint │
│  • Fire-and-forget async flush         │
└─────────────────┬──────────────────────┘
                  │ HTTPS batch (async, non-blocking)
                  ▼
       ┌──────────────────────┐
       │  Ingest API          │
       │  (FastAPI)           │
       │  • Idempotent write  │
       │  • Schema validation │
       └──────┬───────────────┘
              │
    ┌─────────┴─────────┐
    ▼                   ▼
┌──────────┐     ┌───────────────┐
│ClickHouse│     │  PostgreSQL   │
│ • metrics│     │  • orgs       │
│ • events │     │  • api keys   │
│ • trends │     │  • alerts     │
└──────────┘     └───────────────┘
              │
              ▼
    ┌──────────────────┐
    │  Dashboard API   │
    │  (FastAPI)       │
    └──────────────────┘
              │
              ▼
    ┌──────────────────┐
    │  React Dashboard │
    └──────────────────┘
```

---

## 2. Component Inventory

| Component | Technology | Responsibility |
|-----------|-----------|----------------|
| Python SDK | Python 3.9+ (httpx async) | Instrument LLM calls |
| JS SDK | TypeScript (node-fetch) | Instrument LLM calls (Node/browser) |
| Ingest API | FastAPI | Receive + validate metric events |
| Analytics DB | ClickHouse | Time-series metrics storage + aggregation |
| Metadata DB | PostgreSQL | Orgs, API keys, alert rules |
| Dashboard API | FastAPI | Serve dashboard metrics |
| Dashboard UI | React + Recharts | Visualize metrics |
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
  ├── Capture metadata:      ~0.1ms
  ├── Enqueue to buffer:     ~0.1ms
  └── Return to caller:      ~0.1ms

Async flush (background):
  ├── Serialize batch:       ~0.5ms
  └── HTTP POST (fire):      non-blocking
```

---

## 7. Security Considerations

- Prompt/response content NEVER transmitted to ObserveML (only hashes)
- API keys scoped per organization; no cross-org data access
- Ingest endpoint idempotent on `event_id` (prevents replay amplification)

---

## 8. 333-Line Law Compliance

- `sdk/python/observe.py` — public API surface only
- `sdk/python/_buffer.py` — async buffer + flush only
- `api/ingest/router.py` — ingest validation + write only
- `api/metrics/router.py` — aggregation queries only
