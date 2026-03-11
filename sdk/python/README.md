# ObserveML Python SDK

[![PyPI version](https://img.shields.io/pypi/v/observeml)](https://pypi.org/project/observeml/)

**Drop-in LLM observability. Captures metadata only — never prompt or response content.**

> **Observer Principle — non-negotiable:** `track()` has NO `prompt` or `response` parameter.
> It captures: model, latency, tokens, cost, error flags. Nothing else. Ever.
> Content-leak tests run in CI on every PR and block merges if violated.

## Quick Start

```bash
pip install observeml
```

```python
import observeml

observeml.configure(api_key="your-api-key")

# After your LLM call:
observeml.track(
    model="gpt-4o",
    latency_ms=320,
    input_tokens=150,
    output_tokens=80,
    cost_usd=0.0024,
)
```

## Configuration options

```python
observeml.configure(
    api_key="your-api-key",
    endpoint="https://api.observeml.io/v1/ingest",  # default
    flush_interval_s=5.0,   # OB-17: how often to batch-send events (default 5 s)
)
```

Or use the class directly for per-instance control:

```python
from observeml import ObserveML

tracker = ObserveML(
    api_key="your-api-key",
    flush_interval_s=1.0,   # flush every second in high-throughput environments
)
tracker.track(model="claude-3-5-sonnet", latency_ms=410)
```

## What is captured?

| Field | Type | Description |
|-------|------|-------------|
| `model` | str | e.g. `"gpt-4o"` |
| `latency_ms` | int | Wall-clock duration of the LLM call |
| `input_tokens` | int | Prompt token count |
| `output_tokens` | int | Completion token count |
| `cost_usd` | float | Estimated cost |
| `error` | bool | Whether the call failed |
| `error_code` | str | Provider error code if any |
| `call_site` | str | Optional fingerprint of source location |
| `prompt_hash` | str | Optional SHA-256 of prompt+response (dedup only) |

**What is NOT captured:** prompt text, response text, user identity, system prompts.

## Prompt hash (optional dedup)

```python
h = observeml.prompt_hash(my_prompt, llm_response)
observeml.track(model="gpt-4o", latency_ms=200, prompt_hash=h)
```

The hash enables deduplication without transmitting content.

## Performance

- `track()` p99 < 1ms — fire-and-forget, non-blocking
- Background flush every `flush_interval_s` seconds (default 5 s, batch of 100)
- Queue max 10,000 events; drops silently when full rather than blocking

## Privacy guarantee

ObserveML **never** transmits prompt or response content to any server.

This is enforced at three levels:
1. **Signature** — `track()` has no `prompt`/`response` parameters
2. **Payload inspection** — `test_content_leak` asserts the queued dict contains no forbidden keys
3. **CI gate** — tests run on every PR; a violation blocks merge

If you need content-level tracing, this is not the right tool by design.

## Alert thresholds (Sprint 02)

ObserveML supports server-side anomaly detection. Configure thresholds via the dashboard
or API to receive webhook notifications when metrics exceed defined limits:

```bash
curl -X POST https://api.observeml.io/v1/alerts \
  -H "x-api-key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "metric": "avg_latency_ms",
    "threshold": 1000,
    "call_site": "chat-completion",
    "webhook_url": "https://hooks.example.com/observeml"
  }'
```

Supported metrics: `avg_latency_ms`, `error_rate`, `cost_usd`.

