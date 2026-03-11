# ObserveML — Production Observability for LLM Apps
> Project 03 · The Agency AGI · NEXUS-Micro Deployment  
> Version: v0.1.0 — 2026-03-11 — Sprint 0 (Setup)
>
> *"Prajnanam Brahma" — Consciousness is Brahman. (Aitareya Upanishad 3.3)*
> *Your LLM app is not conscious — but it should be observable. ObserveML gives it awareness of itself.*

---

## What Is ObserveML?

**ObserveML** is the observability layer that every LLM application is missing.
Drop in 3 lines of middleware. Every prompt, completion, tool call, and RAG retrieval
is captured, traced, and surfaced on a dashboard that actually answers: *"Is my AI working?"*

```python
# Python — wrap your OpenAI client
from observeml import ObserveML
client = ObserveML.wrap(openai.OpenAI(), api_key="oml_...")
# All calls now traced automatically
```

```javascript
// JavaScript — same pattern
import { ObserveML } from 'observeml'
const client = ObserveML.wrap(new OpenAI(), { apiKey: 'oml_...' })
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

| Layer | Technology |
|-------|------------|
| **SDK** | Python + JavaScript/TypeScript |
| **Backend API** | FastAPI |
| **Storage** | ClickHouse (append-only traces, high throughput) |
| **Dashboard** | React 18 + Vite + Recharts |
| **Embeddings** | OpenAI text-embedding-3-small (drift detection) |
| **Tracing** | OpenTelemetry-compatible spans |
| **CI/CD** | GitHub Actions |
| **Deploy** | Fly.io |

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

## 15-Day Sprint Plan

| Sprint | Days | Focus | Lead Agent |
|--------|------|-------|-----------|
| **Sprint 0** | 1–2 | Architecture + ClickHouse setup + tracing schema | Backend Architect + DB Architect |
| **Sprint 1** | 3–7 | Python/JS SDK + trace ingestion API + ClickHouse writes | AI Engineer + Senior Developer |
| **Sprint 2** | 8–11 | Dashboard: cost/latency/drift charts + prompt diff viewer | Frontend Developer |
| **Sprint 3** | 12–15 | Hallucination scoring + RAG eval + harden + launch | AI Engineer + Security + QA |

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

*The Agency AGI · ObserveML v0.1.0 · 2026-03-11*
