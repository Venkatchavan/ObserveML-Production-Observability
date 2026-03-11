# Changelog

All notable changes to ObserveML are documented here.
Format: [Semantic Versioning](https://semver.org). Dates are UTC.

---

## [1.0.0] — 2026-03-11 (Sprint 03)

**Sprint goal:** SDKs published, multi-model comparison dashboard live, production deployed,
SDK documentation complete.

### Added

- **Multi-model comparison dashboard** (OB-21): new Compare tab with side-by-side latency,
  error-rate, and cost bar charts (`ModelComparison.tsx`)
- **Regression detection** (OB-22): Welch's z-test using `math.erfc` — no scipy dependency;
  `regression_detector.py` + `GET /v1/compare/regression` endpoint
- **Cost tracking per model** (OB-23): `GET /v1/compare/cost` returning daily cost breakdown;
  `CostRow` model added to `events.py`
- **Python SDK v1.0.0** (OB-24): promoted to Production/Stable; `flush_interval_s` configurable;
  full suite in `test_sdk_v1.py`
- **TypeScript SDK v1.0.0** (OB-25): promoted to v1.0.0; `flushIntervalMs` configurable;
  `prompt_hash` determinism tests in `sdk_v1.test.ts`
- **Production deployment** (OB-26): `Caddyfile` with automatic TLS, HSTS, CSP, and X-Frame-Options
  for `api.observeml.io` + `app.observeml.io`
- **Documentation site** (OB-27): MkDocs Material theme with four pages — Home, Quickstart,
  Privacy & Observer Principle, API Reference
- **E2E regression tests** (OB-29): four new `test_integration.py` test functions covering
  regression endpoint shape, stability assertion, model comparison, and cost endpoint
- `GET /v1/compare/models` endpoint returning per-model aggregated stats

### Changed

- `api/app/db/clickhouse.py` — added `query_model_comparison`, `query_regression_windows`,
  `query_cost_breakdown`; parameterized time windows use `subtractHours()/subtractDays()`
  to avoid ClickHouse INTERVAL binding issues
- `api/app/main.py` — registered `compare` router (4 routers total)
- `dashboard/src/App.tsx` — three-tab layout: Overview, Alerts, Compare
- `dashboard/src/api/client.ts` — added `ModelComparisonRow`, `RegressionFinding`, `CostRow`
  types and corresponding fetchers

### Notes

- OB-28 (supply chain review: lock files, OIDC pipeline audit) is a **HUMAN GATE** —
  no automated code. Requires manual review before distributing production packages.
- Regression detection minimum sample: 5 events per window. Below this, findings are skipped.
- Regression p-value threshold: 0.05 (two-tailed).

---

## [0.1.1] — 2026-02-25 (Sprint 02)

### Added

- **Anomaly detection** (OB-11): sliding-window z-score detector runs as a background FastAPI task
- **Alert dispatch** (OB-12): SSRF-safe webhook delivery with allowlist validation
- **Alert CRUD** (OB-13/14): `POST/GET/DELETE /v1/alerts`, `GET /v1/alerts/feed`
- **Dashboard v0.2**: `AlertFeed.tsx`, `ThresholdConfig.tsx`, `ModelDrillDown.tsx`,
  two-tab layout (Overview + Alerts)
- **PyPI/npm OIDC publish pipelines** (OB-17): `.github/workflows/publish-python.yml`
  + `publish-npm.yml`
- **Fly.io deploy config** (OB-18): `fly.toml` for production
- **Integration tests** (OB-19): `test_integration.py` — events → anomaly → alert_fired flow
- **SDK configurable flush interval** (OB-20): `flush_interval_s` (Python) / `flushIntervalMs` (TS)

---

## [0.1.0] — 2026-02-18 (Sprint 01)

### Added

- **FastAPI application** with ClickHouse + PostgreSQL backend
- **Metric events ingest** (`POST /v1/ingest`) — validated, batched, async write to ClickHouse
- **Metrics query** (`GET /v1/metrics`, `GET /v1/metrics/trend`) — aggregations over time window
- **Python SDK v0.1.0**: background-thread queue, `track()`, `prompt_hash()`, `flush()`
- **TypeScript SDK v0.1.0**: `setInterval` flush, `track()`, `promptHash()`
- **Observer Principle** enforcement: no prompt/response fields in API signature or payloads
- **Docker Compose** dev environment (FastAPI + ClickHouse + PostgreSQL)
- **PostgreSQL migrations** for `organizations`, `api_keys`, `alert_rules`, `alert_fired`
- **ClickHouse schema**: `metric_events` table, 90-day TTL, partitioned by `org_id + date`
- **React + Vite dashboard** with overview charts (Recharts)
- **GitHub issue templates**, dependabot config, CI workflow skeleton
