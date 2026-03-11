## Summary
<!-- What changed and why? -->

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] SDK change (Python / JavaScript)
- [ ] Refactor
- [ ] Security fix
- [ ] Dependency update

## Test Coverage
- [ ] Unit tests added/updated (coverage ≥ 80%)
- [ ] SDK tests pass on Python 3.9–3.12 matrix
- [ ] All existing tests pass

## 333-Line Law
- [ ] No source file I touched or created exceeds 333 lines

## Vedantic Check
<!-- The Agency AGI constitutional ground — AGENT-CONSTITUTION.md -->
- [ ] **Maya**: Does this change observe what LLM apps are *actually* doing vs. what we think?
- [ ] **Viveka**: SDK overhead impact checked — does this change add latency to the observed app?
- [ ] **Dharma**: Is this observability, not interference? The observer must not alter the observed.
- [ ] **Vairagya**: Not attached to the previous metric design if data shows it doesn't answer a real question

## SDK Compatibility
- [ ] Python SDK: backward compatible (no breaking changes without version bump)
- [ ] JavaScript SDK: backward compatible
- [ ] PII scrubbing not weakened by this change

## Security Checklist
- [ ] No secrets or API keys in code or tests
- [ ] PII scrubbing pipeline not bypassed
- [ ] ClickHouse injection not possible via trace data

## Related Issues
Closes #
