# Quick Start

## 1. Create an Account

Sign up at [app.observeml.io](https://app.observeml.io) and create your first API key.

## 2. Install the SDK

=== "Python"
    ```bash
    pip install observeml==1.0.0
    ```

=== "TypeScript / npm"
    ```bash
    npm install observeml@1.0.0
    ```

## 3. Configure

=== "Python"
    ```python
    import observeml

    observeml.configure(api_key="obs_live_xxxx")
    ```

=== "TypeScript"
    ```typescript
    import { configure } from "observeml";

    configure("obs_live_xxxx");
    ```

## 4. Track Your First Call

Wrap each LLM call with a timer and track the result. The call to `track()` is
fire-and-forget — it returns immediately and never blocks the caller.

=== "Python (OpenAI)"
    ```python
    import time
    import observeml
    from openai import OpenAI

    client = OpenAI()
    observeml.configure(api_key="obs_live_xxxx")

    def chat(prompt: str) -> str:
        t0 = time.perf_counter()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)

        observeml.track(
            model="gpt-4o",
            latency_ms=latency_ms,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            cost_usd=estimate_cost(response.usage),
            call_site="chat",
        )
        return response.choices[0].message.content
    ```

=== "TypeScript (OpenAI)"
    ```typescript
    import OpenAI from "openai";
    import { configure, track } from "observeml";

    const openai = new OpenAI();
    configure("obs_live_xxxx");

    async function chat(prompt: string): Promise<string> {
      const t0 = performance.now();
      const resp = await openai.chat.completions.create({
        model: "gpt-4o",
        messages: [{ role: "user", content: prompt }],
      });
      track({
        model: "gpt-4o",
        latencyMs: Math.round(performance.now() - t0),
        inputTokens: resp.usage?.prompt_tokens ?? 0,
        outputTokens: resp.usage?.completion_tokens ?? 0,
        callSite: "chat",
      });
      return resp.choices[0].message.content ?? "";
    }
    ```

## 5. Open the Dashboard

Go to [app.observeml.io](https://app.observeml.io), enter your API key, and see live metrics.

## Advanced Configuration

```python
observeml.configure(
    api_key="obs_live_xxxx",
    flush_interval_s=1.0,   # batch every 1 s (default: 5 s)
    endpoint="https://api.observeml.io/v1/ingest",  # default
)
```

## Set Up Alerts

Create a threshold rule to get notified when latency spikes:

```bash
curl -X POST https://api.observeml.io/v1/alerts \
  -H "x-api-key: obs_live_xxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "metric": "avg_latency_ms",
    "threshold": 1000,
    "webhook_url": "https://hooks.slack.com/your-webhook"
  }'
```
