# Security Threat Model â€” ObserveML
**v2.1.0 | 2026-03-16 | Security Engineer**

---

## 1. Attack Surface

| Surface | Entry Point | Trust Level |
|---------|------------|-------------|
| All API endpoints | Internet | IP rate-limited (200 req/min/IP); any IP exceeding limit gets 429 |
| Ingest API (`/v1/ingest`) | Internet | API key required; per-org 100 req/min; 402 after free-tier breach |
| Dashboard API (`/v1/metrics`) | Internet | API key required; per-org 100 req/min |
| Teams API (`/v1/teams`) | Internet | API key required; role enforced server-side |
| Billing API (`/v1/billing`) | Internet | API key required |
| Org Admin API (`/v1/org`) | Internet | API key + deletion token for GDPR |
| Intelligence API (`/v1/intelligence`) | Internet | API key required; fail-open (never 500) |
| CORS | Browser requests | Explicit origin allow-list (`CORS_ORIGINS` env var); never `*`; preflight max-age 600 s |
| Host header | HTTP | `TrustedHostMiddleware` active when `TRUSTED_HOSTS` env var is set |
| SDK (npm / PyPI / Maven / RubyGems) | Developer's codebase | Trusted after install |
| ClickHouse | Internal only | No external access |
| PostgreSQL | Internal only | No external access |

---

## 2. OWASP Top-10 Mapping

| # | Risk | ObserveML Control |
|---|------|-------------------|
| A01 | Broken Access Control | API key scoped per org; no cross-org data path; team roles enforced server-side; CORS origin allow-list prevents unauthorized browser origin access |
| A02 | Cryptographic Failures | API keys stored as SHA-256 hashes; deletion tokens stored as SHA-256 hashes; HTTPS everywhere |
| A03 | Injection | No user-content in SQL (parameterized queries); ClickHouse queries use typed parameters |
| A04 | Insecure Design | SDK fire-and-forget: no response data returned; two-step GDPR deletion with 24h cooling-off |
| A05 | Security Misconfiguration | No debug endpoints; no LLM prompt content in logs; CORS never wildcard (`allow_credentials=False`); `TrustedHostMiddleware` available for host-header validation |
| A06 | Vulnerable Components | Dependabot; `safety` + `npm audit` in CI |
| A07 | Auth Failures | API key validated on every request (no session tokens); old key invalidated within 1 request of rotation; IP rate limit (200 req/min) blocks brute-force enumeration |
| A08 | Data Integrity | SDK events include `event_id` idempotency key; dedup in ingest layer; deletion tokens are single-use |
| A09 | Logging Failures | API access logged (org + action); no prompt/response content in logs; audit_log for key rotation and GDPR |
| A10 | SSRF | No user-controlled URL fetching in SDK or API. Sparkline images use QuickChart.io with metric values only — no org identifiers or private data in URL |

---

## 3. Threat Scenarios

### T-01: API Key Brute Force
**Threat**: Attacker enumerates API keys by sending many requests with different key values to any endpoint.  
**Control**: (1) IP-based rate limiting middleware: 200 req/min per IP, returns `429` with `Retry-After: 60` header. (2) Per-org rate limit: 100 req/min after successful auth. (3) Keys are 256-bit random (SHA-256 hash stored) — computationally infeasible to guess. (4) `last_used_at` tracked; anomalous key-cycling is detectable.  
**Residual Risk**: LOW

### T-02: Cross-Org Metric Leakage
**Threat**: Org A's API key used to read Org B's metrics.  
**Control**: API key â†’ org_id lookup is server-side; all queries scoped by org_id derived from key, not from request body.  
**Residual Risk**: LOW

### T-03: SDK Supply Chain Attack
**Threat**: ObserveML SDK package compromised to exfiltrate LLM prompts/responses.  
**Control**: SDK only captures metadata (never prompt content); PyPI + npm packages published via GitHub Actions OIDC (no manual publish).  
**Residual Risk**: MEDIUM â€” `âš ï¸ REQUIRES HUMAN REVIEW` before each SDK release

### T-04: Metric Flooding (DoS)
**Threat**: Attacker floods ingest endpoint with high-volume events to inflate ClickHouse storage.  
**Control**: Per-org ingest rate limit (10K events/min); oversized payloads rejected (max 100 events per batch, max 5KB per event); free-tier billing hard cap (402 after 10k events/month).  
**Residual Risk**: LOW

### T-05: GDPR Deletion via Stolen API Key
**Threat**: Attacker with stolen API key triggers `POST /v1/org/request-data-deletion` to destroy org data.  
**Control**: Two-step deletion: (1) request issues a single-use token with 24h cooling-off period; (2) `DELETE /v1/org/data?token=` requires that token. Deleting immediately after issuance returns 409. Org has 24h window to detect and rotate key.  
**Residual Risk**: LOW

### T-06: Team Role Escalation
**Threat**: `viewer` role member escalates to `owner` by crafting invite request.  
**Control**: `role` field is validated server-side via CHECK constraint (`owner`, `analyst`, `viewer`); API key determines org context — cannot invite to a different org.  
**Residual Risk**: LOW

### T-07: Root Cause Narration Hallucination Risk
**Threat**: The `/v1/intelligence/root-cause` endpoint produces a plausible but false narrative, leading engineers to the wrong remediation action.  
**Control**: (1) Narrative is purely heuristic — only references observed metric values from ClickHouse, no LLM. (2) Every response includes `confidence` (HIGH/MEDIUM/LOW) and mandatory `caveat`. (3) `show_data_url` links to raw time-series data so engineers can verify themselves. (4) LOW confidence is returned when sample size < 20 or delta < 20%.  
**Residual Risk**: MEDIUM — engineers must treat narration as a starting hypothesis, not ground truth. The `caveat` field enforces this expectation in the API contract.

### T-08: Cross-Origin Request Forgery (CORS bypass)
**Threat**: A malicious website in the user's browser silently calls ObserveML API endpoints (e.g. `POST /v1/ingest`) on behalf of a logged-in user, exfiltrating org metrics or poisoning data.  
**Control**: (1) `CORSMiddleware` in `main.py` with an explicit `allow_origins` list (env var `CORS_ORIGINS`). Browser pre-flight requests for non-simple methods will be rejected for unlisted origins. (2) `allow_credentials=False` — no cookies are used, preventing CSRF via cookie session. (3) `max_age=600` — reduces preflight round-trips without weakening the policy. (4) SSE endpoint additionally validates `Origin` header at the application layer as a defence-in-depth check.  
**Production action required**: Set `CORS_ORIGINS` to your exact frontend domain (e.g. `CORS_ORIGINS=https://app.observeml.io`).  
**Residual Risk**: LOW when `CORS_ORIGINS` is correctly configured in production.

### T-09: Host Header Injection
**Threat**: Attacker sends a request with a spoofed `Host` header (e.g. `Host: evil.com`) to exploit password-reset email generation or cache-poisoning vulnerabilities that use the Host header to construct URLs.  
**Control**: `TrustedHostMiddleware` is available and activated when the `TRUSTED_HOSTS` env var is set to a comma-separated list of allowed hostnames. Returns `400 Bad Request` for unrecognised `Host` headers.  
**Production action required**: Set `TRUSTED_HOSTS=api.observeml.io` (your actual API hostname) in production.  
**Residual Risk**: LOW when `TRUSTED_HOSTS` is set; MEDIUM if left empty (middleware inactive).

---

## 4. Privacy Controls

- Prompt/response content: NEVER transmitted, stored, or logged by the SDK
- Call-site identifier: hashed source location (not function names or code)
- API keys: stored as SHA-256 hash; plaintext only shown once at creation

---

## 5. Security Review Schedule

- Pre-launch: SDK security review (confirm no content capture)
- Pre-launch: Verify `CORS_ORIGINS` and `TRUSTED_HOSTS` are set to production values in deployment secrets
- On each SDK release: `pip-audit` + `npm audit` + manual code review
- Quarterly: dependency CVE review; re-audit `CORS_ORIGINS` allow-list for stale entries

