# Phase 4 - Self-Awareness Before Tool Calling

## Summary

Implement the SMART layer that determines whether the agent needs to call a tool or can answer directly from its own knowledge before the agent loop starts.

---

## Description

Most tool-calling agents call tools indiscriminately - even for questions the model can already answer accurately. The SMART paper (ACL 2025) shows this leads to unnecessary latency, higher API costs, and paradoxically worse accuracy.

The self-awareness check is a lightweight pre-step: before routing to any tool, ask the model to judge whether external data is actually required. If the model can answer confidently from its training knowledge, return the answer immediately without entering the tool-calling pipeline.

Real-world results from the paper: 24% reduction in unnecessary tool calls, 37% improvement in overall accuracy.

---

## Source

SMART - ACL 2025

---

## Impact Area

- Entry point of the agent pipeline
- Latency and cost of every agent interaction
- Overall answer quality

---

## Dependencies

- Phase 1 (tool schemas - the SMART layer needs to know what tools exist to reason about necessity)

---

## Acceptance Criteria

- [ ] A question answerable from parametric knowledge returns a direct answer without any tool being called
- [ ] A question requiring real-time data correctly routes to the tool pipeline
- [ ] A question requiring a calculation correctly routes to the tool pipeline
- [ ] The decision includes a short reason that can be logged
- [ ] The system prompt clearly defines the boundary between tool-needed and tool-not-needed cases
- [ ] Edge cases (ambiguous queries) default to routing through the tool pipeline

---

## Out of Scope

- Selecting which tool to call (Phase 5)
- The agent loop itself (Phase 7)
- Calibrating or fine-tuning the self-awareness threshold
