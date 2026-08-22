#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 <xword-dl source or URL> [YYYY-MM-DD]" >&2
  exit 2
fi

source_name="$1"
output="data/crossword.puz"
xword_dl=".venv/bin/xword-dl"

if [[ ! -x "$xword_dl" ]]; then
  echo "Missing $xword_dl. Install it with:" >&2
  echo "  uv pip install --python .venv/bin/python 'xword-dl==2025.10.14'" >&2
  exit 1
fi

args=("$xword_dl" "$source_name" --output "$output")

if [[ $# -eq 2 ]]; then
  args+=(--date "$2")
fi

"${args[@]}"
echo "Downloaded $output"
