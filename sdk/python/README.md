# ObserveML Python SDK

[![PyPI version](https://img.shields.io/pypi/v/observeml)](https://pypi.org/project/observeml/)
[![Python versions](https://img.shields.io/pypi/pyversions/observeml)](https://pypi.org/project/observeml/)
[![CI](https://github.com/Venkatchavan/ObserveML-Production-Observability/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/Venkatchavan/ObserveML-Production-Observability/actions/workflows/ci-cd.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../LICENSE)

**v1.1.0 — Drop-in LLM observability. Captures metadata only — never prompt or response content.**

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
    flush_interval_s=5.0,   # how often to batch-send events (default 5 s)
    sample_rate=0.1,        # OB-31: sample 10% of calls client-side (default 1.0 = 100%)
)
```

Or use the class directly for per-instance control:

```python
from observeml import ObserveML

tracker = ObserveML(
    api_key="your-api-key",
    flush_interval_s=1.0,   # flush every second in high-throughput environments
    sample_rate=0.5,        # sample 50%
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
| `trace_id` | str | Optional OTel trace ID for cross-system correlation (OB-36) |

**What is NOT captured:** prompt text, response text, user identity, system prompts.

## Prompt hash (optional dedup)

```python
h = observeml.prompt_hash(my_prompt, llm_response)
observeml.track(model="gpt-4o", latency_ms=200, prompt_hash=h)
```

The hash enables deduplication without transmitting content.

## Performance

- `track()` p99 < 1ms â€” fire-and-forget, non-blocking
- Background flush every `flush_interval_s` seconds (default 5 s, batch of 100)
- Queue max 10,000 events; drops silently when full rather than blocking

## Privacy guarantee

ObserveML **never** transmits prompt or response content to any server.

This is enforced at three levels:
1. **Signature** â€” `track()` has no `prompt`/`response` parameters
2. **Payload inspection** â€” `test_content_leak` asserts the queued dict contains no forbidden keys
3. **CI gate** â€” tests run on every PR; a violation blocks merge

If you need content-level tracing, this is not the right tool by design.

## Alert thresholds

ObserveML v1.1.3 includes server-side anomaly detection. Configure thresholds via the
dashboard or API to receive webhook notifications when metrics exceed defined limits:

```bash
# Create an alert rule (latency > 500 ms)
curl -X POST https://api.observeml.io/v1/alerts \
  -H 'x-api-key: obs_live_xxxx' \
  -H 'Content-Type: application/json' \
  -d '{"metric": "avg_latency_ms", "threshold": 500}'

# Token budget alert (projected monthly cost > $20)
curl -X POST https://api.observeml.io/v1/alerts \
  -H 'x-api-key: obs_live_xxxx' \
  -H 'Content-Type: application/json' \
  -d '{"metric": "monthly_projected_cost_usd", "threshold": 20}'
```

Allowed `metric` values: `avg_latency_ms`, `error_rate`, `cost_usd`, `monthly_projected_cost_usd`.

## Supported Python versions

`3.9`, `3.10`, `3.11`, `3.12` â€” tested in CI on every push.

## Changelog

See [CHANGELOG.md](../../CHANGELOG.md) for the full release history.

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


