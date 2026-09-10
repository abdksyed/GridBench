# GridBench datasets

The dataset is built from `crossword/` by `src/downloads/export_jsonl.py`.

| File | Each Row Content | #Rows |
|---|---|---:|
| `puzzles.jsonl` | one puzzle (grid, clues, rebus, split) | 98,548 |
| `entries.jsonl` | one entry from those puzzles | 5,332,845 |
| `crosswordqa.jsonl` | clue–answer pairs from CrosswordQA | 5,814,875 |
| `raw/crosswordqa/` | original [CrosswordQA](https://huggingface.co/datasets/albertxu/CrosswordQA) CSVs | — |

Each row in the puzzles/entries belong to one of the following `split`: `train` · `dev` · `test_temporal` · `test_publisher`.

| Split | Puzzles | Entries | Rule |
|---|---:|---:|---|
| `test_publisher` | 8,188 | 280,779 | atlantic, inkubator, newyorker, vulture, Independent cryptic |
| `test_temporal` | 9,036 | 407,557 | newest 10% from remaining publishers|
| `dev` | 9,036 | 417,653 | next-newest 10% (prompts / DSPy) |
| `train` | 72,288 | 4,226,856 | remainder |

Temporal % is of puzzles **not** in `test_publisher`.

**CrosswordQA:** We combine both the `train.csv` + `valid.csv` and drop a rowif its normalized clue appears in our non-train puzzles (967,373 dropped). The final dataset has around ~62% of pairs which are not in `entries.jsonl`.
