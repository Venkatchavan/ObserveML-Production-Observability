# ObserveML Ruby SDK — v0.1.0

Production observability for LLM applications — Ruby / Rails edition.

## Quick Start

```ruby
require 'observeml'

# Configure once at startup
ObserveML.configure(api_key: 'obs_live_xxxx')

# Instrument any LLM call — fire-and-forget, < 1ms overhead
t0 = Process.clock_gettime(Process::CLOCK_MONOTONIC, :millisecond)
response = openai.chat(...)
ObserveML.track(
  model:         'gpt-4o',
  latency_ms:    Process.clock_gettime(Process::CLOCK_MONOTONIC, :millisecond) - t0,
  input_tokens:  response.usage.prompt_tokens,
  output_tokens: response.usage.completion_tokens,
  cost_usd:      0.0024,
  call_site:     'chat_handler',
  session_id:    current_session_id,
)

# Graceful shutdown (called automatically via at_exit)
ObserveML.shutdown
```

## Observer Principle

`track()` **has no `prompt` or `response` parameter**. Only metadata is transmitted:

| Key | Type | Description |
|-----|------|-------------|
| `model` | String | Model name (`gpt-4o`, `claude-3-5`, etc.) |
| `latency_ms` | Integer | Wall-clock latency of the LLM call |
| `input_tokens` | Integer | Prompt token count |
| `output_tokens` | Integer | Completion token count |
| `cost_usd` | Float | Cost of the call |
| `call_site` | String | Identifier for the code location |
| `error` | Boolean | Whether the call errored |
| `error_code` | String | Error type if applicable |
| `session_id` | String | Session grouping key (OB-45) |
| `trace_id` | String | OTel trace ID (OB-36) |

## Thread Safety

The SDK uses a `SizedQueue(1000)` with a single daemon flush thread.
`track()` is non-blocking — it drops events silently when the queue is full
rather than blocking the caller.

## Zero Dependencies

Pure Ruby stdlib: `Net::HTTP`, `JSON`, `SecureRandom`. No gems required at runtime.
