# ObserveML — Production Observability for LLM Apps

> Project 03 · The Agency AGI · NEXUS-Micro Deployment  
> **Version: v1.2.0 — 2026-03-16 — Sprint 5 (Teams, Billing, GDPR, Session Analytics)**
>
> *"Prajnanam Brahma" — Consciousness is Brahman. (Aitareya Upanishad 3.3)*  
> *Your LLM app is not conscious — but it should be observable. ObserveML gives it awareness of itself.*

[![CI](https://github.com/Venkatchavan/ObserveML-Production-Observability/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/Venkatchavan/ObserveML-Production-Observability/actions/workflows/ci-cd.yml)
[![PyPI](https://img.shields.io/pypi/v/observeml?label=PyPI)](https://pypi.org/project/observeml/)
[![npm](https://img.shields.io/npm/v/observeml?label=npm)](https://www.npmjs.com/package/observeml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/observeml)](https://pypi.org/project/observeml/)

---

## What Is ObserveML?

**ObserveML** is the observability layer that every LLM application is missing.
Drop in 3 lines. Latency, cost, tokens, errors, and anomaly alerts — surfaced on a
dashboard that answers: *"Is my AI working?"*

```python
# Python — 3 lines to full observability
import observeml

observeml.configure(api_key="obs_live_xxxx", sample_rate=0.1)  # sample 10% of calls
observeml.track(model="gpt-4o", latency_ms=320, input_tokens=150, output_tokens=80, cost_usd=0.0024, trace_id="your-otel-trace-id")
```

```typescript
// TypeScript / JavaScript
import { configure, track } from 'observeml'

configure('obs_live_xxxx', undefined, undefined, 0.1)  // sampleRate=0.1
track({ model: 'gpt-4o', latencyMs: 320, inputTokens: 150, outputTokens: 80, costUsd: 0.0024, traceId: 'your-otel-trace-id' })
```

---

## The Gap in the Market

| Tool | Gap |
|------|-----|
| LangSmith | LangChain only |
| Helicone | Basic cost + latency, no semantic analysis |
| Arize Phoenix | Requires MLOps expertise to operate |
| Datadog LLM | $40k+ enterprise contract |
| **ObserveML** | Framework-agnostic, < 3 lines, works with any LLM provider |

---

## What ObserveML Measures

| Metric | Why It Matters |
|--------|---------------|
| **Token cost per session** | Know your LLM bill per user before the month ends |
| **p95 / p99 latency** | SLA-grade latency monitoring per prompt version |
| **Prompt version drift** | Semantic similarity between prompt v1 and v2 responses |
| **RAG retrieval quality** | Are the retrieved chunks actually relevant to the query? |
| **Hallucination signals** | Confidence scoring + factual consistency checks |
| **Task completion rate** | Did the user get what they asked for? (implicit signal) |

---

## Tech Stack

| Layer | Technology | Version |
|-------|------------|----------|
| **Python SDK** | observeml (PyPI) | `1.2.0` |
| **JS/TS SDK** | observeml (npm) | `1.2.0` |
| **Java SDK** | io.observeml:observeml-java (Maven/Gradle) | `0.1.0` |
| **Backend API** | FastAPI + Uvicorn | `0.111` / `0.29` |
| **Metadata DB** | PostgreSQL | `16` |
| **Metrics Store** | ClickHouse (MergeTree, 90-day TTL) | `23.8` |
| **Dashboard** | React 18 + Vite + Recharts | `18` / `5` |
| **CI/CD** | GitHub Actions | — |
| **Deploy** | Fly.io (production) | — |

---

## Vedantic Design Principles Applied

| Principle | Application |
|-----------|------------|
| **Brahman** | Every trace contributes to the whole system's self-awareness |
| **Maya** | Metrics reveal what the LLM is *actually* doing vs. what we think it's doing |
| **Viveka** | Dashboard surfaces only signal, not noise — curated metrics, not 200 charts |
| **Neti Neti** | Hallucination scores are confidence indicators, not ground truth |
| **Sakshi** | ObserveML watches without judgment — all data captured, none hidden |
| **Vairagya** | Prompt versions are compared without attachment to the "old" approach |
| **Dharma** | Observability is infra — it supports the product, never becomes the product |

---

## Sprint History

| Sprint | Status | Focus |
|--------|--------|-------|
| **Sprint 0** | ✅ Done | Architecture, ClickHouse schema, PostgreSQL migrations |
| **Sprint 1** | ✅ Done | Python + JS SDK v0.1.0, POST /v1/ingest, ClickHouse writes |
| **Sprint 2** | ✅ Done | Alert rules, anomaly detection, dashboard v0.2 |
| **Sprint 3** | ✅ Done | Multi-model comparison, regression detection, v1.0.0 production |
| **Sprint 4** | ✅ Done | Sampling, SSE live feed, percentiles (p50/p95/p99), trace_id, model routing, CSV export, token budget |
| **Sprint 5** | ✅ Done | Teams/RBAC, Stripe billing (free tier), usage metering, prompt hash analytics, session grouping, Java SDK, API key rotation, GDPR deletion |

## Quick Start

```bash
# Python
pip install observeml==1.2.0

# TypeScript / Node
npm install observeml@1.2.0

# Java / Gradle
implementation 'io.observeml:observeml-java:0.1.0'
```

See the [Python SDK README](sdk/python/README.md) or the [docs site](docs-site/docs/quickstart.md) for a
full integration walkthrough.

---

## Agency Agents Activated

| Agent | Role |
|-------|------|
| AGI Goal Decomposer | Activation plan |
| Backend Architect | FastAPI + ClickHouse ingestion pipeline |
| Database Architect | ClickHouse schema (MergeTree, TTL, materialized views) |
| AI Engineer | Embedding-based drift, RAG relevance scoring, hallucination signals |
| Senior Developer | Python + JS SDK design |
| Frontend Developer | React dashboard with Recharts |
| DevOps Automator | CI/CD, PyPI + npm package release |
| Security Engineer | PII scrubbing in traces, OWASP audit |
| Ethical Reviewer | Hallucination score transparency, no false safety guarantees |
| QA / Reality Checker | Launch gate verification |
| Technical Writer | SDK docs for Python + JS |
| Growth Hacker | Dev.to articles, Twitter launch |

---

---

*Copyright © 2026 Venkat Chavan · Licensed under the [MIT License](LICENSE) · ObserveML v1.2.0 · [GitHub](https://github.com/Venkatchavan/ObserveML-Production-Observability)*
