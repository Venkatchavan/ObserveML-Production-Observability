# API Reference

## Authentication

All API endpoints require an `X-API-Key` header.

```http
X-API-Key: oml_your_key_here
```

Obtain a key from your account settings.

---

## Ingest

### `POST /v1/ingest`

Submit one or more metric events.

**Request Body**

```json
{
  "events": [
    {
      "model": "gpt-4o",
      "latency_ms": 312,
      "input_tokens": 180,
      "output_tokens": 95,
      "cost_usd": 0.00413,
      "error": false,
      "call_site": "summarizer"
    }
  ]
}
```

**Response `200`**

```json
{"accepted": 1}
```

---

## Metrics

### `GET /v1/metrics`

Aggregated metrics for the authenticated organisation.

**Query Parameters**

| Param | Default | Description |
|-------|---------|-------------|
| `model` | *(all)* | Filter by model name |
| `hours` | `24` | Look-back window in hours |

**Response `200`**

```json
[
  {
    "call_site": "summarizer",
    "model": "gpt-4o",
    "avg_latency_ms": 307.4,
    "p50_latency_ms": 280.0,
    "p95_latency_ms": 610.0,
    "p99_latency_ms": 812.0,
    "total_calls": 1420,
    "total_cost_usd": 5.87,
    "error_rate": 0.007
  }
]
```

---

### `GET /v1/metrics/token-budget`

Returns the current calendar-month cost projection for the authenticated organisation.

**Response `200`**

```json
{
  "daily_avg_cost_usd": 0.84,
  "projected_monthly_cost_usd": 26.04,
  "days_in_month": 31
}
```

---

### `GET /v1/metrics/export`

Streaming CSV download of raw metric events for the last N days.

**Query Parameters**

| Param | Default | Description |
|-------|---------|-------------|
| `days` | `30` | Number of past days to include |

**Response `200`** — `text/csv` stream with header row:

```
event_id,call_site,model,latency_ms,input_tokens,output_tokens,cost_usd,error,error_code,trace_id,ts
3fa85...,summarizer,gpt-4o,312,180,95,0.00413,false,,abc123,2026-03-11 14:32:00.000
```

---

### `GET /v1/metrics/trend`

Hourly trend for a single model.

**Query Parameters**

| Param | Required | Description |
|-------|----------|-------------|
| `model` | Yes | Model name to trend |
| `hours` | No (default: 24) | Window in hours |

**Response `200`** — array of `TrendPoint`:

```json
[
  {"hour": "2026-03-11T14:00:00", "avg_latency_ms": 298.1, "call_count": 87}
]
```

---

## Comparison

---

### `GET /v1/compare/routing`

Returns model routing recommendations filtered by latency and cost constraints.
Every row includes a `caveat` field — results reflect observed performance only.

**Query Parameters**

| Param | Default | Description |
|-------|---------|-------------|
| `max_latency_ms` | `5000` | Maximum acceptable average latency |
| `max_cost_usd` | `1.0` | Maximum acceptable average cost per call |

**Response `200`** — meets-constraints models first, then sorted by cost:

```json
[
  {
    "model": "gpt-3.5-turbo",
    "avg_latency_ms": 180.4,
    "avg_cost_usd": 0.00031,
    "error_rate": 0.002,
    "total_calls": 8400,
    "meets_constraints": true,
    "caveat": "Based on observed performance only; evaluate for your specific workload"
  }
]
```

---

### `GET /v1/compare/models`

Side-by-side stats for all models used in the last 7 days.

**Response `200`**

```json
[
  {
    "model": "gpt-4o",
    "avg_latency_ms": 307.4,
    "error_rate": 0.007,
    "total_cost_usd": 5.87,
    "call_count": 1420
  }
]
```

---

### `GET /v1/compare/regression`

Regression findings using Welch's z-test comparing two time windows.

**Query Parameters**

| Param | Default | Description |
|-------|---------|-------------|
| `window_hours` | `24` | Length of each comparison window (hours) |

**Response `200`** — sorted regressions first, then stable:

```json
[
  {
    "call_site": "summarizer",
    "metric": "latency_ms",
    "baseline_mean": 298.0,
    "current_mean": 441.0,
    "z_score": 4.12,
    "p_value": 0.0001,
    "is_regression": true
  }
]
```

---

### `GET /v1/compare/cost`

Daily cost per model for the last N days.

**Query Parameters**

| Param | Default | Description |
|-------|---------|-------------|
| `days` | `7` | Number of days to include |

**Response `200`**

```json
[
  {"model": "gpt-4o", "day": "2026-03-11", "total_cost_usd": 5.87}
]
```

---

## Alerts

### `POST /v1/alerts`

Create an alert rule.

```json
{
  "metric": "avg_latency_ms",
  "operator": "gt",
  "threshold": 500.0,
  "model_filter": "gpt-4o",
  "webhook_url": "https://hooks.example.com/observeml"
}
```

Allowed `metric` values: `avg_latency_ms`, `error_rate`, `total_cost_usd`, `monthly_projected_cost_usd`.
Allowed `operator` values: `gt`, `lt`.

**Response `201`** — the created rule with `id`.

---

### `GET /v1/alerts`

List all alert rules for the organisation.

---

### `DELETE /v1/alerts/{alert_id}`

Delete an alert rule.

---

### `GET /v1/alerts/feed`

Recent alert firings, newest first.

**Response `200`**

```json
[
  {
    "id": "3fa85...",
    "rule_id": "1b9d...",
    "metric": "avg_latency_ms",
    "threshold": 500.0,
    "observed_value": 612.4,
    "model": "gpt-4o",
    "fired_at": "2026-03-11T14:32:00Z"
  }
]
```

---

## Streaming

### `GET /v1/stream/events`

Server-Sent Events stream of metric events for the authenticated organisation.

**Headers**

| Header | Required | Description |
|--------|----------|-------------|
| `x-api-key` | Yes | Your API key |
| `Origin` | No | If present, must exactly match the configured dashboard origin |

**Response `200`** — `text/event-stream`

The server replays the last 50 events on connect, then streams live events as they are ingested.
A `: keepalive` comment is sent every 25 seconds to prevent proxy timeouts.

```
data: {"event_id": "3fa85...", "model": "gpt-4o", "latency_ms": 312, ...}

data: {"event_id": "9bc12...", "model": "claude-3-5-sonnet", "latency_ms": 280, ...}

: keepalive
```

Security: `Access-Control-Allow-Origin` is **never** set to `*`.
Only the exact origin configured in `settings.dashboard_origin` is reflected.

---

## Health

### `GET /health`

Liveness check — no authentication required.

**Response `200`**

```json
{"status": "ok"}
```

---

## Python SDK

### Installation

```bash
pip install observeml==1.1.0
```

### `configure(api_key, base_url, flush_interval_s, sample_rate)`

| Param | Default | Description |
|-------|---------|-------------|
| `api_key` | *(required)* | Your API key |
| `base_url` | `"https://api.observeml.io"` | API base URL |
| `flush_interval_s` | `5` | How often the background thread flushes (seconds) |
| `sample_rate` | `1.0` | Fraction of events to send (0.0–1.0); drop happens before queuing |

### `track(**kwargs)`

Enqueues one metric event. All fields match the ingest schema above.
Does not block. Raises `ValueError` for unknown fields in strict mode.

| Extra field | Type | Description |
|-------------|------|-------------|
| `trace_id` | str | Optional OpenTelemetry trace ID for cross-system correlation |

### `prompt_hash(prompt_text, response_text) -> str`

Returns a stable SHA-256 hex digest without storing the original text.

### `ObserveML` class

```python
from observeml import ObserveML
tracker = ObserveML(api_key="oml_k", flush_interval_s=10, sample_rate=0.1)
tracker.track(model="gpt-4o", latency_ms=200, trace_id="abc123")
tracker.flush()  # Force flush before process exit
```

---

## TypeScript / JavaScript SDK

### Installation

```bash
npm install observeml@1.1.0
```

### `configure(options)`

| Option | Default | Description |
|--------|---------|-------------|
| `apiKey` | *(required)* | Your API key |
| `baseUrl` | `"https://api.observeml.io"` | API base URL |
| `flushIntervalMs` | `5000` | Flush interval in milliseconds |
| `sampleRate` | `1.0` | Fraction of events to send (0.0–1.0) |

### `track(event)`

Enqueues one metric event. Non-blocking, fire-and-forget.
Accepts optional `traceId?: string` field for OTel correlation.

### `promptHash(prompt, response) -> string`

Client-side SHA-256 digest of prompt + response (using Web Crypto API).

### `ObserveML` class

```typescript
import { ObserveML } from "observeml";
const tracker = new ObserveML({ apiKey: "oml_k", flushIntervalMs: 10000 });
tracker.track({ model: "gpt-4o", latencyMs: 200 });
await tracker.flush();
```
