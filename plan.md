# GridBench Plan

## Project Goal

GridBench is a personal experiment for comparing how well language models solve
crosswords. Start with one puzzle, make the evaluation trustworthy, and then add
data, reasoning strategies, and prompt optimizers one at a time.

The primary result is exact completed-grid accuracy. Word accuracy and cell
accuracy explain partial progress.

## Keep It Small

This is not a production system.

- No automated tests or CI for now.
- No web app, dashboard, database, API server, deployment, or monitoring.
- No generic puzzle framework before another puzzle type is actually added.
- No large corpus/download framework. Keep the existing download script simple.
- No second evaluation framework. Inspect AI remains the final evaluator.
- No LLM judge for correctness. Gold solutions and deterministic grading are enough.
- No complex report generator until manually reading Inspect logs becomes painful.
- No requirement to reach 100 puzzles before the small experiment works end to end.

Add a file or abstraction only when the current experiment genuinely needs it.

## Models

Run the same conditions across these four model families:

- GPT-5.6 sol
- Claude Opus 5
- Grok 4.6
- Gemini 3.7 Flash

Use the exact provider/model IDs available at the time of each run. Do not guess
or permanently bake marketing names into the benchmark. Record the full model ID
in Inspect metadata and keep it fixed while comparing methods.

For fair comparisons, use the same puzzles, prompt condition, temperature,
structured output, and scoring code for every model.

## Metrics

Keep the existing three Inspect metrics:

1. `exact_grid_correct`: `1` only when the complete grid is correct.
2. `word_accuracy`: exact Across and Down answers divided by all entries.
3. `cell_accuracy`: correct open cells divided by all open cells.

Exact grid correctness is always the headline result. Word and cell accuracy are
diagnostics, not replacements for solving the puzzle.

Malformed output is an incorrect solution. Provider or runtime failures should
be visible in the Inspect log rather than confused with a normally completed but
wrong answer.

## Experiment Rules

- Keep raw puzzle files and answer-bearing data local.
- Never put the gold solution in a normal evaluation prompt.
- Use temperature `0` for baseline comparisons.
- Use one epoch initially.
- Use Inspect caching to avoid paying twice for identical calls.
- Change one major variable at a time.
- Preserve the original one-shot baseline even after adding multi-call methods.
- Label multi-call methods such as ReAct and RLM separately from one-shot methods.
- Record model ID, method, prompt version, puzzle ID, score, call count, and cost
  when Inspect provides it.

## Phase 0: Confirm the Existing Single-Puzzle Baseline

The current repository already has:

- `data/download_crossword.sh` for downloading one `.puz` file;
- `src/crossword.py` for prompt rendering, OpenAI execution, grading, and Inspect;
- deterministic exact-grid, word, and cell metrics;
- structured JSON output containing completed grid rows.

Before adding anything else:

1. Download one puzzle with a known solution.
2. Run the direct script once.
3. Run the Inspect task against one available model.
4. Open the Inspect log and confirm all three metric values are present.
5. Manually inspect one correct-looking and one malformed output.

Exit condition: one real model call produces a readable Inspect log with all
three metrics and no scoring exception.

## Phase 1: Run the Same One-Shot Prompt Across Models

Run the current `generate()` baseline on the same puzzle across all available
model families. Do not introduce DSPy yet.

Compare:

- exact grid result;
- word and cell accuracy;
- output/schema failures;
- latency and cost when available.

If a listed model is unavailable, record that fact and use its current equivalent
rather than blocking the entire project.

Exit condition: a small table with one row per model for the same puzzle.

## Phase 2: Build a Small Useful Dataset

Do not jump straight from one puzzle to 100. Grow in steps:

1. Start with 5 puzzles to find parser and prompt problems.
2. Grow to 10-20 puzzles for early method comparisons.
3. Grow toward 40-100 only after runs are stable and affordable.

Try to include:

- American standard puzzles;
- British cryptic puzzles;
- small and normal-sized grids where sources provide them.

A simple local folder of `.puz` files plus a small JSONL manifest is sufficient.
The manifest only needs puzzle path/ID, region, style, source, date, and split.
Do not build a download service or generic corpus pipeline.

Once prompt optimization begins, freeze non-overlapping splits:

- training puzzles for optimizer feedback and demonstrations;
- validation puzzles for selecting optimizer candidates;
- test puzzles used only for final Inspect evaluation.

Split by puzzle, and avoid duplicate clues or answers crossing splits where this
can be detected easily. Keep region/style proportions reasonably similar.

Exit condition: at least 10 clean local puzzles can be run through the same task.

## Phase 3: Improve the Manual One-Shot Prompt

Before using an optimizer, try a few understandable prompt variants manually:

1. Current minimal prompt.
2. Explicitly tell the model to solve crossings jointly and verify every row.
3. Improve clue/grid formatting without adding answer information.
4. Ask for internal reasoning but require only the final JSON grid in the output.

Give each prompt a short version name such as `baseline-v1` or `verify-v2` and
record it in Inspect metadata. Stop manually tweaking once improvements become
unclear; that is the point where DSPy becomes useful.

Exit condition: choose one clear one-shot prompt as the pre-DSPy baseline.

## Phase 4: Add a Minimal DSPy Predict Baseline

Add one small DSPy file only when the dataset and Inspect baseline work. Keep the
existing grader rather than rewriting metrics in DSPy.

The first DSPy program should be only:

```python
class CrosswordSolver(dspy.Module):
    def __init__(self):
        self.solve = dspy.Predict("puzzle_prompt -> grid_json")

    def forward(self, puzzle_prompt):
        return self.solve(puzzle_prompt=puzzle_prompt)
```

DSPy's metric can call the same deterministic grading function. Inspect remains
the source of final benchmark results; DSPy evaluation is only used internally
when an optimizer requires it.

First run unoptimized `dspy.Predict` across the models. This tells us whether the
DSPy adapter or output formatting changes the baseline before optimization.

Exit condition: DSPy Predict returns the same grid contract and can be scored by
the existing grader.

## Phase 5: Try Reasoning Modules

Test each method as a separate condition. Do not replace the baseline.

### 5A. Chain of Thought

Replace `dspy.Predict` with `dspy.ChainOfThought` while keeping the same puzzle
input and final grid output. This is the first reasoning experiment because it
can still be a single model call.

Compare Predict versus Chain of Thought on the same puzzles and models.

### 5B. ReAct

Only try ReAct after Chain of Thought. Give it a very small set of deterministic,
non-answer-revealing tools, for example:

- inspect an entry's cells and current crossing pattern;
- place or replace a candidate answer in a working grid;
- report length or crossing conflicts;
- validate the final grid format.

Tools must not return the gold answer. ReAct is multi-step and likely multi-call,
so report it separately from the one-shot baseline and record call count/cost.

### 5C. RLM

Treat `dspy.RLM` as an optional solver architecture, not an optimizer. It gives a
model a Python REPL and recursive sub-model calls for inspecting and manipulating
context. It may help with a 15x15 grid and iterative crossing constraints, but it
also adds cost, latency, sandbox requirements, and experimental API risk.

Try RLM only if ReAct or normal reasoning struggles with maintaining grid state.
Keep it in a separate recursive/multi-call result category.

Exit condition: decide whether extra inference-time reasoning materially improves
exact solves enough to justify its calls and cost.

## Phase 6: Try Simple Few-Shot Optimization

Few-shot experiments require the frozen train/validation/test split.

Run in this order:

1. `LabeledFewShot` with a very small number of demonstrations.
2. `BootstrapFewShot` using the deterministic metric to accept demonstrations.
3. `BootstrapFewShotWithRandomSearch` only if basic bootstrapping helps.
4. Optionally `KNNFewShot` if selecting examples by region, style, or dimensions
   appears useful.
5. Optionally `InferRules`, especially for learning recurring cryptic conventions.

Never use a test puzzle as a demonstration. A demonstration may contain its own
gold completed grid, but only because it belongs to the training split.

Exit condition: determine whether demonstrations beat the zero-shot Predict and
Chain-of-Thought conditions on validation and untouched test puzzles.

## Phase 7: MIPROv2

Use MIPROv2 after the basic few-shot experiments. It searches instructions and
demonstration combinations, so it costs more and has more ways to overfit.

Use a bounded initial run such as `auto="light"`. Use a scalar optimization score
that keeps exact solving dominant while still rewarding partial progress:

```python
score = (
    0.80 * float(grade.exact_grid_correct)
    + 0.15 * grade.word_accuracy
    + 0.05 * grade.cell_accuracy
)
```

Choose candidates on validation puzzles. Run the selected program once on the
untouched test set with Inspect.

Exit condition: compare MIPROv2 against the best manual and few-shot conditions,
including optimization cost.

## Phase 8: GEPA

GEPA is the main prompt-optimization experiment because the grader can provide
specific textual feedback, not just one number.

Feedback can include:

- exact-grid result;
- word and cell accuracy;
- wrong dimensions or invalid characters;
- wrong Across/Down entry IDs;
- conflicting or incorrect cell locations;
- parse failures.

The optimizer may use gold answers and diagnostics on training puzzles. Normal
evaluation prompts and all test-time feedback must remain answer-free.

Start with `auto="light"`, a bounded metric-call budget, and an explicitly chosen
reflection model. Track reflection-model cost separately from crossword-solving
cost.

Optimize separately for each target model for the fairest best-model comparison.
An additional cross-model transfer experiment can optimize on one model and run
the resulting prompt on the other three, but label it clearly as transfer.

Exit condition: evaluate the selected GEPA program on the untouched test split
through the same Inspect metrics.

## Phase 9: Optional Optimizers

Only explore these if the earlier results leave a specific question:

- `SIMBA`: alternative reflective optimization focused on difficult examples;
- `COPRO`: simpler instruction-only search;
- `BetterTogether`: combine prompt and weight optimization after both are useful;
- `BootstrapFinetune` or GRPO: model-weight optimization, only for models that can
  actually be fine-tuned and only if prompt optimization has plateaued;
- `Ensemble`: combine multiple solvers, reported as a higher-cost multi-call method.

These are not required for the core personal project.

## Phase 10: Compare Results

Maintain one simple Markdown or CSV table. Suggested columns:

```text
model
method
prompt_version
split
puzzles
exact_solved
exact_rate
word_accuracy
cell_accuracy
parse_or_runtime_errors
model_calls
cost
```

The headline should always show an integer count such as `7/20`, followed by the
percentage. Break down American versus British cryptic only once there are enough
puzzles for the comparison to mean something.

The most useful comparisons are:

- model versus model under the same baseline;
- Predict versus Chain of Thought;
- one-shot versus ReAct/RLM;
- zero-shot versus few-shot;
- manual prompt versus MIPROv2 versus GEPA;
- per-model optimization versus cross-model prompt transfer;
- accuracy gain versus added calls and cost.

## Possible Later Extensions

These remain outside the main roadmap until the crossword benchmark is working:

- interactive crossword solving with model-visible grid tools;
- a multimodal condition using a rendered crossword image;
- Sudoku with its own independent parser, prompt, and grader;
- crossword generation and structural validation;
- larger or cleaner source-balanced datasets.

Do not add any of these merely to make the repository look complete.

## Immediate Next Steps

1. Run the current single-puzzle Inspect task with one real model.
2. Confirm the three metrics in the log.
3. Run the identical baseline across the other available model families.
4. Collect 5 puzzles and confirm the same task handles all of them.
5. Only then add the minimal DSPy Predict experiment.

