# Phase 3 - Safe Expression Evaluation

## Summary

Implement the calculator tool that evaluates arithmetic expressions safely without exposing arbitrary code execution.

---

## Description

The agent needs to perform calculations on behalf of the user. The naive approach - passing the model's expression directly to a language evaluator - is a critical security vulnerability. A malicious or poorly formed expression could execute arbitrary code.

The safe approach parses the expression into an abstract syntax tree first, inspects every node, and only permits arithmetic operations. Anything outside that boundary is rejected with a clear error before any computation occurs.

---

## Source

Engineering Best Practice

---

## Impact Area

- Security boundary of the agent
- Calculator capability

---

## Dependencies

- None - tool functions are standalone

---

## Acceptance Criteria

- [ ] Arithmetic expressions with addition, subtraction, multiplication, and division are evaluated correctly
- [ ] Non-arithmetic input is rejected with a descriptive error before any evaluation occurs
- [ ] Division by zero is handled without crashing
- [ ] The tool never executes arbitrary code under any input
- [ ] Returns a structured response containing the original expression and the result

---

## Out of Scope

- Scientific functions, trigonometry, or advanced math
- Symbolic computation
- Argument validation at the dispatch layer (Phase 6)
