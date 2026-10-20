# Phase 13 - Approval Gate and Audit Log

## Summary

Give the agent its first action with a real effect (sending the email draft the workflow already writes), and put a human in front of every action like it. Every dispatched call, approved or not, is recorded in an append-only audit log.

---

## Description

Until now every tool only reads: it looks things up, queries the database, or drafts text, and nothing outside the agent changes. This phase adds a `send_email` tool that delivers to a local outbox, and makes `validation.dispatch` the place where the risk of a call gets checked.

Every tool gets an explicit read or write classification next to its registration. Reads run as before. Writes stop at an injected approver, which sees the exact validated arguments plus any upstream failure, and the call only runs on an explicit yes. Everything else is a denial: no approver, an approver error, a timeout, or any other answer. A denial comes back as a structured result of kind `denied`, and the agent treats it as final.

The planner also gets a second legal output: a clarification question instead of a plan, for requests too ambiguous to act on.

Full concepts, tasks, and testing checklist: [week 15 docs](https://github.com/Buffden/ai-application-engineering/tree/main/docs/phase-3-ai-agents-and-tool-calling/week-15-human-in-the-loop-ai) (`concepts.md`, `project.md`, `goals.md`).

---

## Source

Engineering Best Practice (OWASP Top 10 for LLM Applications: Excessive Agency, Prompt Injection)

---

## Impact Area

- `validation.py`: classification in `_REGISTRY`, the gate and the audit record inside `dispatch`
- `schemas.py`, `tools.py`: the new `send_email` tool
- `workflow.py`: proposes the send after synthesis, through `dispatch`
- `agent.py`: treats a denial as final
- `planner.py`, `prompts/planner.txt`: clarification output shape
- New: approver implementations (CLI and scripted), outbox directory and audit log file (both ignored by git)

---

## Dependencies

- Phase 6 (single dispatch entry point)
- The week 14 planner, executor, and workflow (`planner.py`, `executor.py`, `workflow.py`)

---

## Acceptance Criteria

- [ ] Every registered tool has an explicit read/write classification, and a test fails if a new tool is registered without one
- [ ] An unclassified tool is treated as a write
- [ ] `send_email` writes exactly one file to the outbox and returns the usual result or `{"error": ..., "kind": ...}` shape
- [ ] The gate sits inside `dispatch`, after validation and before the tool runs. Reads skip the approver, writes always reach it
- [ ] The gate fails closed: no approver, an approver error, a timeout, or anything other than an explicit yes means `kind: denied` and no effect
- [ ] The approver sees the tool, the resolved arguments, the reason, and any upstream step that failed
- [ ] The audit log is JSON Lines, append-only, one record per dispatched call (reads, approvals, denials, validation failures), with a run id, and holds arguments but not full results
- [ ] `run_workflow` proposes the send through the gate, and still returns the report when the send is denied
- [ ] After a denial, the reactive loop makes no further write calls in that turn
- [ ] An ambiguous request returns a clarification question and dispatches nothing
- [ ] Tests cover the gate, the audit log, the workflow send path, and the clarification fallback

---

## Out of Scope

- Real email delivery (SMTP or a mail API)
- A web UI for approvals
- Log rotation, shipping, or dashboards (roadmap week 19)
