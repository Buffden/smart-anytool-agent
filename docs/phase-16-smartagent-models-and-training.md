# Phase 16 - SMARTAgent Models and Training

## Summary

Finish the SMART paper replication with the parts that need a GPU: the open base models' prompting baselines, the released SMARTAgent checkpoints, our own fine-tuned SMARTAgent, the "normal reasoning trained" baseline, and the confidence validation experiment. Then place our prompt gate (Phases 4, 11, 12) next to all of it and answer whether it behaves more like the paper's tool prompt or like SMARTAgent.

Runs on one rented GPU, reusing Phase 15's loop, tools, and graders.

---

## Why This Phase Exists

- Phase 15 reproduces the paper's prompting baselines on GPT models. Those are the paper's reference points, not its contribution.
- The contribution is SMARTAgent: models fine-tuned on SMART-ER so they call tools only when their own knowledge falls short. The headline claim is a 24.00% macro-average decrease in tool use with a 37.10% macro-average increase in performance.
- Testing that claim needs open models, which means a GPU.

---

## Paper Reference Numbers

Each cell gives tool calls per question, then accuracy (%). For IN3, accuracy is Missing Details Recovery at levels 3 and 2, followed by Summarized Intention Coverage.

**Table 3 (in-domain)**

| Model | Setting | MATH | FreshQA | IN3 |
| --- | --- | --- | --- | --- |
| Llama-3.1-8B | Normal reasoning trained | 0.00, 41.00 | 0.00, 48.00 | 0.00, 38.37 / 42.49, n/a |
| Llama-3.1-8B | Reasoning prompt | 0.00, 53.00 | 0.00, 26.00 | 0.00, 40.70 / 25.76, n/a |
| Llama-3.1-8B | Tool prompt | 1.93, 51.00 | 2.05, 56.00 | 3.77, 54.76 / 25.90, 70.20 |
| Llama-3.1-8B | SMARTAgent | 0.88, 54.75 | 1.05, 67.00 | 3.80, 81.40 / 67.41, 78.28 |
| Mistral-7B | Normal reasoning trained | 0.00, 17.00 | 0.00, 48.00 | 0.00, 41.86 / 43.84, n/a |
| Mistral-7B | Reasoning prompt | 0.00, 17.25 | 0.00, 29.00 | 0.00, 37.21 / 33.06, n/a |
| Mistral-7B | Tool prompt | 3.90, 13.25 | 1.67, 49.00 | 3.80, 48.84 / 21.70, 63.04 |
| Mistral-7B | SMARTAgent | 0.60, 22.75 | 1.00, 64.00 | 3.60, 74.42 / 65.44, 81.76 |

**Table 4 (out-of-distribution)**

| Model | Setting | GSM8K | MINTQA |
| --- | --- | --- | --- |
| Llama-3.1-8B | Normal reasoning trained | 0.00, 80.29 | 0.00, 21.65 |
| Llama-3.1-8B | Reasoning prompt | 0.00, 82.26 | 0.00, 12.37 |
| Llama-3.1-8B | Tool prompt | 2.53, 83.17 | 4.03, 16.49 |
| Llama-3.1-8B | SMARTAgent | 0.76, 83.40 | 1.06, 29.90 |
| Mistral-7B | Normal reasoning trained | 0.00, 58.68 | 0.00, 21.65 |
| Mistral-7B | Reasoning prompt | 0.00, 50.57 | 0.00, 19.59 |
| Mistral-7B | Tool prompt | 3.56, 55.34 | 6.46, 10.31 |
| Mistral-7B | SMARTAgent | 0.45, 58.98 | 0.99, 25.77 |

Rows for Mistral-Nemo-12B, Mistral-Small-24B, and Llama-3.1-70B are in the paper. Copy them from there if you run those models.

---

## How the Paper's Code Works (Source of Truth)

Phase 15 covers the tool prompt loop, the reasoning prompt, the tools, and the grading. This phase adds `inference/inference_smart.py` and the training setup. Read them yourself before building. Where these notes and the code disagree, the code wins.

**SMART loop (SMARTAgent models)**

- Prompts come from the `_smart.json` files. The instruction and input are always joined into one user message.
- Each round, the model writes steps in the form "- Step N: title (tool: Name)" or "(general reasoning)", one under another. `### Final Response` ends the question.
- If the last step parsed is a tool step, the tool runs, and its result is attached to that step as "- Output: ...".
- The user message is then **rebuilt**, not appended to: the instruction, the task, `### Reasoning Steps`, and every step so far in the step format.
- At most 10 rounds, temperature 0.000001, 4096 max tokens, served through vLLM.
- Differences from the tool prompt loop: Search uses the function's default of 10 results instead of 3, and Code doesn't carry earlier snippets over.

**Training**

- LLaMA-Factory (the repo's `training` submodule), SFT with LoRA: rank 16, alpha 32, dropout 0.05, all layers. Sequence length 4096, per-device batch 2, gradient accumulation 4, learning rate 1e-4, cosine schedule with 0.1 warmup, 3 epochs, bf16 (paper Table 7).
- The paper trained on 4 A40 GPUs, so the effective batch is 32.
- Training data: `data_train/instruction_pair_data.json`. The indicator version, `instruction_pair_data_indicator.json`, puts one of `[[Reasoning]]`, `[[Code]]`, `[[Search]]`, `[[AskUser]]` at the start of each step.
- After training, the LoRA weights are merged into the base model using the paper's merge configs.

**Confidence validation (paper section 5.3 and appendix C.5)**

- Llama-3.1-8B and Mistral-7B are trained with the indicator tokens.
- 50 decision steps are sampled from the Time and Intention test splits. A decision step is the next step of a solution chain, given every step before it.
- The model's confidence is the probability it gives the indicator token it chooses. Decisions are labeled correct or incorrect against the ground truth, and the paper reports higher confidence on correct decisions (its Figure 6).

---

## Known Gaps in the Paper's Released Code

Record each of these as a deviation if you work around it, so nobody reads it as a silent fix.

1. **Search crashes in the SMART loop.** `inference_smart.py` reads the search query from a variable that's only set in the final-response branch. As released, every Search call raises an error and the question is dropped. Decision: read the query from the last parsed step, which is clearly what was meant.
2. **"Normal reasoning trained" data isn't released.** The paper trained it on the training queries with their original solutions and no tools. Decision: build it from `data_raw/` by removing tool steps, document exactly how, and treat the result as an approximation.

---

## Decisions to Make (and Write Down)

- **GPU.** One rented GPU with at least 48 GB (A40, L40S, or A100) covers the 8B and 7B models for both inference and LoRA training. To keep the effective batch of 32 on one GPU, raise gradient accumulation to 16. Record the provider, GPU type, hours, and cost.
- **Which models.** Required: Llama-3.1-8B and Mistral-7B, the only ones in Table 4. Optional: Mistral-Nemo-12B and Mistral-Small-24B. Out of scope: Llama-3.1-70B, which needs several GPUs.
- **Which models to train.** Required: our own SmartAgent-Llama-3.1-8B, plus Llama-3.1-8B for the normal reasoning trained baseline and for confidence validation. Mistral-7B training is optional. Use the released Mistral checkpoint for its SMARTAgent row.
- **Model versions.** Record the Hugging Face revision hash of every base model and checkpoint.
- **Secrets on the GPU box.** Serper and OpenAI keys go in the provider's secret store, never in the repo or the image.
- **Code execution.** The same container setup as Phase 15, on the GPU box.

---

## Tasks

### Task 1 - GPU environment
- A rented GPU box with vLLM, the project code, and the code-execution container.
- Plug vLLM into Phase 15's model-call interface, so both of Phase 15's pipelines run on open models unchanged, using the Llama and Mistral message layouts.
- **Done when:** vLLM serves Llama-3.1-8B-Instruct and `paper_tool_prompt` finishes a 2-question smoke run with it.

### Task 2 - SMART loop as a pipeline
- `paper_smart`: the step format, rebuilding the user message each round, the 10-round cap, the Search fix from gap 1, Search with 10 results, and Code without carry-over, all as released.
- Same tools and graders as Phase 15.
- **Done when:** a 2-question smoke run with SmartAgent-Llama-3.1-8B on each test set finishes, and the traces show the step format.

### Task 3 - Base model rows
- Run `paper_reasoning_prompt` and `paper_tool_prompt` on Llama-3.1-8B-Instruct and Mistral-7B-Instruct-v0.3, on all five sets.
- **Done when:** both base models have numbers for both settings on all five sets.

### Task 4 - Released SMARTAgent rows
- Run `paper_smart` with SmartAgent-Llama-3.1-8B and SmartAgent-Mistral-7B-Instruct-v0.3 on all five sets. Nemo and Small are optional.
- **Done when:** both rows are filled in, and the macro-average tool-use decrease and performance increase are computed the way the paper describes them.

### Task 5 - Training environment
- LLaMA-Factory from the paper's `training` submodule, on the same box.
- **Done when:** a 10-step training run on a small slice of the data finishes and saves a LoRA checkpoint.

### Task 6 - Fine-tune our own SmartAgent-Llama-3.1-8B
- Table 7 hyperparameters, with gradient accumulation scaled to keep the effective batch at 32.
- Keep the training loss curve and the validation numbers.
- **Done when:** 3 epochs finish, the LoRA is merged, and `paper_smart` with our model has numbers on all five sets next to the released checkpoint's. If the gap is bigger than run-to-run noise, write down the likely causes.

### Task 7 - Normal reasoning trained baseline
- Build the no-tool training set from `data_raw/` (gap 2), train Llama-3.1-8B with the same settings, and evaluate it with `paper_reasoning_prompt`.
- **Done when:** its row is filled in and the data construction is documented.

### Task 8 - Confidence validation
- Train Llama-3.1-8B on the indicator data, adding the four special tokens to the tokenizer the way the paper's indicator config does.
- Sample 50 decision steps from the Time and Intention test splits with a fixed seed. Each one is a solution chain cut just before step k, with the ground-truth choice for step k (tool or reasoning) taken from the raw data.
- For each sample, read the probability the model gives each special token as its next output. Its choice is the most likely token, and its confidence is that token's probability.
- **Done when:** the samples and seed are saved, and you have the mean confidence and the distribution for correct vs incorrect decisions, plus a chart comparable to the paper's Figure 6.

### Task 9 - Place our prompt gate
- Put Phase 12's `baseline` and `smart` results and Phase 15's GPT rows in the same tables as this phase's rows, marked as a different method and different tools where that's the case.
- Answer plainly: on tool use and on accuracy, is our prompt gate closer to the paper's tool prompt baseline, or to SMARTAgent?
- **Done when:** the comparison paragraph is written and backed by the tables.

### Task 10 - Write-up and housekeeping
- Fill in the results tables, list every deviation, give the GPU and API spend, and say what surprised you.
- Keep the summary files cited here in git. Raw traces, checkpoints, and model weights stay out.
- Tick Phase 16 in the README.
- **Done when:** someone could rerun any row from this doc alone.

---

## What Counts as a Successful Replication

- **Write down your tolerance before any run.** A reasonable start: tool calls within about 0.3 and accuracy within about 5 points of the paper for each model row, after Phase 15's spot-check correction on the Search-based sets.
- **The paper's central claim is reproduced** if, for both 8B and 7B, SMARTAgent uses clearly fewer tools than the same model's tool prompt, with equal or higher accuracy, on most of the five sets. That should hold for both the released checkpoint and our own.
- **The confidence result is reproduced** if mean confidence on correct decisions is clearly above mean confidence on incorrect ones.
- **Rows outside the tolerance are findings, not failures.** For each one, name the most likely cause and the evidence for it.

---

## Results

Not run yet. Paper numbers are given as tool calls, accuracy.

**In-domain**

| Model | Setting | MATH | FreshQA | IN3 | Paper (MATH / FreshQA / IN3) |
| --- | --- | --- | --- | --- | --- |
| Llama-3.1-8B | Reasoning prompt | | | | 0.00, 53.00 / 0.00, 26.00 / 0.00, 40.70 / 25.76 |
| Llama-3.1-8B | Tool prompt | | | | 1.93, 51.00 / 2.05, 56.00 / 3.77, 54.76 / 25.90 |
| Llama-3.1-8B | SMARTAgent (released) | | | | 0.88, 54.75 / 1.05, 67.00 / 3.80, 81.40 / 67.41 |
| Llama-3.1-8B | SMARTAgent (ours) | | | | same as above |
| Llama-3.1-8B | Normal reasoning trained (ours) | | | | 0.00, 41.00 / 0.00, 48.00 / 0.00, 38.37 / 42.49 |
| Mistral-7B | Reasoning prompt | | | | 0.00, 17.25 / 0.00, 29.00 / 0.00, 37.21 / 33.06 |
| Mistral-7B | Tool prompt | | | | 3.90, 13.25 / 1.67, 49.00 / 3.80, 48.84 / 21.70 |
| Mistral-7B | SMARTAgent (released) | | | | 0.60, 22.75 / 1.00, 64.00 / 3.60, 74.42 / 65.44 |

**Out-of-distribution**

| Model | Setting | GSM8K | MINTQA | Paper (GSM8K / MINTQA) |
| --- | --- | --- | --- | --- |
| Llama-3.1-8B | Reasoning prompt | | | 0.00, 82.26 / 0.00, 12.37 |
| Llama-3.1-8B | Tool prompt | | | 2.53, 83.17 / 4.03, 16.49 |
| Llama-3.1-8B | SMARTAgent (released) | | | 0.76, 83.40 / 1.06, 29.90 |
| Llama-3.1-8B | SMARTAgent (ours) | | | same as above |
| Llama-3.1-8B | Normal reasoning trained (ours) | | | 0.00, 80.29 / 0.00, 21.65 |
| Mistral-7B | Reasoning prompt | | | 0.00, 50.57 / 0.00, 19.59 |
| Mistral-7B | Tool prompt | | | 3.56, 55.34 / 6.46, 10.31 |
| Mistral-7B | SMARTAgent (released) | | | 0.45, 58.98 / 0.99, 25.77 |

**Macro averages (SMARTAgent vs tool prompt)**

| Model | Tool use decrease | Performance increase | Paper |
| --- | --- | --- | --- |
| Released checkpoints | | | 24.00% / 37.10% (all five paper models) |
| Our Llama-3.1-8B | | | |

**Confidence validation**

| Decisions | Count | Mean confidence |
| --- | --- | --- |
| Correct | | |
| Incorrect | | |

---

## Rules

- Don't edit the paper's instruction text or training data, even to fix typos.
- Don't tune anything based on test questions.
- Record every deviation from the paper's code, however small.
- Report bad results too.
- Never commit API keys, model weights, or checkpoints.
- Shut the GPU box down when it isn't running anything.

---

## Dependencies

- Phase 15 (loop, tools, graders, full prompt items, spot-checks)

---

## Out of Scope

- Llama-3.1-70B (needs several GPUs)
- The paper's Appendix D extras (AMC'23 and o1-style models)
- Changing the `baseline` or `smart` pipelines or their graders
