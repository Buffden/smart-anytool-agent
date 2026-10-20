# Phase 14 - MCP Server and Client

## Summary

Move three capabilities (PostgreSQL queries, the text intelligence REST API, and document retrieval over `rag-document-engine`) behind a Model Context Protocol server in its own process. The agent becomes an MCP host that discovers and calls those tools over stdio, with Phase 13's gate and audit log covering them exactly as they cover local tools.

---

## Description

Today every tool is compiled into the agent: its schema is in `schemas.py`, its function is in `tools.py`, and `_REGISTRY` ties them together. This phase splits that. A server built on the official MCP Python SDK exposes the database, backend, and retrieval capabilities as tools, and the ingested documents as resources. The agent launches the server, lists its tools once, translates them into OpenAI function schemas, and merges them with the tools that stay local.

The safety properties don't move to the server. `query_database` keeps both of its layers (the `sqlglot` validator and the `agent_readonly` role) on the server side. The read/write classification stays on the host, keyed by tool name, because the MCP spec says a server's own annotations must be treated as untrusted. Every call, local or MCP, still goes through `dispatch` before it's handed to either a local function or the MCP client.

Target MCP spec revision 2026-07-28 (stateless, a protocol version on every request, `server/discover`), and check which revisions your installed SDK version speaks.

Full concepts, tasks, and testing checklist: [week 16 docs](https://github.com/Buffden/ai-application-engineering/tree/main/docs/phase-3.5-model-context-protocol/week-16-model-context-protocol) (`concepts.md`, `project.md`, `goals.md`).

---

## Source

Model Context Protocol specification (modelcontextprotocol.io)

---

## Impact Area

- New: the MCP server (location decided in week 16's `project.md`), exposing `query_database`, `analyze_text`, `classify_text`, `list_conversations`, `get_chat_history`, `send_chat_message`, `search_documents`, and document resources
- `validation.py`: `dispatch` routes to the local function or the MCP client, after the gate and the audit record
- `schemas.py`, `retriever.py`: discovered tools join the local ones before filtering
- `agent.py` / `main.py`: launch the server and discover its tools once at startup
- `tools.py`: the moved tools leave, and `get_weather`, `web_search`, `calculator`, `send_email` stay

---

## Dependencies

- Phase 13 (the gate and audit log must cover MCP calls before any write is reachable over MCP)
- Phase 6 (dispatch)
- Phase 2 `rag-document-engine` (hybrid search for `search_documents`)

---

## Acceptance Criteria

- [ ] The server runs over stdio and passes a manual check in the MCP Inspector before the agent connects
- [ ] `query_database` on the server still enforces the `sqlglot` validator and connects as `agent_readonly`
- [ ] Nothing in the server writes to standard output except the protocol
- [ ] The agent discovers server tools once at startup and refreshes only when the server says its list changed
- [ ] Every MCP call goes through `dispatch`, with host-side classification, approval for writes, and an audit record showing where the tool ran
- [ ] An MCP tool with no host-side classification is treated as a write
- [ ] `send_chat_message` over MCP stops for approval, and a denial leaves the backend unchanged
- [ ] `search_documents` returns top chunks with source and chunk index, and the agent cites the source in its answer
- [ ] A stopped or crashed server produces a clear `transport` error, never an empty result
- [ ] Tests cover discovery, the gate over MCP, error mapping, and the audit log

---

## Out of Scope

- Streamable HTTP transport and authorization (roadmap week 20)
- Sampling and elicitation
- Publishing the server for other hosts
- Connecting third-party MCP servers
