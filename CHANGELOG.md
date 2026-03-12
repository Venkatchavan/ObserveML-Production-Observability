# Changelog

All notable changes to ObserveML are documented here.
Format: [Semantic Versioning](https://semver.org). Dates are UTC.

---

## [1.1.0] — 2026-03-12 (Sprint 04 — Sampling, SSE, Analytics)

### Added

- **OB-31 — Head-based sampling** — Python and JS SDKs accept `sample_rate` (0.0–1.0);
  events are dropped client-side before any network call, preserving the Observer Principle.
- **OB-32 — Server-Sent Events** — `GET /v1/stream/events` streams live ingested events
  per-org; Origin header validated (no wildcard CORS); last 50 events replayed on connect;
  25-second keepalive comment prevents proxy timeouts.
- **OB-33 — Latency percentiles** — `GET /v1/metrics` now returns `p50_latency_ms`,
  `p95_latency_ms`, and `p99_latency_ms` via ClickHouse `quantile()` functions.
- **OB-34 — Token budget alerting** — new `monthly_projected_cost_usd` alert metric;
  `GET /v1/metrics/token-budget` returns daily avg and projected monthly cost.
- **OB-35 — Model routing recommendations** — `GET /v1/compare/routing` returns per-model
  performance compared against caller-supplied `max_latency_ms` and `max_cost_usd`
  constraints; every row includes a `caveat` field (Vedantic Launch Gate satisfied).
- **OB-36 — OpenTelemetry trace_id propagation** — SDK `track()` accepts optional
  `trace_id`; stored in ClickHouse `metric_events.trace_id`; exposed in CSV export.
- **OB-37 — Live Feed dashboard panel** — new "Live Feed" tab; SSE auto-reconnect with
  5-second back-off; shows last 50 events with trace ID, latency, cost, and error flag.
- **OB-38 — CSV export** — `GET /v1/metrics/export` streams a CSV of all event columns
  including `trace_id` and `p99_latency_ms` for the last N days (default 30).

### Changed

- Dashboard: "Call Site Breakdown" table now includes a **p99 latency** column.
- Dashboard: header bar has an **Export CSV** button.
- Dashboard: **Token Budget** status banner shows projected monthly cost.
- Python SDK version bumped to `1.1.0`; JS SDK `sampleRate` constructor param added.

### Migration

Run `migrations/clickhouse/002_trace_id.sql` on any existing ClickHouse instance
(`ALTER TABLE metric_events ADD COLUMN IF NOT EXISTS trace_id String DEFAULT ''`).
The `ensure_table()` startup call performs this migration automatically.

---

## [1.0.3] — 2026-03-12 (Test-API full green)

### Fixed

- **CI — Test FastAPI + ClickHouse: async fixture errors (8 ERRORs)** — rewrote
  `api/tests/test_integration.py` to use `pytest-asyncio` `asyncio_mode = "auto"`;
  removed deprecated module-scoped `event_loop` fixture override; removed all explicit
  `@pytest.mark.asyncio` decorators (mode=auto handles them)
- **CI — Test FastAPI + ClickHouse: ConnectError (1 FAIL)** — replaced
  `httpx.AsyncClient(base_url="http://localhost:8000")` with
  `httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")`;
  all 9 tests now run in-process via ASGI transport — no live TCP server needed
- **CI — Test FastAPI + ClickHouse: Coverage 0%** — was 0% only because all tests
  errored before executing; with ASGI transport they exercise all API routes
- **CI — Test Python SDK (matrix): BackendUnavailable** — `sdk/python/pyproject.toml`
  used `setuptools.backends.legacy:build` which does not exist as a PEP 517 entry-point;
  changed to the standard `setuptools.build_meta` backend (works on Python 3.9–3.12)
- **CI — Test FastAPI + ClickHouse: `pytest: command not found`** — `pip install`
  step in `test-api` job now installs `pytest pytest-cov pytest-asyncio` alongside
  `api/requirements.txt`
- **CI — Lint Python: ruff F841** — removed unused `rule_id =` assignment in
  `api/tests/test_integration.py:149`
- **CI — Lint Python: ruff format (18 files)** — ran `ruff format api/ sdk/python/`
  to bring all 18 Python source files into Black-compatible format; both
  `ruff check` and `ruff format --check` now exit 0

### Changed

- `pyproject.toml` (root): added `[tool.pytest.ini_options]` with
  `asyncio_mode = "auto"` and `asyncio_default_fixture_loop_scope = "session"`

---

## [1.0.2] — 2026-03-12 (Security + Lint full-pass)

### Fixed

- **CI — Lint Python: ruff F401** — removed all unused imports across Python test files:
  - `sdk/python/tests/test_tracker.py`: removed `import queue as stdlib_queue`, `configure`
  - `sdk/python/tests/test_sdk_v1.py`: removed `import queue as stdlib_queue`, `import threading`,
    `configure`, `track` (all only used via `observeml.*` module API in those tests)
  - `api/tests/test_integration.py`: removed `from datetime import datetime, timezone` (unused)
- **CI — Lint Python: ruff format** — normalized inline comment spacing in
  `api/app/models/events.py` (`is_regression: bool  # …` — Black-style 2-space rule)
- **CI — Security Scan Python: starlette CVEs** — added explicit `starlette>=0.49.1` to
  `api/requirements.txt` and relaxed `fastapi` to `>=0.115.5` so pip resolves a
  starlette version that patches CVE-2025-54121 (fix: 0.47.2) and CVE-2025-62727 (fix: 0.49.1)

### Added

- **LICENSE** — MIT License, Copyright © 2026 Venkat Chavan
- **pyproject.toml** — updated SDK author from "The Agency" to "Venkat Chavan"

---

## [1.0.1] — 2026-03-11 (CI / packaging fix)

### Fixed

- **`observeml._default` proxy** — `sdk/python/observeml/__init__.py` now replaces itself
  with a `types.ModuleType` subclass so `observeml._default` is readable and writable
  at the package level; fixes 3 `test_sdk_v1.py` failures (`AttributeError`)
- **JS SDK timer leak** — call `.unref()` on the `setInterval` timer in `tracker.ts`
  so jest no longer force-exits with a stale-timer warning
- **CI — `npm ci` fails** — removed `package-lock.json` from `.gitignore`; committed
  the lockfile so `npm ci` can run in CI
- **CI — `npm run lint` fails** — added `eslint`, `@typescript-eslint/parser`, and
  `@typescript-eslint/eslint-plugin` (^8) dev-deps; added `"type-check": "tsc --noEmit"`
  script; created `.eslintrc.json`
- **CI — ruff E401** — split `import hashlib, uuid` into two lines in
  `api/tests/test_integration.py`
- **CI — `safety` v3 CLI break** — pinned `safety<3` in workflow so legacy
  `safety check -r` syntax works
- **CI — wrong pip extras name** — renamed `[dev]` → `[test]` in
  `sdk/python/pyproject.toml`; CI calls `pip install -e ".[test]"`
- **Security** — upgraded `@typescript-eslint` from ^6 → ^8 eliminating 6 high-severity
  ReDoS vulnerabilities in `minimatch` (CVEs GHSA-3ppc, GHSA-7r86, GHSA-23c5)
- Added root `pyproject.toml` with `black` + `ruff` config (`line-length = 100`)

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
