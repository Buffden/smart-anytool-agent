"""Shared eval plumbing: the two pipelines and per-question cost counters.

Importing this module patches the OpenAI client and agent.dispatch so every
LLM call, token and tool call is counted. Counters are thread-local, so
questions can run in parallel without mixing their numbers.
"""
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from openai.resources.chat.completions import Completions  # noqa: E402

import agent  # noqa: E402
import retriever  # noqa: E402
from smart import self_awareness_check  # noqa: E402


class Counters(threading.local):
    def __init__(self):
        self.reset()

    def reset(self):
        self.enabled = True
        self.llm_calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.tool_calls = []


counters = Counters()

_original_create = Completions.create
_original_dispatch = agent.dispatch


def _counting_create(self, *args, **kwargs):
    response = _original_create(self, *args, **kwargs)
    if counters.enabled:
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


def measure(pipeline: str, question: str) -> dict:
    """Run one question through one pipeline and return its answer and costs."""
    counters.reset()
    start = time.perf_counter()
    try:
        answer, gate_needs_tool = PIPELINES[pipeline](question)
        error = None
    except Exception as exc:
        answer, gate_needs_tool, error = "", None, repr(exc)
    latency = time.perf_counter() - start

    return {
        "pipeline": pipeline,
        "answer": answer,
        "gate_needs_tool": gate_needs_tool,
        "tool_calls": list(counters.tool_calls),
        "n_tool_calls": len(counters.tool_calls),
        "llm_calls": counters.llm_calls,
        "tokens": counters.prompt_tokens + counters.completion_tokens,
        "latency_s": round(latency, 3),
        "error": error,
    }


@contextmanager
def uncounted():
    """Wrap LLM calls that are not part of the pipeline, like grading."""
    counters.enabled = False
    try:
        yield
    finally:
        counters.enabled = True


def change(before, after):
    if not before:
        return "n/a"
    return f"{100 * (after - before) / before:+.1f}%"
