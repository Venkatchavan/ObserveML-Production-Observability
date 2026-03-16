# Quick Start

## 1. Create an Account

Sign up at [app.observeml.io](https://app.observeml.io) and create your first API key.

## 2. Install the SDK

=== "Python"
    ```bash
    pip install observeml==2.0.0
    ```

=== "TypeScript / npm"
    ```bash
    npm install observeml@2.0.0
    ```

=== "Ruby"
    ```bash
    gem install observeml
    ```

=== "Java / Gradle"
    ```groovy
    implementation 'io.observeml:observeml-java:0.1.0'
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
fire-and-forget â€” it returns immediately and never blocks the caller.

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
    sample_rate=0.1,        # OB-31: only send 10% of events (default: 1.0 = 100%)
)
```

## Sampling (OB-31)

For high-volume services you can reduce telemetry overhead with head-based sampling.
Dropping happens client-side — events are never serialised or queued:

=== "Python"
    ```python
    observeml.configure(api_key="obs_live_xxxx", sample_rate=0.05)  # 5%
    ```

=== "TypeScript"
    ```typescript
    import { ObserveML } from "observeml";
    const tracker = new ObserveML("obs_live_xxxx", undefined, undefined, 0.05);
    ```

## OTel Trace ID (OB-36)

Pass an OpenTelemetry trace ID to correlate LLM calls with distributed traces:

=== "Python"
    ```python
    from opentelemetry import trace

    span = trace.get_current_span()
    trace_id = format(span.get_span_context().trace_id, "032x")

    observeml.track(
        model="gpt-4o",
        latency_ms=320,
        cost_usd=0.0024,
        trace_id=trace_id,
    )
    ```

=== "TypeScript"
    ```typescript
    track({
      model: "gpt-4o",
      latencyMs: 320,
      traceId: span.spanContext().traceId,
    });
    ```

## Java SDK (OB-46)

Instrument JVM applications (including Android) with the Java SDK:

```java
import io.observeml.TrackerClient;
import java.util.Map;

TrackerClient tracker = new TrackerClient("obs_live_xxxx");
tracker.track(Map.of(
    "model", "gpt-4o",
    "latencyMs", 320,
    "inputTokens", 150,
    "outputTokens", 80,
    "costUsd", 0.0024
));
tracker.shutdown();  // graceful flush on app exit
```

## Ruby SDK (OB-57)

Instrument Ruby and Rails applications with the Ruby SDK (zero runtime dependencies):

```ruby
require 'observeml'

ObserveML.configure(api_key: 'obs_live_xxxx')

# In your LLM wrapper:
t0 = Process.clock_gettime(Process::CLOCK_MONOTONIC, :millisecond)
response = client.chat(messages: [{ role: 'user', content: prompt }])
latency_ms = Process.clock_gettime(Process::CLOCK_MONOTONIC, :millisecond) - t0

ObserveML.track(
  model: 'gpt-4o',
  latency_ms: latency_ms,
  input_tokens: response.usage.prompt_tokens,
  output_tokens: response.usage.completion_tokens,
  cost_usd: 0.0024,
  call_site: 'chat'
)
```

`ObserveML.track` is fire-and-forget — it enqueues the event and returns immediately.
The daemon flush thread batches and sends events every 5 seconds.
Call `ObserveML.shutdown` to drain the queue gracefully on app exit (automatically
called via `at_exit`).

## Session Grouping (OB-45)

Tag related LLM calls with a `session_id` to aggregate cost and latency per session:

=== "Python"
    ```python
    observeml.track(model="gpt-4o", latency_ms=320, cost_usd=0.0024,
                    session_id="user-session-abc123")
    ```

=== "TypeScript"
    ```typescript
    track({ model: "gpt-4o", latencyMs: 320, costUsd: 0.0024,
            sessionId: "user-session-abc123" });
    ```

Then retrieve the session summary:

```bash
curl https://api.observeml.io/v1/metrics/session/user-session-abc123 \
  -H "x-api-key: obs_live_xxxx"
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

