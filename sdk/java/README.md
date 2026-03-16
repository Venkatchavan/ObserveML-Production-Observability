# ObserveML Java SDK — v0.1.0

> OB-46 · Sprint 05 · Java / Kotlin SDK for JVM-based LLM applications

[![Java](https://img.shields.io/badge/Java-11%2B-blue)](https://adoptium.net/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../LICENSE)

---

## Installation

### Gradle
```groovy
implementation 'io.observeml:observeml-java:0.1.0'
```

### Maven
```xml
<dependency>
    <groupId>io.observeml</groupId>
    <artifactId>observeml-java</artifactId>
    <version>0.1.0</version>
</dependency>
```

---

## Quick Start

```java
import io.observeml.TrackerClient;
import java.util.HashMap;
import java.util.Map;

// Create one instance per application (thread-safe)
TrackerClient tracker = new TrackerClient(
    "obs_live_xxxx",
    "https://api.observeml.io"
);

// Track an LLM call — fire and forget
Map<String, Object> event = new HashMap<>();
event.put("model",        "gpt-4o");
event.put("latencyMs",    320);
event.put("inputTokens",  150);
event.put("outputTokens", 80);
event.put("costUsd",      0.0024);
event.put("callSite",     "chat-endpoint");
event.put("sessionId",    "user-session-abc123");   // OB-45
event.put("traceId",      "otel-trace-id-here");    // OB-36
tracker.track(event);

// Graceful shutdown (flush remaining events)
tracker.shutdown();
```

---

## Observer Principle

> **There is no `prompt` or `response` parameter — ever.**
>
> `TrackerClient.track()` accepts only telemetry metadata:
> latency, token counts, cost, model name, call site, session ID, and trace ID.
> Raw prompt and response text are never transmitted to ObserveML.

---

## Accepted Keys

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `model` | `String` | ✅ | Model name (`gpt-4o`, `claude-3-5`, etc.) |
| `latencyMs` | `int` | ✅ | End-to-end latency in milliseconds |
| `inputTokens` | `int` | | Prompt token count |
| `outputTokens` | `int` | | Completion token count |
| `costUsd` | `double` | | Estimated cost in USD |
| `callSite` | `String` | | Source location identifier |
| `error` | `boolean` | | Whether the call errored |
| `errorCode` | `String` | | Provider error code if any |
| `sessionId` | `String` | | Session grouping ID (OB-45) |
| `traceId` | `String` | | OpenTelemetry trace ID (OB-36) |

---

## Thread Safety

`TrackerClient` is fully thread-safe. A single daemon thread drains events
from a bounded queue (capacity 1,000) and flushes them in batches of up to
50 to the API. Calling `track()` from multiple threads simultaneously is safe.

---

## Build

```bash
./gradlew build
./gradlew test
./gradlew jar
```

Requires JDK 11+. No runtime dependencies beyond the Java standard library.

---

*Copyright © 2026 Venkat Chavan · MIT License · ObserveML v1.2.0*
