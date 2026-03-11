# Sprint 03 — ObserveML
**Duration**: 2 weeks | **Goal**: Production launch + multi-model comparison + SDK v1.0 release  
**Version**: v1.0.0 | **Agent**: Sprint Prioritizer

---

## Sprint Goal

> ObserveML v1.0 SDKs published. Multi-model comparison dashboard live. Production deployed. SDK documentation complete.

---

## Tickets

| ID | Title | Points | Owner |
|----|-------|--------|-------|
| OB-21 | Multi-model comparison: side-by-side metric charts | 5 | Frontend Developer |
| OB-22 | Regression detection: p-value comparison for metric distributions | 5 | AI Engineer |
| OB-23 | Cost tracking: token usage → cost estimation per model | 3 | Backend Architect |
| OB-24 | SDK v1.0 Python: semver tag + full test suite | 3 | Senior Developer |
| OB-25 | SDK v1.0 JS/TS: semver tag + full test suite | 3 | Senior Developer |
| OB-26 | Production deploy + custom domain | 2 | DevOps Automator |
| OB-27 | SDK documentation site (MkDocs or Docusaurus) | 5 | Technical Writer |
| OB-28 | Security review: SDK supply chain (OIDC publish audit) | 0 | `⚠️ REQUIRES HUMAN REVIEW` |
| OB-29 | E2E: multi-model comparison + regression detection | 3 | QA Engineer |
| OB-30 | v1.0.0 version tag + CHANGELOG | 1 | Technical Writer |

**Total**: 30 points (+ 1 human gate)

---

## Definition of Done

- [ ] SDK v1.0 published to PyPI and npm with full documentation
- [ ] Multi-model comparison: 2+ models compared in dashboard
- [ ] Regression detection fires correctly (tested with synthetic regression data)
- [ ] SDK supply chain review completed (`⚠️ REQUIRES HUMAN REVIEW`)
- [ ] Production deployed with custom domain
- [ ] v1.0.0 tagged; SDK docs live

---

## Vedantic Launch Gate

> *Neti Neti — ObserveML does NOT capture prompt content, model weights, or user identity. This is the constitutional limit. It must be tested before v1.0 ships.*

- [ ] Content-leak test: passes on final v1.0 SDK build
- [ ] SDK overhead p99 < 1ms: passes on final v1.0 SDK build
- [ ] Org isolation: tested and passing
- [ ] 333-Line Law: all modules checked

---

## Śhāstrārtha Sprint Review Checkpoint

**Viṣaya**: Is the SDK truly privacy-safe for production LLM applications?  
**Saṃśaya**: Was the content-leak test run on the actual npm/PyPI package (not just source)?  
**Siddhānta**: Launch only if content-leak test passes on the published package, not just in source.
