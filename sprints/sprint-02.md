# Sprint 02 — ObserveML
**Duration**: 2 weeks | **Goal**: SDK published to PyPI + npm; dashboard shows alerts  
**Version**: v0.2.0 | **Agent**: Sprint Prioritizer

---

## Sprint Goal

> ObserveML SDKs are published to PyPI and npm. The dashboard shows alert notifications when a metric anomaly is detected.

---

## Tickets

| ID | Title | Points | Owner |
|----|-------|--------|-------|
| OB-11 | Anomaly detection: sliding window threshold comparison | 5 | AI Engineer |
| OB-12 | Alert model: per-metric thresholds + notification dispatch | 3 | Backend Architect |
| OB-13 | Dashboard: alert feed + threshold configuration UI | 5 | Frontend Developer |
| OB-14 | PyPI publish pipeline: GitHub Actions OIDC (no manual publish) | 3 | DevOps Automator |
| OB-15 | npm publish pipeline: GitHub Actions OIDC | 3 | DevOps Automator |
| OB-16 | Fly.io deployment: API + dashboard | 3 | DevOps Automator |
| OB-17 | SDK streaming support: batch send every 5s (configurable) | 3 | Senior Developer |
| OB-18 | Dashboard drill-down: per-model metric timeline | 3 | Frontend Developer |
| OB-19 | Integration test: events + anomaly detection + alert fired | 3 | QA Engineer |
| OB-20 | SDK documentation: README + docstrings for public API | 2 | Technical Writer |

**Total**: 33 points

---

## Definition of Done

- [ ] Python SDK published to PyPI (GitHub Actions OIDC, no manual publish)
- [ ] JS SDK published to npm
- [ ] Anomaly alert fires when metric exceeds threshold (tested)
- [ ] Dashboard shows alert feed
- [ ] Deployed to Fly.io staging
- [ ] SDK README covers `track()` usage with privacy note (no prompt content)

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| PyPI publish rate limits | LOW | MEDIUM | OIDC publish is reliable; test in staging PyPI first |
| Anomaly detection false positive rate | MEDIUM | MEDIUM | Ship as configurable threshold; users tune it |
| Fly.io ClickHouse memory usage | MEDIUM | MEDIUM | Profile before deploy; may need larger instance |

---

## Śhāstrārtha Sprint Review Checkpoint

**Viṣaya**: Did we ship SDKs that are publicly available and privacy-safe?  
**Saṃśaya**: Were the publish pipelines tested end-to-end, or just configured?  
**Siddhānta**: Ship only if both SDKs install + track successfully from external package.
