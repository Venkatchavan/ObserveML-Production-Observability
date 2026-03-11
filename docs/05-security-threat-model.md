# Security Threat Model â€” ObserveML
**v1.0.3 | 2026-03-12 | Security Engineer**

---

## 1. Attack Surface

| Surface | Entry Point | Trust Level |
|---------|------------|-------------|
| Ingest API (`/v1/ingest`) | Internet | Untrusted; API key required |
| Dashboard API (`/v1/metrics`) | Internet | Untrusted; API key required |
| SDK (npm / PyPI package) | Developer's codebase | Trusted after install |
| ClickHouse | Internal only | No external access |
| PostgreSQL | Internal only | No external access |

---

## 2. OWASP Top-10 Mapping

| # | Risk | ObserveML Control |
|---|------|-------------------|
| A01 | Broken Access Control | API key scoped per org; no cross-org data path |
| A02 | Cryptographic Failures | API keys stored as SHA-256 hashes; HTTPS everywhere |
| A03 | Injection | No user-content in SQL (parameterized queries); ClickHouse queries use typed parameters |
| A04 | Insecure Design | SDK fire-and-forget: no response data returned that could leak org info |
| A05 | Security Misconfiguration | No debug endpoints; no LLM prompt content in logs |
| A06 | Vulnerable Components | Dependabot; `safety` + `npm audit` in CI |
| A07 | Auth Failures | API key validated on every request (no session tokens) |
| A08 | Data Integrity | SDK events include `event_id` idempotency key; dedup in ingest layer |
| A09 | Logging Failures | API access logged (org + action); no prompt/response content in logs |
| A10 | SSRF | No user-controlled URL fetching in SDK or API |

---

## 3. Threat Scenarios

### T-01: API Key Brute Force
**Threat**: Attacker enumerates API keys via ingest endpoint.  
**Control**: Rate limiting (100 req/min per IP); keys are 256-bit random; brute force is computationally infeasible.  
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
**Control**: Per-org ingest rate limit (10K events/min); oversized payloads rejected (max 100 events per batch, max 5KB per event).  
**Residual Risk**: LOW

---

## 4. Privacy Controls

- Prompt/response content: NEVER transmitted, stored, or logged by the SDK
- Call-site identifier: hashed source location (not function names or code)
- API keys: stored as SHA-256 hash; plaintext only shown once at creation

---

## 5. Security Review Schedule

- Pre-launch: SDK security review (confirm no content capture)
- On each SDK release: `pip-audit` + `npm audit` + manual code review
- Quarterly: dependency CVE review

