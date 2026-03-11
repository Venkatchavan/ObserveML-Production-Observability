# Test Plan â€” ObserveML
**v1.0.3 | 2026-03-12 | Senior QA Engineer**

---

## 1. Test Strategy

> *"Sakshi â€” does the SDK actually avoid capturing prompt content? Observe it, don't just assert you configured it that way."*

| Layer | Target Coverage | Tooling |
|-------|----------------|---------|
| Unit | â‰¥ 80% | pytest (backend), Jest (SDK-JS), pytest (SDK-Python) |
| Integration | Key paths | pytest + testcontainers (ClickHouse + PostgreSQL) |
| SDK Overhead | Latency impact | pytest-benchmark |
| Security | Content-leak | pytest + log inspection |
| E2E | Dashboard flow | Playwright |

---

## 2. Test Scenarios

### 2.1 Unit Tests

| Scenario | Component | Pass Criteria |
|----------|-----------|---------------|
| API key hashed correctly before storage | Key service | DB contains SHA-256 of key, not plaintext |
| Metric event schema validation rejects missing fields | Ingest validator | 422 returned for missing `event_type` |
| Org-scoped query includes org_id WHERE clause | Metrics repository | SQL reviewed for scope |
| Dedup on duplicate event_id | Ingest handler | Second identical event_id returns 200 but creates no new row |
| SDK Python: prompt content NOT in emitted payload | Python SDK | Payload inspection: no `prompt` or `response` keys |
| SDK JS: prompt content NOT in emitted payload | JS SDK | Payload inspection: no `prompt` or `response` keys |

### 2.2 Integration Tests

| Scenario | Components | Pass Criteria |
|----------|-----------|---------------|
| SDK sends event â†’ ClickHouse â†’ dashboard query returns it | SDK + API + ClickHouse | End-to-end event visibility < 5s |
| Cross-org metrics isolation | API + ClickHouse | Org A cannot read Org B events |
| API key rate limit (100 req/min) enforced | Rate limiter + API | 429 after 101st request within 1 min |
| ClickHouse TTL (90-day) schema correct | ClickHouse DDL | TTL expression present in SHOW CREATE TABLE |

### 2.3 SDK Overhead Test (pytest-benchmark)

| Scenario | Target |
|----------|--------|
| Python SDK `track()` call: no impact > 1ms (async, fire-and-forget) | p99 overhead < 1ms |
| JS SDK: no blocking main thread | `setTimeout 0` dispatch verified |

### 2.4 Security Tests

| Scenario | Expected Result |
|----------|----------------|
| Log inspection after SDK call | No `prompt` or `response` content in any log |
| Cross-org API key query | Zero results; no foreign org data |
| Large event batch (>100 events) | 413 rejected |

### 2.5 E2E (Playwright)

| Flow | Pass Criteria |
|------|---------------|
| Create API key â†’ send events â†’ view dashboard | Metrics visible within 5s |

---

## 3. Neti Neti (Out of Scope for v1)

- Multi-region ClickHouse replication testing
- Load testing at >10K events/min
- Browser compatibility beyond Chrome/Firefox
- SDK compatibility below Python 3.9 / Node 18

---

## 4. Launch Gate Criteria

- [ ] Unit â‰¥ 80% (backend + both SDKs)
- [ ] SDK content-leak test passes (zero prompt/response in payloads)
- [ ] Cross-org isolation test passes
- [ ] SDK overhead p99 < 1ms
- [ ] Playwright E2E passes in staging

