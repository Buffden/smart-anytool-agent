import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evals"))

import graders  # noqa: E402
import harness  # noqa: E402
from fetch_benchmarks import parse_item  # noqa: E402
from run_benchmark_eval import build_summary  # noqa: E402


# helpers

def make_judge_response(text: str) -> MagicMock:
    message = MagicMock()
    message.content = text
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


def make_row(pipeline, correct, n_tool_calls=0, gate_needs_tool=None, benchmark="gsm8k"):
    return {
        "benchmark": benchmark, "run": 1, "id": "q1", "pipeline": pipeline,
        "answer": "", "correct": correct, "n_tool_calls": n_tool_calls,
        "gate_needs_tool": gate_needs_tool, "llm_calls": 1, "tokens": 100,
        "latency_s": 1.0, "error": None,
    }


# fetch_benchmarks.parse_item

def test_parse_item_extracts_question_and_gold():
    item = {
        "input": "### Task\nHow many eggs?\n### Reasoning Steps\n",
        "output": "16 - 3 = 13\n### Final Response\n13",
    }
    assert parse_item(item) == ("How many eggs?", "13")


# graders.last_number

def test_last_number_takes_the_final_number():
    assert graders.last_number("She sells 9 eggs, so she makes $18 per day.") == 18

def test_last_number_ignores_thousands_commas():
    assert graders.last_number("The total is 14,104,692.") == 14104692

def test_last_number_handles_decimals_and_negatives():
    assert graders.last_number("Change is -2.5 degrees") == -2.5

def test_last_number_returns_none_without_digits():
    assert graders.last_number("no idea") is None


# graders.grade_gsm8k

def test_gsm8k_numeric_match_skips_the_judge():
    with patch("graders.client.chat.completions.create") as create:
        assert graders.grade_gsm8k("She makes $18 every day.", "18", "gpt-4o") == (True, "numeric")
    create.assert_not_called()

def test_gsm8k_falls_back_to_judge_on_mismatch():
    with patch("graders.client.chat.completions.create", return_value=make_judge_response("wrong")):
        assert graders.grade_gsm8k("The answer is 20.", "18", "gpt-4o") == (False, "judge")

def test_gsm8k_unclear_judge_verdict_is_unparsed():
    with patch("graders.client.chat.completions.create", return_value=make_judge_response("maybe")):
        assert graders.grade_gsm8k("I could not solve it.", "18", "gpt-4o") == (None, "unparsed")


# graders.grade_freshqa

def test_freshqa_exact_match_is_case_insensitive():
    with patch("graders.client.chat.completions.create") as create:
        assert graders.grade_freshqa("canada", "Canada", "gpt-4o") == (True, "exact")
    create.assert_not_called()

def test_freshqa_uses_judge_for_paraphrases():
    with patch("graders.client.chat.completions.create", return_value=make_judge_response("Correct")):
        assert graders.grade_freshqa("The artist is from Canada.", "Canada", "gpt-4o") == (True, "judge")

# harness.uncounted

def test_uncounted_pauses_counting_and_restores_it():
    harness.counters.reset()
    with harness.uncounted():
        assert harness.counters.enabled is False
    assert harness.counters.enabled is True

def test_uncounted_restores_counting_after_an_error():
    harness.counters.reset()
    try:
        with harness.uncounted():
            raise RuntimeError("judge failed")
    except RuntimeError:
        pass
    assert harness.counters.enabled is True


# run_benchmark_eval.build_summary

def test_summary_reports_tool_calls_per_question_and_accuracy():
    rows = [make_row("baseline", True, 2), make_row("baseline", False, 0)]
    section = build_summary(rows)["gsm8k"]["baseline"]
    assert section["tool_calls_per_question"] == 1.0
    assert section["accuracy_pct"] == 50.0

def test_summary_splits_smart_accuracy_by_gate_decision():
    rows = [
        make_row("baseline", True, 1),
        make_row("smart", True, 0, gate_needs_tool=False),
        make_row("smart", False, 1, gate_needs_tool=True),
    ]
    section = build_summary(rows)["gsm8k"]
    assert section["smart"]["gate_answered_directly_pct"] == 50.0
    assert section["smart"]["accuracy_when_answered_directly_pct"] == 100.0
    assert section["smart"]["accuracy_when_routed_to_tools_pct"] == 0.0
    assert "delta_smart_vs_baseline" in section

def test_summary_attaches_paper_rows_only_for_freshqa():
    rows = [make_row("baseline", True, benchmark="freshqa"), make_row("baseline", True)]
    summary = build_summary(rows)
    assert "paper_reference" in summary["freshqa"]
    assert "paper_reference" not in summary["gsm8k"]
