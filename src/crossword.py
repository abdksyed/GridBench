# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "openai>=2.0,<3",
#   "inspect-ai>=0.3.251,<0.4",
#   "pydantic>=2.10,<3",
#   "puzpy>=0.6.1,<0.7",
# ]
# ///

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import puz
from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.model import GenerateConfig, ResponseSchema
from inspect_ai.scorer import (
    CORRECT,
    INCORRECT,
    Score,
    Scorer,
    Target,
    accuracy,
    mean,
    scorer,
)
from inspect_ai.solver import TaskState, generate
from inspect_ai.util import JSONSchema
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

MODEL = "gpt-5.6-luna"
PUZZLE_PATH = Path("data/crossword.puz")

PROMPT = """Solve this crossword puzzle.

The grid uses # for blocked cells and . for open cells.

Grid ({rows} rows x {cols} columns):
{grid}

Across clues:
{across}

Down clues:
{down}

Use the grid, answer lengths, and crossing letters to solve every entry.
Return JSON with an `entries` array, where each string is one complete row of the grid.
Answers must contain uppercase A-Z letters only.
"""


class CrosswordSolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[str]


class CrosswordGrade(BaseModel):
    """Deterministic comparison between the gold and predicted grids."""

    parse_valid: bool
    grid_valid: bool
    exact_grid_correct: bool
    word_accuracy: float
    cell_accuracy: float
    expected_rows: int
    expected_cols: int
    predicted_rows: int
    predicted_cols: int
    wrong_dimensions: bool = False
    invalid_cells: list[str] = Field(default_factory=list)
    wrong_cells: list[str] = Field(default_factory=list)
    wrong_words: list[str] = Field(default_factory=list)
    raw_parsed_response: dict[str, object] | None = None
    parse_error: str | None = None


def _grid_rows_and_columns(puzzle: puz.Puzzle) -> tuple[list[str], list[str]]:
    """Return normalized gold rows and columns, using # for blocks."""

    if hasattr(puzzle, "solution_grid"):
        grid = puzzle.solution_grid()
        rows = ["".join(row) for row in grid.rows()]
        columns = ["".join(column) for column in grid.cols()]
    else:
        rows = [
            puzzle.solution[start : start + puzzle.width]
            for start in range(0, len(puzzle.solution), puzzle.width)
        ]
        columns = [
            "".join(puzzle.solution[row * puzzle.width + col] for row in range(puzzle.height))
            for col in range(puzzle.width)
        ]
    return (
        [row.upper().replace(".", "#") for row in rows],
        [column.upper().replace(".", "#") for column in columns],
    )


def _parse_solution(
    raw_output: str | CrosswordSolution,
) -> tuple[CrosswordSolution | None, dict[str, Any] | None, str | None]:
    if isinstance(raw_output, CrosswordSolution):
        return raw_output, raw_output.model_dump(mode="json"), None
    try:
        decoded = json.loads(raw_output.strip())
        if not isinstance(decoded, dict):
            return None, None, "response must be a JSON object"
        return CrosswordSolution.model_validate(decoded), decoded, None
    except (ValueError, TypeError) as exc:
        return None, None, f"invalid response JSON: {exc}"


def _word_from_rows(rows: list[str], clue: dict[str, Any], width: int) -> str | None:
    start = int(clue["cell"])
    length = int(clue["len"])
    row, col = divmod(start, width)
    if clue["dir"] == "across":
        if row >= len(rows) or col + length > len(rows[row]):
            return None
        return rows[row][col : col + length]
    if col >= width or row + length > len(rows):
        return None
    if any(col >= len(candidate) for candidate in rows[row : row + length]):
        return None
    return "".join(rows[row + offset][col] for offset in range(length))


def grade_solution(
    puzzle: puz.Puzzle,
    raw_output: str | CrosswordSolution,
) -> CrosswordGrade:
    """Compare a predicted row-grid against the puzpy solution grid."""

    solution, raw, parse_error = _parse_solution(raw_output)
    gold_rows, gold_columns = _grid_rows_and_columns(puzzle)
    expected_rows, expected_cols = puzzle.height, puzzle.width
    if solution is None:
        return CrosswordGrade(
            parse_valid=False,
            grid_valid=False,
            exact_grid_correct=False,
            word_accuracy=0.0,
            cell_accuracy=0.0,
            expected_rows=expected_rows,
            expected_cols=expected_cols,
            predicted_rows=0,
            predicted_cols=0,
            raw_parsed_response=raw,
            parse_error=parse_error,
        )

    predicted = [row.strip().upper() for row in solution.entries]
    predicted_rows = len(predicted)
    predicted_cols = max((len(row) for row in predicted), default=0)
    wrong_dimensions = predicted_rows != expected_rows or any(
        len(row) != expected_cols for row in predicted
    )

    invalid_cells: list[str] = []
    wrong_cells: list[str] = []
    correct_cells = 0
    open_cells = 0
    for row_index, gold_row in enumerate(gold_rows):
        for col_index, gold_cell in enumerate(gold_row):
            if gold_cell == "#":
                continue
            open_cells += 1
            predicted_cell = (
                predicted[row_index][col_index]
                if row_index < predicted_rows and col_index < len(predicted[row_index])
                else None
            )
            location = f"R{row_index + 1}C{col_index + 1}"
            if predicted_cell is None:
                wrong_cells.append(location)
            elif not (predicted_cell.isascii() and predicted_cell.isalpha()):
                invalid_cells.append(location)
            elif predicted_cell != gold_cell:
                wrong_cells.append(location)
            else:
                correct_cells += 1

    numbering = puzzle.clue_numbering()
    clues = [*numbering.across, *numbering.down]
    wrong_words: list[str] = []
    correct_words = 0
    for clue in clues:
        row, col = divmod(int(clue["cell"]), expected_cols)
        length = int(clue["len"])
        if clue["dir"] == "across":
            expected = gold_rows[row][col : col + length]
        else:
            expected = gold_columns[col][row : row + length]
        if _word_from_rows(predicted, clue, expected_cols) == expected:
            correct_words += 1
        else:
            wrong_words.append(f"{clue['num']}-{clue['dir'].title()}")

    word_accuracy = correct_words / len(clues) if clues else 0.0
    cell_accuracy = correct_cells / open_cells if open_cells else 0.0
    rectangular = not wrong_dimensions and all(
        all(cell == "#" or (cell.isascii() and cell.isalpha()) for cell in row)
        for row in predicted
    )
    blocks_match = rectangular and all(
        predicted[row][col] == "#"
        for row in range(expected_rows)
        for col in range(expected_cols)
        if gold_rows[row][col] == "#"
    )
    grid_valid = rectangular and blocks_match
    exact = grid_valid and not wrong_cells and not invalid_cells and not wrong_words
    return CrosswordGrade(
        parse_valid=True,
        grid_valid=grid_valid,
        exact_grid_correct=exact,
        word_accuracy=word_accuracy,
        cell_accuracy=cell_accuracy,
        expected_rows=expected_rows,
        expected_cols=expected_cols,
        predicted_rows=predicted_rows,
        predicted_cols=predicted_cols,
        wrong_dimensions=wrong_dimensions,
        invalid_cells=invalid_cells,
        wrong_cells=wrong_cells,
        wrong_words=wrong_words,
        raw_parsed_response=raw,
    )


def build_prompt(puzzle: puz.Puzzle) -> str:
    numbering = puzzle.clue_numbering()
    grid = "\n".join(
        "".join("#" if cell == "." else "." for cell in row)
        for row in (
            puzzle.fill[start : start + puzzle.width]
            for start in range(0, len(puzzle.fill), puzzle.width)
        )
    )
    across = "\n".join(
        f"{clue['num']}-Across ({clue['len']}): {clue['clue']}"
        for clue in numbering.across
    )
    down = "\n".join(
        f"{clue['num']}-Down ({clue['len']}): {clue['clue']}"
        for clue in numbering.down
    )
    return PROMPT.format(
        rows=puzzle.height,
        cols=puzzle.width,
        grid=grid,
        across=across,
        down=down,
    )


def crossword_response_schema() -> ResponseSchema:
    return ResponseSchema(
        name="crossword_solution",
        description="One string for each row of the completed crossword grid.",
        json_schema=JSONSchema.model_validate(CrosswordSolution.model_json_schema()),
        strict=True,
    )


def _grade_score(
    puzzle: puz.Puzzle,
    state: TaskState,
    value: str,
) -> Score:
    completion = state.output.completion if state.output is not None else ""
    grade = grade_solution(puzzle, completion)
    if value == "exact_grid_correct":
        score_value: str | float = CORRECT if grade.exact_grid_correct else INCORRECT
    else:
        score_value = getattr(grade, value)
    return Score(
        value=score_value,
        answer=completion,
        metadata=grade.model_dump(mode="json"),
    )


@scorer(name="exact_grid_correct", metrics=[accuracy()])
def exact_grid_scorer(puzzle: puz.Puzzle) -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        return _grade_score(puzzle, state, "exact_grid_correct")

    return score


@scorer(name="word_accuracy", metrics=[mean()])
def word_accuracy_scorer(puzzle: puz.Puzzle) -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        return _grade_score(puzzle, state, "word_accuracy")

    return score


@scorer(name="cell_accuracy", metrics=[mean()])
def cell_accuracy_scorer(puzzle: puz.Puzzle) -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        return _grade_score(puzzle, state, "cell_accuracy")

    return score


@task
def crossword(puzzle: str = str(PUZZLE_PATH)) -> Task:
    """Run one crossword with Inspect AI and the three deterministic metrics."""

    puzzle_path = Path(puzzle)
    if not puzzle_path.exists():
        raise ValueError(f"Missing crossword puzzle: {puzzle_path}")
    puzzle_data = puz.read(str(puzzle_path))
    return Task(
        dataset=[
            Sample(
                id=puzzle_path.stem,
                input=build_prompt(puzzle_data),
                target="",
                metadata={
                    "puzzle_path": str(puzzle_path),
                    "rows": puzzle_data.height,
                    "cols": puzzle_data.width,
                },
            )
        ],
        solver=generate(tool_calls="none"),
        scorer=[
            exact_grid_scorer(puzzle_data),
            word_accuracy_scorer(puzzle_data),
            cell_accuracy_scorer(puzzle_data),
        ],
        config=GenerateConfig(
            temperature=0,
            max_retries=2,
            max_connections=1,
            response_schema=crossword_response_schema(),
            cache=True,
        ),
        epochs=1,
        fail_on_error=False,
        score_on_error=False,
        metadata={
            "model": MODEL,
            "puzzle_path": str(puzzle_path),
            "metrics": ["exact_grid_correct", "word_accuracy", "cell_accuracy"],
        },
    )


def main() -> None:
    if not PUZZLE_PATH.exists():
        raise SystemExit(
            "Missing data/crossword.puz. Run ./data/download_crossword.sh first."
        )

    puzzle: puz.Puzzle = puz.read(str(PUZZLE_PATH))
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("Set OPENAI_API_KEY before running this script.")

    base_url = os.environ.get("OPENAI_BASE_URL")
    client = OpenAI(base_url=base_url) if base_url else OpenAI()

    prompt = build_prompt(puzzle)
    response = client.responses.parse(
        model=MODEL,
        input=[
            {
                "role": "system",
                "content": "You are an expert crossword solver.",
            },
            {"role": "user", "content": prompt},
        ],
        text_format=CrosswordSolution,
    )

    solution = response.output_parsed
    if solution is None:
        raise SystemExit(f"The model did not return a crossword solution: {response.output_text}")
    print(solution.model_dump_json(indent=2))
    print(grade_solution(puzzle, solution).model_dump_json(indent=2))

if __name__ == "__main__":
    main()
