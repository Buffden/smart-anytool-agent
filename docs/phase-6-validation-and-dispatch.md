# Phase 6 - Pydantic Argument Validation and Dispatch

## Summary

Implement the validation layer that parses, validates, and routes tool call requests from the agent loop to the correct tool function.

---

## Description

The model returns tool call arguments as a raw JSON string. Before any tool function is invoked, these arguments must be parsed, validated against the expected schema, and routed to the correct function. This layer is the security and reliability boundary between the LLM and the actual tool execution.

Validation catches malformed JSON, missing required fields, wrong types, and out-of-range values before they reach the tool. Dispatch ensures that every tool call is routed through a single, auditable entry point rather than scattered conditionals.

---

## Source

Engineering Best Practice

---

## Impact Area

- Security boundary between the LLM and tool execution
- Reliability of every tool call
- Error messages returned to the model when arguments are invalid

---

## Dependencies

- Phase 1 (tool schemas - validation is against these definitions)
- Phase 2 and Phase 3 (tool functions must exist to dispatch to)

---

## Acceptance Criteria

- [ ] Raw JSON string from the model is parsed before any validation occurs
- [ ] Malformed JSON returns a structured error without crashing
- [ ] Missing required arguments return a descriptive error
- [ ] Wrong argument types are caught and reported cleanly
- [ ] Valid arguments are dispatched to the correct tool function
- [ ] All dispatch goes through a single entry point - no direct tool calls elsewhere in the codebase
- [ ] Error results are returned in the same format as success results so the agent loop handles both uniformly

---

## Out of Scope

- Retrying failed tool calls (handled by self-reflection in Phase 9)
- Modifying or sanitizing argument values beyond type coercion
- Authentication or rate limiting on tool calls
