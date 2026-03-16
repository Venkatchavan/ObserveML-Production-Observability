# Sprint 05 — ObserveML
**Duration**: 2 weeks | **Goal**: Teams, Stripe billing, GDPR compliance, session analytics  
**Version**: v1.2.0 | **Agent**: Sprint Prioritizer | **Status**: ✅ COMPLETED 2026-03-16

---

## Sprint Goal

> ObserveML becomes a team product. Multi-user orgs with RBAC, Stripe billing with usage metering, and GDPR data deletion complete the SaaS foundation. Session grouping and prompt hash analytics add production value for data-conscious teams.

---

## Tickets

| ID | Title | Points | Owner |
|----|-------|--------|-------|
| OB-41 | Multi-user teams: invite members, RBAC (owner / analyst / viewer) | 5 | Backend Architect |
| OB-42 | Stripe billing: free tier (10k events/month) + Pro (unlimited) | 5 | Backend Architect |
| OB-43 | Usage metering dashboard: monthly event count + cost trend bar chart | 3 | Frontend Developer |
| OB-44 | Prompt hash analytics: top-N most-repeated hashes (dedup frequency) | 3 | Backend Architect |
| OB-45 | Session grouping: tag events with `session_id`; drill into per-session cost | 5 | Backend Architect |
| OB-46 | SDK: Java/Kotlin port v0.1 (JVM ingest for Android + server-side Java) | 5 | Senior Developer |
| OB-47 | Organization API key rotation: invalidate old key, issue new, audit log entry | 2 | Security Engineer |
| OB-48 | GDPR data deletion: `DELETE /v1/org/data` removes all ClickHouse + PG rows | 3 | Security Engineer |
| OB-49 | E2E: billing lifecycle + usage metering + session drill-down cost summary | 3 | QA Engineer |
| OB-50 | v1.2.0 CHANGELOG + release notes | 1 | Technical Writer |

**Total**: 35 points

---

## Definition of Done

- [x] Team invite: invited user can log in and see only their org's data (not other orgs)
- [x] Stripe free tier enforced: ingest returns 402 after 10,001st event in billing period
- [x] Usage metering chart shows correct daily event counts and cumulative monthly cost
- [x] Prompt hash top-N: query returns hashes sorted by frequency; hash is not reversible (SHA-256)
- [x] Session grouping: `GET /v1/metrics/session/{session_id}` returns cost, call count, avg latency
- [x] Java SDK `track()` is thread-safe; tested with 10-thread concurrent ingest
- [x] API key rotation: old key returns 401 within 1s of rotation; audit log row created
- [x] GDPR deletion: `DELETE /v1/org/data` removes all rows; returns 204; cannot be undone
- [x] GDPR deletion requires re-authentication (two-step deletion token, not just session token)

---

## Vedantic Launch Gate

> *Brahman — GDPR deletion is irreversible. The whole-system view: deleting an org's data must not cascade to billing records needed for financial compliance. Billing history must survive the data deletion.*

- [x] GDPR deletion preserves Stripe invoice records (deletes only metric and alert data) — MUST PASS
- [x] Prompt hash top-N: confirmed SHA-256 output with no prompt text in API response — MUST PASS
- [x] Java SDK Observer Principle: no prompt/response parameter exists in the API — MUST PASS
- [x] 333-Line Law: Java SDK TrackerClient.java < 333 lines (244 lines)

---

## Śhāstrārtha Sprint Review Checkpoint

**Viṣaya**: Is the GDPR data deletion endpoint safe from accidental or malicious invocation?  
**Saṃśaya**: A `DELETE /v1/org/data` endpoint with only an API key for authentication could be triggered by a stolen key. A single call destroys months of production observability data.  
**Siddhānta**: The deletion endpoint must require: (1) a short-lived deletion token issued via a separate `POST /v1/org/request-data-deletion` step with password re-authentication, (2) a cooling-off period of 24h before deletion executes, (3) an email confirmation to the org owner. The deletion token must expire in 25h and be single-use.
