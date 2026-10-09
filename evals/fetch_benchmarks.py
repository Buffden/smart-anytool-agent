"""Download the SMART paper's released test sets and save them as plain JSONL.

Source: https://github.com/qiancheng0/Open-SMARTAgent (data_inference/)
  ood_gsm_tool_prompt.json     -> evals/benchmarks/gsm8k.jsonl   (1319 questions)
  domain_time_tool_prompt.json -> evals/benchmarks/freshqa.jsonl (100 questions)

Each source item has the paper's prompt in "instruction", the question in
"input" (between "### Task" and "### Reasoning Steps") and the gold answer
after "### Final Response" in "output". We keep only the question and gold.

Usage (from the project root):
  venv/bin/python evals/fetch_benchmarks.py
"""
import json
from pathlib import Path

import httpx

BASE_URL = "https://raw.githubusercontent.com/qiancheng0/Open-SMARTAgent/main/data_inference"
SOURCES = {
    "gsm8k": "ood_gsm_tool_prompt.json",
    "freshqa": "domain_time_tool_prompt.json",
}
OUT_DIR = Path(__file__).parent / "benchmarks"


def parse_item(item: dict) -> tuple[str, str]:
    question = item["input"].split("### Task", 1)[1].split("### Reasoning Steps", 1)[0].strip()
    gold = item["output"].split("### Final Response", 1)[1].strip()
    return question, gold


def main():
    OUT_DIR.mkdir(exist_ok=True)
    for name, filename in SOURCES.items():
        response = httpx.get(f"{BASE_URL}/{filename}", timeout=60, follow_redirects=True)
        response.raise_for_status()

        lines = []
        for i, item in enumerate(response.json(), start=1):
            question, gold = parse_item(item)
            lines.append(json.dumps({"id": f"{name}-{i:04d}", "question": question, "gold": gold}))

        out = OUT_DIR / f"{name}.jsonl"
        out.write_text("\n".join(lines) + "\n")
        print(f"{name}: {len(lines)} questions -> {out.relative_to(Path.cwd()) if out.is_relative_to(Path.cwd()) else out}")


if __name__ == "__main__":
    main()
