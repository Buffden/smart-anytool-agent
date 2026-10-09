"""Phase 12: run the SMART gate on the paper's own test sets.

Benchmarks (fetched by evals/fetch_benchmarks.py, the paper's exact questions):
  gsm8k:   1319 questions, out-of-distribution set in the paper, uses calculator
  freshqa: 100 questions, the paper's "Time" domain, uses web_search

Each question runs through both pipelines (baseline and smart, see harness.py)
and is graded like the paper (cheap match, then a gpt-4o judge). Rows are
appended to a JSONL file as they finish, so a long run can be resumed.

Usage (from the project root):
  venv/bin/python evals/run_benchmark_eval.py --limit 2 --runs 1         # smoke test
  venv/bin/python evals/run_benchmark_eval.py --runs 3                   # full run
  venv/bin/python evals/run_benchmark_eval.py --resume evals/results/benchmark_<ts>.jsonl --runs 3
"""
import argparse
import csv
import json
import random
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from harness import PIPELINES, ROOT, change, measure
from graders import GRADERS

BENCH_DIR = Path(__file__).parent / "benchmarks"
RESULTS_DIR = Path(__file__).parent / "results"

# Paper Table 3, GPT-4o-mini on the "Time" (FreshQA) test split.
# The paper reports no GPT-4o-mini numbers for GSM8K.
PAPER_ROWS = {
    "freshqa": {
        "paper gpt-4o-mini reasoning prompt": {"tool_calls_per_question": 0.00, "accuracy_pct": 44.00},
        "paper gpt-4o-mini tool prompt": {"tool_calls_per_question": 1.06, "accuracy_pct": 56.00},
    },
}

SPOTCHECK_SIZE = 20


def load(benchmark: str, limit: int | None) -> list[dict]:
    path = BENCH_DIR / f"{benchmark}.jsonl"
    if not path.exists():
        raise SystemExit(f"{path} not found, run evals/fetch_benchmarks.py first")
    items = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return items[:limit] if limit else items


def run_one(benchmark: str, item: dict, pipeline: str, run: int, judge_model: str) -> dict:
    result = measure(pipeline, item["question"])
    try:
        correct, grade_method = GRADERS[benchmark](result["answer"], item["gold"], judge_model)
    except Exception as exc:
        correct, grade_method = None, f"grader error: {exc!r}"
    return {
        "benchmark": benchmark,
        "run": run,
        "id": item["id"],
        "question": item["question"],
        "gold": item["gold"],
        **result,
        "correct": correct,
        "grade_method": grade_method,
    }


def summarize(rows: list[dict]) -> dict:
    def pct(num, den):
        return round(100 * num / den, 1) if den else None

    graded = [r for r in rows if r["correct"] is not None]
    direct = [r for r in rows if r["gate_needs_tool"] is False]
    routed = [r for r in rows if r["gate_needs_tool"] is True]

    summary = {
        "questions": len(rows),
        "tool_calls_per_question": round(sum(r["n_tool_calls"] for r in rows) / len(rows), 2),
        "accuracy_pct": pct(sum(r["correct"] for r in graded), len(graded)),
        "ungraded": len(rows) - len(graded),
        "llm_calls": sum(r["llm_calls"] for r in rows),
        "tokens": sum(r["tokens"] for r in rows),
        "mean_latency_s": round(sum(r["latency_s"] for r in rows) / len(rows), 2),
        "errors": sum(r["error"] is not None for r in rows),
    }
    if direct or routed:
        summary["gate_answered_directly_pct"] = pct(len(direct), len(direct) + len(routed))
        summary["accuracy_when_answered_directly_pct"] = pct(
            sum(bool(r["correct"]) for r in direct), sum(r["correct"] is not None for r in direct))
        summary["accuracy_when_routed_to_tools_pct"] = pct(
            sum(bool(r["correct"]) for r in routed), sum(r["correct"] is not None for r in routed))
    return summary


def build_summary(rows: list[dict]) -> dict:
    grouped = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row["benchmark"]][row["pipeline"]].append(row)

    summary = {}
    for benchmark, by_pipeline in grouped.items():
        section = {p: summarize(r) for p, r in by_pipeline.items()}
        if "baseline" in section and "smart" in section:
            b, s = section["baseline"], section["smart"]
            section["delta_smart_vs_baseline"] = {
                "tool_calls_per_question": change(b["tool_calls_per_question"], s["tool_calls_per_question"]),
                "tokens": change(b["tokens"], s["tokens"]),
                "mean_latency_s": change(b["mean_latency_s"], s["mean_latency_s"]),
                "accuracy_pts": (round(s["accuracy_pct"] - b["accuracy_pct"], 1)
                                 if b["accuracy_pct"] is not None and s["accuracy_pct"] is not None else None),
            }
        if benchmark in PAPER_ROWS:
            section["paper_reference"] = PAPER_ROWS[benchmark]
        summary[benchmark] = section
    return summary


def write_spotcheck(rows: list[dict], path: Path) -> None:
    """Sample FreshQA rows for hand-checking the judge and tagging answer drift."""
    candidates = [r for r in rows if r["benchmark"] == "freshqa" and r["run"] == 1]
    if not candidates:
        return
    sample = random.Random(42).sample(candidates, min(SPOTCHECK_SIZE, len(candidates)))
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "pipeline", "question", "gold", "answer", "judge_correct",
                         "human_correct", "if_wrong_is_it_drift"])
        for r in sample:
            writer.writerow([r["id"], r["pipeline"], r["question"], r["gold"],
                             r["answer"].replace("\n", " "), r["correct"], "", ""])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", choices=["gsm8k", "freshqa", "all"], default="all")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--limit", type=int, default=None, help="first N questions per benchmark")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--judge-model", default="gpt-4o")
    parser.add_argument("--resume", type=Path, default=None, help="JSONL from an earlier run to continue")
    args = parser.parse_args()

    benchmarks = ["gsm8k", "freshqa"] if args.benchmark == "all" else [args.benchmark]

    RESULTS_DIR.mkdir(exist_ok=True)
    out = args.resume.resolve() if args.resume else RESULTS_DIR / f"benchmark_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
    done = set()
    if out.exists():
        for line in out.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                done.add((r["benchmark"], r["run"], r["pipeline"], r["id"]))
        print(f"resuming {out.relative_to(ROOT)}: {len(done)} rows already done")

    tasks = [
        (benchmark, item, pipeline, run)
        for benchmark in benchmarks
        for item in load(benchmark, args.limit)
        for run in range(1, args.runs + 1)
        for pipeline in PIPELINES
        if (benchmark, run, pipeline, item["id"]) not in done
    ]
    print(f"{len(tasks)} question runs to do, {args.workers} workers -> {out.relative_to(ROOT)}")

    # workers only run questions; this thread does all the writing
    with ThreadPoolExecutor(max_workers=args.workers) as pool, out.open("a") as f:
        futures = [pool.submit(run_one, *task, args.judge_model) for task in tasks]
        for finished, future in enumerate(as_completed(futures), start=1):
            row = future.result()
            f.write(json.dumps(row) + "\n")
            f.flush()
            mark = {True: "ok", False: "WRONG", None: "?"}[row["correct"]]
            print(f"  {finished}/{len(tasks)} [{row['benchmark']} {row['pipeline']} run {row['run']}] "
                  f"{row['id']} tools={row['n_tool_calls']} {row['latency_s']:.1f}s {mark}")

    rows = [json.loads(line) for line in out.read_text().splitlines() if line.strip()]
    rows = [r for r in rows if r["benchmark"] in benchmarks]
    summary = build_summary(rows)

    summary_path = out.with_name(out.stem + "_summary.json")
    summary_path.write_text(json.dumps(summary, indent=2))
    spotcheck_path = out.with_name(out.stem + "_spotcheck.csv")
    write_spotcheck(rows, spotcheck_path)

    print(json.dumps(summary, indent=2))
    print(f"\nrows:      {out.relative_to(ROOT)}")
    print(f"summary:   {summary_path.relative_to(ROOT)}")
    if spotcheck_path.exists():
        print(f"spotcheck: {spotcheck_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
