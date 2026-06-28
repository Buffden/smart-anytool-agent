# Phase 5 - Hierarchical Tool Filtering

## Summary

Implement the AnyTool retriever layer that selects the relevant tool category for a given query and filters the schema set before passing it to the agent loop.

---

## Description

Passing all available tools to the LLM on every request is wasteful and error-prone. As the tool set grows, the model is more likely to select the wrong tool or get confused by irrelevant options. The AnyTool paper (ICML 2024) addresses this with a hierarchical retriever: first identify the right category, then pass only that category's tools to the agent.

This layer sits between the SMART check and the agent loop. It takes the user query, asks the model which category of tools is relevant, and returns the filtered subset of schemas for the agent loop to use.

---

## Source

AnyTool - ICML 2024

---

## Impact Area

- Tool selection accuracy
- Token efficiency on every agent call
- Scalability as more tools are added in future phases

---

## Dependencies

- Phase 1 (categorized tool schemas)
- Phase 4 (SMART layer - filtering only runs when a tool is confirmed needed)

---

## Acceptance Criteria

- [ ] Given a weather question, only weather tools are passed to the agent loop
- [ ] Given a math question, only calculator tools are passed to the agent loop
- [ ] Given a search question, only search tools are passed to the agent loop
- [ ] When no category matches with confidence, all tools are passed as a fallback
- [ ] Category selection is logged so the decision is visible during debugging

---

## Out of Scope

- Self-reflection on failure (Phase 9)
- Executing any tool calls
- Adding new tool categories beyond the initial three
