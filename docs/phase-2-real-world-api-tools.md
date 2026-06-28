# Phase 2 - Real-World API Tools

## Summary

Implement the weather lookup and web search tool functions that fetch live data from external APIs.

---

## Description

The agent needs real tools that fetch actual data - not stubs. Weather lookup retrieves current conditions for a given city from a public weather API. Web search retrieves live results for a given query. Both tools must handle failure gracefully and return clean, structured responses that the agent can pass back to the model.

These tools demonstrate the core AnyTool premise: a tool-calling agent is only as useful as the real-world APIs it can access.

---

## Source

AnyTool - ICML 2024

---

## Impact Area

- Weather and search capabilities of the agent
- Quality of data returned to the LLM for answer synthesis

---

## Dependencies

- None - tool functions are standalone and do not depend on schemas

---

## Acceptance Criteria

- [ ] Weather lookup accepts a city name and temperature unit, returns current temperature and conditions
- [ ] Weather lookup handles city not found without crashing
- [ ] Web search accepts a query and result count, returns a list of results with title, URL, and snippet
- [ ] Web search handles empty results gracefully
- [ ] Both tools use free APIs that require no API key
- [ ] Both tools return structured data, not raw API responses

---

## Out of Scope

- Calculator / expression evaluation (Phase 3)
- Argument validation (Phase 6)
- Routing or dispatch logic
