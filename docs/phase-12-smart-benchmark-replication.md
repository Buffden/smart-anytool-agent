# Phase 12 - SMART Benchmark Replication

## Summary

Test the SMART gate on the paper's own test questions with the paper's own metrics and grading, so our results sit next to theirs.

---

## Description

This is a replication, not a competition. The paper fine-tunes models; we use a prompt on `gpt-4o-mini`. We report whatever comes out.

**Benchmarks (the paper's exact questions)**

The authors released their test sets in [Open-SMARTAgent](https://github.com/qiancheng0/Open-SMARTAgent) under `data_inference/`. `evals/fetch_benchmarks.py` downloads them and keeps only the question and gold answer.

- **GSM8K:** all 1319 questions (`ood_gsm_tool_prompt.json`). Out-of-distribution set in the paper. Our tool: `calculator`.
- **FreshQA:** the paper's 100 "Time" questions (`domain_time_tool_prompt.json`). In-domain set in the paper. Our tool: `web_search`.

**Metrics (same as the paper)**

- Tool calls per question ("Tool Used" in the paper)
- Accuracy

Also recorded: LLM calls, tokens, latency, how often the gate answered directly, and accuracy split by the gate's decision.

**Grading (same as the paper)**

The paper's `evaluate/inference_eval_{math,time}.py` tries a cheap match first and asks a `gpt-4o` judge only when that fails. We do the same, with their judge prompts copied verbatim into `prompts/judge_math.txt` and `prompts/judge_time.txt`.

- GSM8K: last number in the answer equals the gold number, else the math judge.
- FreshQA: case-insensitive exact match, else the time judge.

Judge calls are excluded from the cost counters.

---

## What the Paper Reports

GPT-4o-mini appears only in the paper's in-domain table (Table 3). There is **no GPT-4o-mini row for GSM8K**.

**FreshQA ("Time"), GPT-4o-mini, Table 3**

| Setting | Tool calls per question | Accuracy |
| --- | --- | --- |
| Reasoning prompt (no tools) | 0.00 | 44.00% |
| Tool prompt | 1.06 | 56.00% |

**GSM8K, Table 4 (other models, context only)**

| Setting | Model | Tool calls per question | Accuracy |
| --- | --- | --- | --- |
| Base model tool prompt | Llama-3.1-8B | 2.53 | 83.17% |
| SMARTAgent | Llama-3.1-8B | 0.76 | 83.40% |
| Base model tool prompt | Mistral-7B | 3.56 | 55.34% |
| SMARTAgent | Mistral-7B | 0.45 | 58.98% |

So FreshQA is the one true apples-to-apples comparison. For GSM8K we compare our baseline with our smart pipeline only, and treat the paper's numbers as loose context.

---

## Known Caveats

- **FreshQA answers have drifted.** The gold answers date from about 2024 ("the artist who *recently* broke the Spotify record"). Live search today returns newer facts, so some right answers will be graded wrong. The spot-check below separates real errors from drift.
- **Different tools.** The paper's math tool runs Python; ours is an arithmetic-only `calculator`. The paper's search engine and date also differ from our DuckDuckGo search.
- **Different agent.** Our baseline is the full AnyTool pipeline (tool filter, agent loop, self-reflection retry), not the paper's single tool prompt.
- **Search fix.** The old `duckduckgo-search` package silently returned no results. It was replaced with `ddgs` before any Phase 12 run, so these runs use working search.

---

## How to Run

From the project root:

1. `venv/bin/python evals/fetch_benchmarks.py` (already done, the JSONL files are committed)
2. Smoke test: `venv/bin/python evals/run_benchmark_eval.py --limit 2 --runs 1`
3. Full run: `venv/bin/python evals/run_benchmark_eval.py --runs 3`
4. If it stops part way, continue with `--resume evals/results/benchmark_<timestamp>.jsonl --runs 3`

The full run is 1419 questions, two pipelines, three runs. Expect roughly $4 to $5 and a few hours with the default 4 workers. More workers is faster but DuckDuckGo may start rate limiting the FreshQA searches.

Each run writes three files to `evals/results/`:

- `benchmark_<timestamp>.jsonl` every graded row, written as it finishes
- `benchmark_<timestamp>_summary.json` the numbers for the results table
- `benchmark_<timestamp>_spotcheck.csv` 20 random FreshQA rows to grade by hand

---

## Spot-Check

Open the spot-check CSV and, for each row, fill in:

- `human_correct`: is the answer right, judged against the gold?
- `if_wrong_is_it_drift`: if wrong, is it because the world changed since the gold was written?

This gives two numbers: how often our judge agrees with a human, and how much of the FreshQA gap is drift rather than the agent.

---

## Results

Not run yet. Fill in from the summary file after the full run:

| Benchmark | Row | Tool calls per question | Accuracy |
| --- | --- | --- | --- |
| FreshQA | Paper, GPT-4o-mini tool prompt | 1.06 | 56.00% |
| FreshQA | Our baseline | | |
| FreshQA | Our smart | | |
| GSM8K | Our baseline | | |
| GSM8K | Our smart | | |

---

## Rules

- Don't change the gate prompt based on test questions.
- Report bad results too.

---

## Dependencies

- Phase 4, Phase 11

---

## Out of Scope

- MATH (the paper's math tool runs Python code, ours only does arithmetic), IN3 (needs an ask-user tool), MINTQA
- Fine-tuning a model
