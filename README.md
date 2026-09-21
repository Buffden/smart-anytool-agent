# smart-anytool-agent

A tool-calling agent that implements concepts from two peer-reviewed AI research papers - **SMART** (ACL 2025) and **AnyTool** (ICML 2024) - on top of OpenAI function calling.

Most tool-calling agents dump every available tool at the LLM and hope it picks correctly. This agent does two things differently:

1. **SMART layer** - before calling any tool, the agent asks: "can I already answer this from my own knowledge?" If yes, it answers directly and skips tool calling entirely. Inspired by *SMART: Self-Aware Agent for Tool Overuse Mitigation* (ACL 2025 Findings).

2. **AnyTool layer** - if a tool is needed, the agent does not pass all tools to the LLM at once. It first filters to the relevant tool category, then passes only that subset. If the result is unsatisfactory, a self-reflection loop retries. Inspired by *AnyTool: Self-Reflective, Hierarchical Agents for Large-Scale API Calls* (ICML 2024).

---

## Research Papers

| Paper | Venue | Key Contribution |
| --- | --- | --- |
| [SMART: Self-Aware Agent for Tool Overuse Mitigation](https://arxiv.org/abs/2502.11435) | ACL 2025 Findings | Self-awareness layer that reduces tool calls by 24% while improving accuracy by 37% |
| [AnyTool: Self-Reflective, Hierarchical Agents for Large-Scale API Calls](https://arxiv.org/abs/2402.04253)<br>[GitHub Repository - AnyTool](https://github.com/dyabel/AnyTool) | ICML 2024 | Hierarchical tool filtering + self-reflection loop; outperforms ToolLLM by 35.4% |

---

## Diagrams

### Architecture

![Architecture](diagrams/docs/architecture.svg)

### Full Pipeline Sequence

![Full Pipeline](diagrams/docs/additional-notes/full-pipeline.svg)

---

## Setup

```bash
git clone https://github.com/Buffden/smart-anytool-agent
cd smart-anytool-agent

python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip3 install -e .

cp .env.example .env
# Add your OPENAI_API_KEY to .env

# For the database tools:
docker compose up -d
# schema, seed data, and the agent_readonly role are created
# automatically from db/seed.sql on first init
```

---

## Usage

```bash
python main.py
```

```text
You: What is 15% of 340?
Agent: [SMART] Answering directly - no tool needed.
       15% of 340 is 51.

You: What is the weather in Tokyo right now?
Agent: [SMART] Tool required - parametric knowledge insufficient.
       [AnyTool] Selected category: weather tools.
       [Tool] get_weather(city=Tokyo, unit=celsius)
       Tokyo is currently 27°C and partly cloudy.

You: What is the latest research on LLM agents?
Agent: [SMART] Tool required - real-time information needed.
       [AnyTool] Selected category: search tools.
       [Tool] web_search(query=latest research LLM agents 2025)
       ...

You: Analyze the sentiment of "I loved this movie, best I've seen all year."
Agent: [SMART] Tool required - specialized NLP task.
       [AnyTool] Selected category: text_intelligence tools.
       [Tool] analyze_text(text="I loved this movie, best I've seen all year.")
       Sentiment: positive. Key topics: movie review, praise.

You: Which department has the highest budget?
Agent: [SMART] Tool required - requires real company data.
       [AnyTool] Selected category: database tools.
       [Tool] query_database(sql="SELECT name, budget FROM departments ORDER BY budget DESC LIMIT 1")
       Engineering, with a budget of $2,500,000.
```

The `text_intelligence` category requires the `ai-text-intelligence-dashboard` Spring Boot backend running on `http://localhost:8080` - see `config.py`'s `backend_base_url`. The `database` category requires Postgres running (`docker compose up -d`) with the `agent_readonly` role created - see `db/seed.sql` and `config.py`'s `agent_db_dsn`.

---

## Implementation Plan

| Concept | Source Paper | Status |
| --- | --- | --- |
| Self-awareness before tool calling | SMART (ACL 2025) | [x] |
| Hierarchical tool filtering | AnyTool (ICML 2024) | [x] |
| Self-reflection on failure | AnyTool (ICML 2024) | [x] |
| Tool schemas grouped by category | AnyTool (ICML 2024) | [x] |
| Agent solver loop | AnyTool (ICML 2024) | [x] |
| Parallel tool call handling | AnyTool (ICML 2024) | [x] |
| Real-world API tools (weather, search) | AnyTool (ICML 2024) | [x] |
| Safe expression evaluation | Engineering best practice | [x] |
| Pydantic argument validation + dispatch | Engineering best practice | [x] |
| CLI entry point | Project infrastructure | [x] |
| Backend-connected tools (`text_intelligence`) | Project infrastructure | [x] |
| Database-aware tools (`database`), read-only enforced two ways | Project infrastructure | [x] |

---

## Stack

- Python 3.12
- OpenAI API (`gpt-4o-mini`)
- Pydantic - argument validation
- httpx - async HTTP for weather API and the text_intelligence backend
- duckduckgo-search - web search, no API key required
- Open-Meteo API - weather, no API key required
- ai-text-intelligence-dashboard - Spring Boot backend for text_intelligence tools (analyze, classify, chat)
- PostgreSQL 16 (via Docker Compose) - operations database for the database tools
- `psycopg` - Postgres driver
- `sqlglot` - parses and validates model-generated SQL before it executes

---

## References

This project is a hands-on implementation of concepts from the following peer-reviewed papers. If you use or build on this work, please consider citing them.

```bibtex
@inproceedings{smart2025,
  title     = {SMART: Self-Aware Agent for Tool Overuse Mitigation},
  booktitle = {Findings of ACL 2025},
  year      = {2025},
  url       = {https://arxiv.org/abs/2502.11435}
}

@inproceedings{anytool2024,
  title     = {AnyTool: Self-Reflective, Hierarchical Agents for Large-Scale API Calls},
  booktitle = {ICML 2024},
  year      = {2024},
  url       = {https://arxiv.org/abs/2402.04253}
}
```
