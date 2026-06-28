# Phase 9 - Self-Reflection on Failure

## Summary

Extend the AnyTool layer with a self-reflection mechanism that retries with an adjusted tool selection when the agent loop fails to produce a satisfactory answer.

---

## Description

The AnyTool paper (ICML 2024) introduces a self-reflection loop that re-activates the retriever when the initial solution is impractical or fails. This prevents the agent from silently returning a wrong or incomplete answer when the first tool selection was incorrect.

When the agent loop returns a failure signal, the retriever re-evaluates the query, widens or adjusts the tool category, and routes to the agent loop again. This retry is bounded to prevent infinite loops.

---

## Source

AnyTool - ICML 2024

---

## Impact Area

- Reliability and robustness of the agent
- Failure recovery behavior
- User-facing answer quality on ambiguous or cross-category queries

---

## Dependencies

- Phase 5 (hierarchical tool filtering - reflection adjusts the same filtering logic)
- Phase 7 (agent solver loop - failure signals come from the loop)

---

## Acceptance Criteria

- [ ] When the agent loop returns a failure, the retriever retries with a wider tool selection
- [ ] Retry is bounded to a maximum number of attempts
- [ ] After exhausting retries, a clear fallback message is returned rather than crashing
- [ ] Each retry attempt is logged with the adjusted tool selection
- [ ] A successful retry result is indistinguishable from a first-attempt success to the user

---

## Out of Scope

- Changing the SMART decision on retry
- Fine-tuning retry thresholds beyond the initial implementation
- Handling failures caused by external API outages
