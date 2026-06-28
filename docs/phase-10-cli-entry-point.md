# Phase 10 - CLI Entry Point

## Summary

Implement the command-line interface that accepts user input, passes it through the full agent pipeline, and displays the final response.

---

## Description

The CLI is the user-facing entry point that wires all previous phases together into a working end-to-end experience. It runs as a read-eval-print loop: accept a question, pass it to the SMART layer, route through the AnyTool layer and agent loop as needed, and print the final answer. The loop continues until the user exits.

This phase is also the integration test for the entire system - if the CLI works correctly end-to-end, all components are correctly connected.

---

## Source

Project Infrastructure

---

## Impact Area

- End-to-end integration of all components
- User-facing experience

---

## Dependencies

- All previous phases must be complete before this can be wired together

---

## Acceptance Criteria

- [ ] The CLI starts and waits for user input
- [ ] User input is passed through the SMART layer first
- [ ] If no tool is needed, the direct answer is printed immediately
- [ ] If a tool is needed, the question routes through AnyTool and the agent loop
- [ ] The final answer is printed clearly after each query
- [ ] Typing "exit" or "quit" terminates the session cleanly
- [ ] Errors from any layer are caught and displayed as a clean message rather than a stack trace
- [ ] The pipeline decision at each step (SMART decision, category selected, tools called) is optionally visible in a verbose mode

---

## Out of Scope

- Web or REST API interface
- Authentication or user sessions
- Conversation history across restarts
