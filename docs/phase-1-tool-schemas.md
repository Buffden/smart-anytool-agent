# Phase 1 - Tool Schemas Grouped by Category

## Summary

Define and organize the tool schema definitions that describe what each tool does, what arguments it accepts, and which category it belongs to.

---

## Description

The agent needs a structured way to communicate available tools to the LLM. Tool schemas are the definitions the model reads to decide which tool to call and what arguments to pass. Without well-written schemas, the model will pick the wrong tool or pass incorrect arguments.

Schemas must also be organized into named categories so the AnyTool layer can filter down to only the relevant subset rather than exposing every tool at once. This categorization is the core mechanism that makes hierarchical filtering possible.

---

## Source

AnyTool - ICML 2024

---

## Impact Area

Foundation layer - every other component in the pipeline depends on this being correct.

---

## Dependencies

None - this is the first piece to implement.

---

## Acceptance Criteria

- [ ] One schema defined per tool: weather lookup, calculator, web search
- [ ] Each schema describes when to use the tool, not just what it does
- [ ] Required and optional parameters are correctly distinguished
- [ ] Tools are grouped into named categories
- [ ] A flat list of all schemas is also available for fallback scenarios
- [ ] A human reading the schemas can predict which tool the model will call for a given query

---

## Out of Scope

- Implementing the actual tool functions
- Validating arguments passed by the model
- Any LLM calls
