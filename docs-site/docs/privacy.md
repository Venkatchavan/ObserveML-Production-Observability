# Privacy & Observer Principle

## The Core Guarantee

> **ObserveML never transmits prompt text, response text, user identity, or system prompts.**

This is the Observer Principle — a constitutional constraint of the ObserveML project.
It is enforced at three independent levels and cannot be disabled.

## What IS Captured

| Field | Description |
|-------|-------------|
| `model` | Model identifier string (e.g. `"gpt-4o"`) |
| `latency_ms` | Wall-clock duration of the LLM call in milliseconds |
| `input_tokens` | Prompt token count from the provider's usage object |
| `output_tokens` | Completion token count |
| `cost_usd` | Estimated cost in USD |
| `error` | Boolean — did the call produce an error? |
| `error_code` | Provider error code string, if any |
| `call_site` | Optional tag you provide to identify the code location |
| `prompt_hash` | *Optional* SHA-256 of (prompt + response) for deduplication only |

## What is NOT Captured

- Prompt text
- Response text
- System prompts
- User identity or session data
- IP addresses
- Any PII

## Three-Level Enforcement

### Level 1 — API Signature

`track()` has no `prompt` or `response` parameter. You cannot accidentally pass content.

```python
# This does not compile — there is no 'prompt' parameter:
observeml.track(model="gpt-4o", latency_ms=200, prompt="my prompt")
# TypeError: track() got an unexpected keyword argument 'prompt'
```

### Level 2 — Payload Inspection

The unit tests assert that the queued dict contains no forbidden keys:

```python
# From sdk/python/tests/test_tracker.py — runs on every PR
assert "prompt" not in event
assert "response" not in event
assert "prompt_content" not in event
assert "response_content" not in event
```

### Level 3 — CI Gate

Both content-leak tests (Python + TypeScript) run on every pull request.
A failure blocks merge. The Vedantic Launch Gate in Sprint 03 requires these
tests to pass on the final published package, not just source.

## Prompt Hash — Optional Deduplication

The `prompt_hash` field is opt-in and is a one-way SHA-256 hash:

```python
h = observeml.prompt_hash(my_prompt, llm_response)
observeml.track(model="gpt-4o", latency_ms=200, prompt_hash=h)
```

The hash allows deduplication of identical calls without revealing content.
A SHA-256 hash cannot be reversed to recover the original text.

## Data Retention

- ClickHouse metric events: 90-day TTL (configurable)
- Alert fired records: no automatic TTL (pruning planned in roadmap)
- No backups of prompt/response content exist — there is nothing to back up

## Compliance Notes

ObserveML is designed to be safely deployable in environments with:
- GDPR data minimisation requirements
- SOC 2 Type II audit requirements
- HIPAA-covered workloads (note: you must conduct your own HIPAA assessment)
- Enterprise LLM governance policies that prohibit prompt logging
