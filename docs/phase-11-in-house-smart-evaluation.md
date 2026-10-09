# Phase 11 - In-House SMART Evaluation

## Summary

Measure what the SMART gate (Phase 4) actually changes in this agent by running the same questions with and without it.

---

## Description

The paper's 24% / 37% numbers come from fine-tuned models on the paper's benchmarks, not from this project. This eval produces our own numbers.

- **baseline:** `retriever.run(question)`, no gate
- **smart:** `self_awareness_check` first, then `retriever.run` only if a tool is needed

Dataset: `evals/smart_dataset.jsonl`, 45 questions (25 knowledge, 10 math, 10 live data), each labeled with whether it needs a tool.

Run: `venv/bin/python evals/run_smart_eval.py --runs 3` (about $0.05).

Raw results: `evals/results/smart_eval_20261009_161745.json`

---

## Results (3 runs, 2026-10-09)

| Question type | Latency (baseline → smart) | Tokens |
| --- | --- | --- |
| Knowledge | 1.55s → 0.79s | -49% |
| Math | 2.20s → 2.90s | +54% |
| Live data | 3.08s → 3.29s | +19% |

- Gate picked correctly 98% of the time. It never skipped a needed tool.
- Accuracy was 100% for both, so no loss, but the questions are too easy to show a gain.
- No drop in unnecessary tool calls: `gpt-4o-mini` already avoids them on easy questions.
- Not comparable to the paper (different models, questions, and metrics). See Phase 12.

---

## Dependencies

- Phase 4, 5, 7, 9

---

## Out of Scope

- Comparing with the paper's numbers (Phase 12)
- Tuning the Phase 4 prompt
