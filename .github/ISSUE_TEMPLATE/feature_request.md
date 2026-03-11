---
name: Feature Request
title: "[FEAT] "
labels: ["enhancement", "needs-triage"]
assignees: []
---

## Feature Summary
<!-- One sentence: what should ObserveML do that it doesn't today? -->

## User Story
> As a **[ML engineer / platform team / LLM app developer]**,  
> I want to **[action]**  
> so that **[outcome / value]**.

## Problem Being Solved
<!-- What observability gap does this address? -->

## Proposed Solution
<!-- SDK change? Dashboard feature? New metric type? -->

## RICE Estimation
| Dimension | Score (1–10) | Notes |
|-----------|-------------|-------|
| **Reach** | | How many SDK users affected? |
| **Impact** | | Does this improve detection rate? |
| **Confidence** | | |
| **Effort** | | Engineer-weeks |

**RICE Score** = ___

## Observer Principle Check
> "The observer must not alter the observed."
- [ ] This feature does NOT add latency to LLM calls (< 2ms SDK overhead budget)
- [ ] This feature does NOT change the output of observed LLM calls
- [ ] If adding a new metric type, sampling strategy is defined

## Philosophical Fit Check
- **Maya (Reality)**: Is this solving a real observability blind spot, or adding dashboard noise?
- **Viveka (Discernment)**: Is this metric/feature essential to LLM reliability?
- **Neti Neti (Limits)**: What will NOT be tracked? Explicitly scoped out?

## Acceptance Criteria
- [ ] 
- [ ] 
- [ ] 

## 333-Line Law
- [ ] This feature can be implemented without any single file exceeding 333 lines
