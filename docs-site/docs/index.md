# ObserveML

**v1.0.2 — Drop-in LLM observability for production AI applications.**

ObserveML tracks what matters — latency, tokens, cost, error rates — without ever
touching prompt or response content.

## Why ObserveML?

| Problem | ObserveML's answer |
|---------|-------------------|
| LLM calls are slow and expensive | p99 < 1ms `track()` overhead; real-time dashboards |
| Cost visibility is poor | Per-model daily cost breakdown, auto-estimated |
| Regressions go unnoticed | Sliding-window statistical detection (Welch's z-test) |
| Compliance requires no-content logging | Observer Principle — no prompt/response transmitted |

## Installation

=== "Python"
    ```bash
    pip install observeml==1.0.0
    ```

=== "TypeScript / npm"
    ```bash
    npm install observeml@1.0.0
    ```

## 30-Second Integration

```python
import observeml

observeml.configure(api_key="your-api-key")

# Somewhere after your LLM call:
observeml.track(
    model="gpt-4o",
    latency_ms=320,
    input_tokens=150,
    output_tokens=80,
    cost_usd=0.0024,
)
```

That's it. Events batch-send in the background every 5 seconds. The caller is never blocked.

## Dashboard

- **Overview** — 7-day trend + per-call-site breakdown
- **Compare** — Side-by-side model latency / error / cost charts + regression feed
- **Alerts** — Real-time threshold breach feed + configurable rules

## Next Steps

- [Quick Start](quickstart.md) — full integration in 5 minutes
- [Privacy](privacy.md) — how the Observer Principle works
- [API Reference](api-reference.md) — all SDK parameters and REST endpoints
