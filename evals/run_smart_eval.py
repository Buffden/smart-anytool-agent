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
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from harness import PIPELINES, ROOT, change, measure

DATASET = Path(__file__).parent / "smart_dataset.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"


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
        result = measure(pipeline, item["question"])
        rows.append({
            "id": item["id"],
            "kind": item["kind"],
            "needs_tool": item["needs_tool"],
            **result,
            "correct": is_correct(result["answer"], item["gold"]),
        })
        mark = {True: "ok", False: "WRONG", None: "-"}[rows[-1]["correct"]]
        print(f"  [{pipeline}] {item['id']} tools={result['n_tool_calls']} "
              f"llm={result['llm_calls']} {result['latency_s']:.1f}s {mark}")
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
