# Phase 7 - Agent Solver Loop

## Summary

Implement the core agent loop that calls the LLM with filtered tool schemas, handles tool call responses, routes through validation, and iterates until a final answer is produced.

---

## Description

The agent loop is the central orchestration mechanism of the system. It receives the user question and filtered schemas from the AnyTool layer, calls the LLM, reads the response, and branches based on what the model returns. If the model returns a text answer, the loop ends. If the model returns tool calls, each call is dispatched through validation, the results are appended to the conversation, and the loop continues.

The loop must be bounded to prevent infinite iteration in cases where the model keeps requesting tool calls without converging on an answer.

---

## Source

AnyTool - ICML 2024

---

## Impact Area

- Core execution engine of the agent
- Correctness of single and multi-step tool call handling
- Safety via iteration limit

---

## Dependencies

- Phase 1 (tool schemas)
- Phase 5 (filtered schemas come from the AnyTool layer)
- Phase 6 (all tool calls go through validation and dispatch)

---

## Acceptance Criteria

- [ ] A question requiring one tool call resolves correctly in a single iteration
- [ ] A question requiring sequential tool calls resolves correctly across multiple iterations
- [ ] All tool results are appended to the conversation before the next LLM call
- [ ] The loop terminates when the model returns a text response with no tool calls
- [ ] The loop terminates with a fallback message when the iteration limit is reached
- [ ] Each iteration is logged with the tool calls made and results received

---

## Out of Scope

- Parallel tool calls in a single response (Phase 8)
- Self-reflection on failure (Phase 9)
- Streaming the final answer
- Conversation history across multiple user turns
