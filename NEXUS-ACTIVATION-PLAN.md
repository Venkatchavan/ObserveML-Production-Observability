# NEXUS Activation Plan — Project_03_ObserveML
> **The Agency AGI** · NEXUS-Micro Pipeline  
> Written by: AGI Goal Decomposer · Reviewed by: AGI Chief Orchestrator  
> Constitutional reference: `philosophy/AGENT-CONSTITUTION.md`  
> Version: v0.1.0 — 2026-03-11

---

## विषयः (Viṣaya) — Subject Confirmation

**What are we building?**  
ObserveML is a drop-in observability SDK for LLM applications (Python + JavaScript).
3 lines of code captures every prompt, completion, cost, latency, and semantic drift.
A React dashboard makes the invisible visible.

**Why does this exist?**  
Because production LLM applications are blind. Engineers don't know if their prompts
are degrading, if costs are exploding per user, or if RAG retrieval is getting worse over time.

**Brahman Check:** Does this serve the whole LLM ecosystem?  
→ Yes. Framework-agnostic observability raises the quality bar for all LLM production deployments.

**What success looks like in 15 days:**
- [ ] Python SDK installable: `pip install observeml`
- [ ] JavaScript SDK installable: `npm install observeml`
- [ ] Dashboard deployed showing cost, latency, drift charts for 1 test app
- [ ] 1 customer (dogfood) sending real traces

---

## संशयः (Saṃśaya) — Known Gaps & Doubts

| Gap | Risk | Resolution |
|-----|------|------------|
| ClickHouse vs PostgreSQL for trace storage | MEDIUM | ClickHouse for traces (append-only, high write), PG for user/config |
| Semantic drift detection requires embeddings — expensive | HIGH | Use cached embeddings; only compute drift on sampled 10% of traces |
| SDK must not add >50ms latency to LLM calls | HIGH | Async write to ClickHouse; SDK is fire-and-forget |
| PII may appear in prompts/completions | HIGH | Auto-detect and scrub PII patterns before storage |
| Trace volume may overwhelm ClickHouse on free tier | MEDIUM | Implement sampling rate config (default 10%, configurable) |

**Neti Neti Declaration:**  
We do not know: whether drift detection signals are actionable enough for customers.
We do not know: if scrubbing PII will affect drift accuracy. Needs Sprint 2 testing.

---

## Agent Activation Waves

### Wave 0 — Foundation (Days 1–2)

| Agent | Task | Output |
|-------|------|--------|
| **Backend Architect** | Design: ingestion pipeline, trace schema, sampling architecture | docs/02-architecture.md |
| **Database Architect** | Design: ClickHouse trace table + PostgreSQL config schema | docs/03-database-schema.md |
| **AI Engineer** | Design: embedding drift algorithm + RAG relevance scoring approach | `docs/ml-design.md` |
| **Sprint Prioritizer** | RICE-scored backlog for 3 sprints | sprint files |

---

### Wave 1 — SDK + Ingestion (Days 3–7)

| Agent | Task | Output |
|-------|------|--------|
| **Senior Developer** | Python SDK: OpenAI/Anthropic/LiteLLM wrappers | `sdk/python/observeml/` |
| **Senior Developer** | JavaScript SDK: OpenAI/Anthropic wrappers | `sdk/javascript/src/` |
| **Backend Architect** | FastAPI ingestion endpoint + ClickHouse writes | `api/app/routers/traces.py` |
| **AI Engineer** | PII scrubbing pipeline (regex + NER) | `api/app/services/pii_scrubber.py` |

**Wave 1 Śhāstrārtha Checkpoint:**  
> `/debate "The SDK uses async fire-and-forget writes. What happens when the ObserveML server is down?"`  
*Expected: local buffer + retry queue. Siddhānta should require offline resilience before Wave 2*

---

### Wave 2 — Dashboard + Drift (Days 8–11)

| Agent | Task | Output |
|-------|------|--------|
| **AI Engineer** | Semantic drift engine: cosine similarity rolling window | `api/app/services/drift_engine.py` |
| **Frontend Developer** | React dashboard: cost/latency/drift charts + trace explorer | `dashboard/src/` |
| **AI Engineer** | RAG relevance scoring: retrieved chunk → query relevance | `api/app/services/rag_evaluator.py` |

**Wave 2 Śhāstrārtha Checkpoint:**  
> `/debate "The drift chart shows semantic similarity over time. What question does this actually answer for an engineer?"`  
*Challenge lazy data display — the chart must answer a specific actionable question*

---

### Wave 3 — Harden & Launch (Days 12–15)

| Agent | Task | Output |
|-------|------|--------|
| **Security Engineer** | API key auth audit, PII scrubbing penetration test | security-threat-model.md |
| **DevOps Automator** | PyPI publish pipeline + npm publish pipeline + Fly.io deploy | CI/CD |
| **Ethical Reviewer** | PII scrubbing completeness review, no retention of sensitive completions | ethics-review.md |
| **QA / Reality Checker** | Launch gate 10-item verification + SDK latency benchmarks | test-plan.md |
| **Technical Writer** | SDK README for PyPI + npm + quickstart guide | docs/ |
| **Growth Hacker** | Dev.to article "We built LLM observability in 15 days" + HN launch | launch/ |
| **Memory Manager** | Retrospective → project-state v0.2.0 | memory/ |

---

## शास्त्रार्थः (Śhāstrārtha) Checkpoints

| ID | Subject | Day | Required Before |
|----|---------|-----|----------------|
| **SD-01** | ClickHouse vs TimescaleDB for traces | Day 2 | Wave 1 start |
| **SD-02** | SDK fire-and-forget vs blocking write + local buffer | Day 5 | Week 2 |
| **SD-03** | PII scrubbing: regex-only vs NER-assisted | Day 8 | Dashboard build |
| **SD-04** | Drift metric: what question does it answer? | Day 10 | Dashboard ship |
| **SD-05** | Launch gate: all 10 items green | Day 15 | Production deploy |

---

## Constitutional Compliance Checklist

- [ ] **Brahman**: Output serves observability of all LLM apps, not just OpenAI
- [ ] **Maya**: PII scrubbing solves the real privacy problem, not just the visible one
- [ ] **Viveka**: SDK adds < 50ms overhead — no tradeoff on the product being observed
- [ ] **Neti Neti**: Hallucination scoring documented as "signal, not ground truth"
- [ ] **Sakshi**: All trace data captured honestly — scrubbed but not deleted
- [ ] **Vairagya**: ClickHouse choice revisable in v0.2.0 if performance disappoints
- [ ] **Dharma**: Observability does not alter behavior of the app it observes
- [ ] **333-Line Law**: No SDK file exceeds 333 lines

---

## Handoff Package

| Artifact | Location | Owner |
|---------|----------|-------|
| `pip install observeml` | PyPI | DevOps Automator |
| `npm install observeml` | npm | DevOps Automator |
| Dashboard URL | Fly.io | Backend Architect |
| PII scrubbing audit | docs/security | Security Engineer |
| Performance benchmarks | docs/benchmarks | QA |
| Sprint retrospective | memory/project-state/ | Memory Manager |

---

*The Agency AGI · NEXUS Activation Plan · ObserveML · v0.1.0 · 2026-03-11*  
*"Chitta vritti nirodha" — The stilling of the fluctuations of consciousness. (Yoga Sutras 1.2)*  
*Observe the fluctuations of your LLM. Then still the noisy ones.*
