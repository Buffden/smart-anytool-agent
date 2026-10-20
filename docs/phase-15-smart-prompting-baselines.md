# Phase 15 - SMART Prompting Baselines

## Summary

Run the SMART paper's own prompting baselines (Qian et al., "SMART: Self-Aware Agent for Tool Overuse Mitigation", arXiv 2502.11435) on GPT models, exactly as the paper's code runs them, across all five of its test sets. This gives Phase 12's results a true like-for-like anchor, and builds the loop, tools, and graders that Phase 16 reuses with open models.

API only: OpenAI and Serper, run from the laptop.

---

## Why This Phase Exists

Phase 12 used the paper's questions, metrics, and judge, but not the paper's method:

- **Method.** It tested our AnyTool pipeline with and without our prompt gate. The paper's baselines are a single prompt, with tools written as plain text.
- **Prompt.** `evals/fetch_benchmarks.py` kept only the question and gold answer and threw away the paper's instruction text.
- **Tools.** Arithmetic-only `calculator` instead of running Python, and DuckDuckGo instead of Serper (Google).
- **Grading.** The GSM8K quick check matched the last number in the answer. The paper requires an exact match on the whole final response.
- **Runs.** 3 runs averaged. The paper does one run at near-zero temperature.
- **Coverage.** 2 of the paper's 5 test sets.

This phase fixes all of that for two new pipelines, `paper_reasoning_prompt` and `paper_tool_prompt`, and leaves `baseline` and `smart` untouched.

---

## The Paper's Test Sets

All of these come from `Open-SMARTAgent/data_inference/`. Each one has a `_tool_prompt.json` file (base-model prompts) and a `_smart.json` file (SMARTAgent prompts, used in Phase 16).

| Test set | Domain | Split | Questions | Tools available |
| --- | --- | --- | --- | --- |
| MATH | Math | In-domain | 400 | Code |
| FreshQA | Time | In-domain | 100 | Search |
| IN3 | Intention | In-domain | 100 | AskUser, Search (with links) |
| GSM8K | Math | Out-of-distribution | 1319 | Code |
| MINTQA | Time | Out-of-distribution | 97 | Search |

---

## Paper Reference Numbers

From the paper's Table 3. Each cell gives tool calls per question, then accuracy (%). For IN3, accuracy is Missing Details Recovery at levels 3 and 2, followed by Summarized Intention Coverage. The paper has no GPT rows for GSM8K or MINTQA.

| Model | Setting | MATH | FreshQA | IN3 |
| --- | --- | --- | --- | --- |
| GPT-4o-mini | Reasoning prompt | 0.00, 73.00 | 0.00, 44.00 | 0.00, 45.35 / 32.41, n/a |
| GPT-4o-mini | Tool prompt | 2.55, 54.50 | 1.06, 56.00 | 1.91, 50.00 / 26.90, 76.44 |
| GPT-4o | Reasoning prompt | 0.00, 79.50 | 0.00, 47.00 | 0.00, 38.37 / 28.54, n/a |
| GPT-4o | Tool prompt | 0.27, 79.25 | 1.01, 65.00 | 1.17, 40.70 / 15.61, 86.80 |

Copy any other row you need straight from the paper. Don't reconstruct it from memory.

---

## How the Paper's Code Works (Source of Truth)

These notes come from `inference/inference_tool_prompt.py`, `inference/inference_normal_vllm.py`, `inference/utils_serper.py`, `inference/utils_code.py`, `inference/utils_askuser.py`, and `evaluate/inference_eval_{math,time,intention}.py`. Read those files yourself before building. Where these notes and the code disagree, the code wins.

**Data items**

- Each item has an `instruction` (principles, tool syntax, output guidelines, worked examples), an `input` (a `### Task` block followed by an empty `### Reasoning Steps`), and an `output` (the gold answer after `### Final Response`).

**Tool prompt loop**

- Message layout: for Llama, the instruction is the system message and the input is the user message. For Mistral, both are joined into one user message.
- At most 10 rounds. Temperature 0.000001, 4096 max tokens, and **no stop sequences**.
- Parse each reply: find the earliest tool marker (`AskUser(`, `Search(`, or an opening Python code fence). Everything before it is a reasoning step. The tool call is the content of the first balanced parentheses, or the first fenced Python block. Anything after the tool call, including made-up tool output, is thrown away.
- With no tool marker, `Final Answer:` ends the question. With neither, the whole reply becomes a reasoning step and the loop continues.
- After a tool call, the reasoning, the tool call, and a `- Tool Output: ...` line are appended to the **same user message**, followed by `### Continue your reasoning`. There are no assistant turns.
- After round 10, the final response is set to a fixed "exceeded maximum step time" text, which the judge marks wrong.

**Reasoning prompt**

- One call with no tools. The reply must contain `### Final Response`. If it doesn't, the answer counts as wrong. There is no retry.

**Tools**

- **Search:** Serper's Google search, restricted to the past year (`qdr:y`), top 3 results in the tool prompt loop. Each result is a numbered title with a `- Date:` line (or a `- Link:` line for IN3) and a `- Snippet:` line. Results missing the date (or link) are **skipped**. It retries up to 10 times if no results come back.
- **Code:** runs the snippet with Python, with a 20 second timeout, and cuts output longer than 256 characters down to its first and last 128. Earlier successful code is run again in front of each new snippet (minus comment lines and lines starting with `print(`), so variables carry over.
- **AskUser:** `gpt-4o` at temperature 0 plays the user, using a short system prompt that has it answer as someone with preferences about the task. The prompt is in `utils_askuser.py`. Copy it verbatim.

**Grading**

- **MATH, GSM8K, FreshQA, MINTQA:** the prediction is the final response with newlines turned into spaces, and the gold is the text after `### Final Response`. A case-insensitive exact match is correct straight away. Otherwise the `gpt-4o` judge decides, at near-zero temperature, using the paper's math or time prompt (already in `prompts/judge_math.txt` and `prompts/judge_time.txt`).
- **IN3:** two `gpt-4o` judge prompts in `inference_eval_intention.py`. One checks whether each missing detail was covered by the agent's questions (Missing Details Recovery, levels 3 and 2). The other checks whether the final summary covers each preference the user stated (Summarized Intention Coverage).
- Questions whose loop crashed are left out of the accuracy.
- **Tool Used** is the number of tool steps in a question's trace, averaged over questions.

---

## Known Gaps in the Paper's Released Code

Record each of these as a deviation if you work around it, so nobody reads it as a silent fix.

1. **GSM8K final marker.** The GSM8K tool prompt tells the model to finish with `### Final Response`, but the tool prompt loop only recognizes `Final Answer:`. Run as released, every GSM8K question would hit the 10-round cap. Decision: recognize both, and report how many answers ended on each.
2. **Reasoning prompt text isn't released.** `inference_normal_vllm.py` expects a data file that isn't in `data_inference/`. Decision: write a chain-of-thought instruction that's the tool prompt's instruction with the tool sections removed, keep the `### Final Response` ending, and commit it so it can be reviewed.

---

## Decisions to Make (and Write Down)

Each one has a recommended default. Change it if you disagree, but record why.

- **Search backend.** Serper, matching the paper. DuckDuckGo results have no dates, and the paper's formatter drops undated results. FreshQA, MINTQA, and IN3 together are about 300 questions per setting, so check that the free tier covers every setting you run, or budget for credits. The key goes in `.env`.
- **Where generated code runs.** A throwaway Docker container with no network, a memory limit, and the 20 second timeout. The paper runs model-written code directly on the machine.
- **Message layout for GPT models.** The code doesn't show how the GPT rows were sent. Default: system plus user, like Llama. Run 10 FreshQA questions both ways and note whether it matters.
- **Model versions.** Use dated snapshots where they're still served, and record the exact id the API returns.
- **Runs.** One run per question at the paper's temperature. A second run is only a stability check.
- **Model-call plug.** Write the loop so the model call can be swapped out. Phase 16 plugs vLLM in here.

---

## Tasks

### Task 1 - Keep the paper's full prompt items, for all five test sets
- Fetch both the `_tool_prompt.json` and `_smart.json` files for all five sets. Keep the instruction, input, and output verbatim, next to the question and gold that Phase 12 already reads.
- **Done when:** item counts match the table above, a byte-for-byte check against the paper's JSON passes, and Phase 12's loader still works unchanged.

### Task 2 - Step parser
- Returns the same steps as the paper's `parse_steps`, after the same header cleanup. It recognizes both final markers (gap 1) and reports which one matched.
- **Done when:** unit tests cover each tool marker, text after a tool call being dropped, nested parentheses inside a query, each final marker, and a reply with neither.

### Task 3 - Search tool
- Serper with the paper's options and formatting. That includes the date/link switch for IN3, skipping undated results, the result count as a parameter (Phase 16 needs 10), and the retry-then-timeout behavior.
- **Done when:** a recorded Serper response produces exactly the paper's text for both the date and link formats, with tests for undated results and empty responses.

### Task 4 - Code tool
- Runs in the container you chose, with the 20 second timeout and the 256 character cut. Carrying earlier code over is a switch (on here; Phase 16's SMART loop turns it off).
- **Done when:** a two-round test shows a variable carrying over when the switch is on and not when it's off, a failing snippet is never kept, and an infinite loop returns the timeout text.

### Task 5 - AskUser tool
- The paper's system and user prompt, copied verbatim, on `gpt-4o` at temperature 0. Calls to it are counted separately from the agent's own calls.
- **Done when:** a test checks the prompt text against the paper's file, and one IN3 item produces a plausible simulated reply.

### Task 6 - Tool prompt pipeline
- The 10-round loop exactly as described above, behind the model-call plug.
- Register it as `paper_tool_prompt` next to `baseline` and `smart`. Let the runner choose which pipelines and which test sets run.
- Save every trace (raw replies and parsed steps).
- **Done when:** a 2-question smoke run on each of the five sets finishes, and the traces read like the paper's examples.

### Task 7 - Reasoning prompt pipeline
- `paper_reasoning_prompt`: one call, using the instruction from gap 2, with no retry.
- **Done when:** a smoke run on each set finishes, and a reply without the final marker is counted wrong.

### Task 8 - Paper-exact grading
- For the four answer-based sets: the paper's exact-match quick check, then the judge. No last-number shortcut. Phase 12's graders stay as they are for `baseline` and `smart`.
- For IN3: both judge prompts, copied verbatim, producing Missing Details Recovery at levels 3 and 2 and Summarized Intention Coverage.
- **Done when:** a test shows "The answer is 18" against gold "18" goes to the judge under paper grading, and the IN3 grader reproduces the paper's verdict on two hand-made examples.

### Task 9 - Runs
- On GPT-4o-mini: the reasoning prompt and the tool prompt, on all five sets.
- On GPT-4o (optional, it costs much more): the same, on the three in-domain sets only, since those are the only ones with GPT-4o rows in the paper.
- **Done when:** a summary file exists for each run.

### Task 10 - Spot-checks
- Fill in Phase 12's spot-check, and a new 20-row spot-check for FreshQA and for MINTQA from this phase.
- Mark each wrong answer as a real error or as out of date. The gold answers are from about 2024 and the searches run in 2026.
- **Done when:** every sheet is filled in, and an "after spot-check" accuracy is reported next to each raw one.

### Task 11 - Write-up
- Fill in the results tables, list every deviation, give the API spend, and say what surprised you.
- Keep the summary files cited here in git (the `.gitignore` exception pattern from Phase 12). Raw traces stay out.
- Tick Phases 12 and 15 in the README.
- **Done when:** someone could rerun any row from this doc alone.

---

## What Counts as a Successful Replication

- **Write down your tolerance before any run.** A reasonable start: tool calls within about 0.3, and accuracy within about 10 points after the spot-check correction for out-of-date answers.
- **If the GPT-4o-mini rows land inside it:** the setup is faithful, and Phase 12's gap to the paper comes from our pipeline and tools, not from the benchmark. Say that explicitly.
- **Rows outside it are findings, not failures.** For each one, name the most likely cause (model snapshot, search results two years later, message layout, a released-code gap) and the evidence for it.

---

## Results

Not run yet. Paper numbers are given as tool calls, accuracy.

**In-domain**

| Model | Setting | MATH | FreshQA | IN3 | Paper (MATH / FreshQA / IN3) |
| --- | --- | --- | --- | --- | --- |
| GPT-4o-mini | Reasoning prompt | | | | 0.00, 73.00 / 0.00, 44.00 / 0.00, 45.35 / 32.41 |
| GPT-4o-mini | Tool prompt | | | | 2.55, 54.50 / 1.06, 56.00 / 1.91, 50.00 / 26.90 |
| GPT-4o | Reasoning prompt (optional) | | | | 0.00, 79.50 / 0.00, 47.00 / 0.00, 38.37 / 28.54 |
| GPT-4o | Tool prompt (optional) | | | | 0.27, 79.25 / 1.01, 65.00 / 1.17, 40.70 / 15.61 |

**Out-of-distribution (no paper rows for GPT models)**

| Model | Setting | GSM8K | MINTQA |
| --- | --- | --- | --- |
| GPT-4o-mini | Reasoning prompt | | |
| GPT-4o-mini | Tool prompt | | |

**Our pipelines (Phase 12, different method and tools, for reference)**

| Pipeline | FreshQA | GSM8K |
| --- | --- | --- |
| baseline | 3.29, 44.1 | 2.41, 84.3 |
| smart | 3.13, 43.9 | 2.37, 83.1 |

---

## Rules

- Don't edit the paper's instruction text, even to fix its typos. Faithful beats tidy.
- Don't tune anything based on test questions.
- Record every deviation from the paper's code, however small.
- Report bad results too.
- Never commit API keys.

---

## Dependencies

- Phase 12 (questions, judge prompts, runner, counters)

---

## Out of Scope

- Open models, SMARTAgent, training, and confidence validation (Phase 16)
- Changing the `baseline` or `smart` pipelines or their graders
