"""A/B eval of the SMART self-awareness gate.

Runs every question in smart_dataset.jsonl through two pipelines:
  baseline: retriever.run(question)            (AnyTool pipeline, no gate)
  smart:    self_awareness_check -> direct answer or retriever.run

and reports tool calls, LLM calls, tokens, latency and accuracy for each.

Usage (from the project root):
  venv/bin/python evals/run_smart_eval.py [--runs N] [--limit N]
"""
import argparse
import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from openai.resources.chat.completions import Completions  # noqa: E402

import agent  # noqa: E402
import retriever  # noqa: E402
from smart import self_awareness_check  # noqa: E402

DATASET = Path(__file__).parent / "smart_dataset.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"


class Counters:
    def __init__(self):
        self.reset()

    def reset(self):
        self.llm_calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.tool_calls = []


counters = Counters()

_original_create = Completions.create
_original_dispatch = agent.dispatch


def _counting_create(self, *args, **kwargs):
    response = _original_create(self, *args, **kwargs)
    counters.llm_calls += 1
    if response.usage:
        counters.prompt_tokens += response.usage.prompt_tokens
        counters.completion_tokens += response.usage.completion_tokens
    return response


def _counting_dispatch(name, raw_args):
    counters.tool_calls.append(name)
    return _original_dispatch(name, raw_args)


Completions.create = _counting_create
agent.dispatch = _counting_dispatch


def run_baseline(question: str) -> tuple[str, bool | None]:
    return retriever.run(question), None


def run_smart(question: str) -> tuple[str, bool | None]:
    gate = self_awareness_check(question)
    if not gate["needs_tool"]:
        return gate["answer"] or "", False
    return retriever.run(question), True


PIPELINES = {"baseline": run_baseline, "smart": run_smart}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower())


def is_correct(answer: str, gold: list[str] | None) -> bool | None:
    if gold is None:
        return None
    norm = normalize(answer)
    no_commas = norm.replace(",", "")
    return any(g.lower() in norm or g.lower().replace(",", "") in no_commas for g in gold)


def evaluate(items: list[dict], pipeline: str) -> list[dict]:
    rows = []
    for item in items:
        counters.reset()
        start = time.perf_counter()
        try:
            answer, gate_needs_tool = PIPELINES[pipeline](item["question"])
            error = None
        except Exception as exc:
            answer, gate_needs_tool, error = "", None, repr(exc)
        latency = time.perf_counter() - start

        rows.append({
            "id": item["id"],
            "kind": item["kind"],
            "needs_tool": item["needs_tool"],
            "pipeline": pipeline,
            "answer": answer,
            "correct": is_correct(answer, item["gold"]),
            "gate_needs_tool": gate_needs_tool,
            "tool_calls": list(counters.tool_calls),
            "n_tool_calls": len(counters.tool_calls),
            "llm_calls": counters.llm_calls,
            "tokens": counters.prompt_tokens + counters.completion_tokens,
            "latency_s": round(latency, 3),
            "error": error,
        })
        mark = {True: "ok", False: "WRONG", None: "-"}[rows[-1]["correct"]]
        print(f"  [{pipeline}] {item['id']} tools={rows[-1]['n_tool_calls']} "
              f"llm={counters.llm_calls} {latency:.1f}s {mark}")
    return rows


def summarize(rows: list[dict]) -> dict:
    def pct(num, den):
        return round(100 * num / den, 1) if den else None

    no_tool = [r for r in rows if not r["needs_tool"]]
    needs_tool = [r for r in rows if r["needs_tool"]]
    graded = [r for r in rows if r["correct"] is not None]

    return {
        "questions": len(rows),
        "total_tool_calls": sum(r["n_tool_calls"] for r in rows),
        "unnecessary_tool_calls": sum(r["n_tool_calls"] for r in no_tool),
        "no_tool_questions_with_tool_use_pct": pct(sum(r["n_tool_calls"] > 0 for r in no_tool), len(no_tool)),
        "needs_tool_questions_missing_tool_pct": pct(sum(r["n_tool_calls"] == 0 for r in needs_tool), len(needs_tool)),
        "accuracy_pct": pct(sum(r["correct"] for r in graded), len(graded)),
        "accuracy_by_kind_pct": {
            kind: pct(sum(r["correct"] for r in g), len(g))
            for kind in sorted({r["kind"] for r in graded})
            for g in [[r for r in graded if r["kind"] == kind]]
        },
        "llm_calls": sum(r["llm_calls"] for r in rows),
        "tokens": sum(r["tokens"] for r in rows),
        "mean_latency_s": round(sum(r["latency_s"] for r in rows) / len(rows), 2),
        "errors": sum(r["error"] is not None for r in rows),
    }


def gate_metrics(rows: list[dict]) -> dict:
    gated = [r for r in rows if r["pipeline"] == "smart" and r["gate_needs_tool"] is not None]
    tp = sum(r["gate_needs_tool"] and r["needs_tool"] for r in gated)
    tn = sum(not r["gate_needs_tool"] and not r["needs_tool"] for r in gated)
    fp = sum(r["gate_needs_tool"] and not r["needs_tool"] for r in gated)
    fn = sum(not r["gate_needs_tool"] and r["needs_tool"] for r in gated)
    return {
        "gate_accuracy_pct": round(100 * (tp + tn) / len(gated), 1) if gated else None,
        "true_tool": tp, "true_direct": tn,
        "false_tool (overuse)": fp, "false_direct (missed tool)": fn,
    }


def change(before, after):
    if not before:
        return "n/a"
    return f"{100 * (after - before) / before:+.1f}%"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    items = [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]
    if args.limit:
        items = items[: args.limit]

    all_rows = []
    for run in range(1, args.runs + 1):
        for pipeline in PIPELINES:
            print(f"run {run}/{args.runs} pipeline={pipeline}")
            for row in evaluate(items, pipeline):
                row["run"] = run
                all_rows.append(row)

    by_pipeline = defaultdict(list)
    for row in all_rows:
        by_pipeline[row["pipeline"]].append(row)

    summary = {p: summarize(rows) for p, rows in by_pipeline.items()}
    summary["gate"] = gate_metrics(all_rows)
    b, s = summary["baseline"], summary["smart"]
    summary["delta_smart_vs_baseline"] = {
        "total_tool_calls": change(b["total_tool_calls"], s["total_tool_calls"]),
        "unnecessary_tool_calls": change(b["unnecessary_tool_calls"], s["unnecessary_tool_calls"]),
        "llm_calls": change(b["llm_calls"], s["llm_calls"]),
        "tokens": change(b["tokens"], s["tokens"]),
        "mean_latency_s": change(b["mean_latency_s"], s["mean_latency_s"]),
        "accuracy_pts": (round(s["accuracy_pct"] - b["accuracy_pct"], 1)
                         if b["accuracy_pct"] is not None and s["accuracy_pct"] is not None else None),
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"smart_eval_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(json.dumps({"summary": summary, "rows": all_rows}, indent=2))

    print(json.dumps(summary, indent=2))
    print(f"\nfull results: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
