# AnyTool: Agent Loop, Parallel Calls, and Self-Reflection - Research Notes

**Paper**: AnyTool: Self-Reflective, Hierarchical Agents for Large-Scale API Calls
**Venue**: ICML 2024
**arXiv**: [https://arxiv.org/abs/2402.04253](https://arxiv.org/abs/2402.04253)
**GitHub**: [https://github.com/dyabel/AnyTool](https://github.com/dyabel/AnyTool)

---

## Problem It Solves

Existing tool-calling agents struggle when the number of available tools is large. Passing all tools to the LLM at once causes:

- Context window overflow (thousands of tool descriptions)
- The model picking wrong or irrelevant tools
- No recovery mechanism when the first selection fails

AnyTool solves this with three mechanisms: hierarchical filtering, a bounded solver loop, and self-reflection on failure.

---

## Core Idea

AnyTool decomposes tool calling into three stages:

```text
1. Retrieve      → narrow the tool space before the LLM sees it
2. Solve         → agent loop calls LLM + tools until answer found
3. Reflect       → if failed, widen tool selection and retry
```

---

## Agent Solver Loop

See diagram: [agent-solver-loop.puml](agent-solver-loop.puml)

The solver loop is the core execution engine. It iterates between calling the LLM and executing tools until one of two things happens:

- The model produces a text answer with no tool calls → success, exit loop
- The iteration limit is reached → signal failure to the reflection layer

**Why the limit matters**: Without it, a model that repeatedly calls tools without converging would loop forever. The limit forces a failure signal that the reflection layer can act on.

**Why results go back into messages**: The LLM is stateless. Every new call starts fresh. Appending tool results to the conversation is the only way to carry context forward across iterations.

---

## Parallel Tool Calls

See diagram: [parallel-tool-calls.puml](parallel-tool-calls.puml)

The LLM can return multiple tool calls in a single response. This happens when the answer requires data from more than one source simultaneously, e.g., weather in two cities, or a calculation combined with a search.

**Key constraint**: All results must be appended before the next LLM call. If you only execute the first and skip the rest, the model's next response will be based on incomplete context; it either re-requests the missing data or synthesises a wrong answer.

**Partial failure**: If one tool call fails (e.g., API error), its error result is still appended. The model receives both the success and the error and decides how to proceed. The loop does not abort on a single tool failure.

---

## Self-Reflection on Failure

See diagram: [self-reflection.puml](self-reflection.puml)

Inspired by the AnyTool paper's reflection mechanism. When the solver loop signals failure (`None`), the retriever widens the tool selection and retries.

**Why widening works**: The first failure often means the tool category was too narrow. The question may span multiple categories, or the category classifier made the wrong call. Widening to all tools gives the model a second chance with the full tool set.

**Why retries are bounded**: Unbounded reflection loops can spiral. A fixed `max_retries` ensures the system always terminates with either an answer or a clean fallback message, never a hang or crash.

**User transparency**: A successful retry result is indistinguishable from a first-attempt success. The user always receives a string. The failure signal (`None`) is internal to the pipeline.

---

## Key Results from the Paper

- Outperforms ToolLLM by **35.4%** on ToolBench benchmark
- Handles APIs at scale (16,000+ tools) via hierarchical filtering
- Self-reflection loop recovers from ~30% of initial failures
- GPT-4 backend with hierarchical retrieval consistently outperforms flat tool passing

---

## How This Project Implements It

| Paper Mechanism | Project Implementation |
| --- | --- |
| Solver loop with iteration bound | `agent.py`: `solve()` with `agent_max_iterations` |
| Parallel tool execution | `agent.py`: `for call in message.tool_calls` |
| Failure signal | `agent.solve()` returns `None` on limit |
| Self-reflection + widening | `retriever.py`: `run()` with `retriever_max_retries` |
| Fallback to user | `retriever.run()` returns fallback string after exhausting retries |

The paper uses a large-scale API corpus with thousands of tools. This project uses three tools (weather, search, calculator) but applies the same loop-and-reflect architecture at small scale.
