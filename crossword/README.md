# Crossword corpus

Local collection of crossword `.puz` files, merged and grouped as
`publisher/type/yyyy-mm-dd.puz`.

**98,549** unique puzzles (from 113,699 downloaded files).

## Sources

Two downloads, then a merge.

1. **Archive** (`puzzles/`, 92,801 files).
   The [xwords archive](https://q726kbxun.github.io/xwords/xwords.html),
   downloaded with
   [`view_archive.py`](https://github.com/Q726kbXuN/q726kbxun.github.io/blob/main/xwords/view_archive.py)
   (`src/downloads/download_archive.py`).

2. **xword-dl** (`data/`, 20,898 files).
   Extra / overlapping puzzles from the
   [xword-dl](https://github.com/thisisparker/xword-dl) library
   (`src/downloads/download_xwordl.py`).

Washington Post puzzles are the LA Times crossword; they were treated as LAT copies.

## Merge

`src/downloads/merge_data.py` hashes each **solution grid** and keeps one file
per unique grid (prefer archive over xword-dl).

- 113,699 source files
- 98,549 unique grids copied here
- 15,149 extra copies dropped
- 1 file skipped (corrupt checksum: `data/sdpq/2025-11-01.puz`)
- 50 same-publisher/same-date collisions kept as `yyyy-mm-dd-1.puz`, etc.

Type is taken from the filename suffix when present (`-mini`, `-cryptic`, …),
then from the xword-dl source (`latm` → LAT mini, `tnym` → New Yorker mini),
then from grid size:

| Size | Type |
|---|---|
| 9×9 and smaller (area ≤ 81) | `mini` |
| 10×10 to 13×13 (area ≤ 169) | `midi` |
| 21×21 | `sundays` |
| everything else | `classic` |

## Types

American-style dailies, by size:

- **mini** — small grid, typically 5×5 to 9×9
- **midi** — medium grid, typically 10×10 to 13×13
- **classic** — standard daily, almost all 15×15
- **sundays** — 21×21 Sunday puzzle

Named extras (mostly NYT):

- **bonus** — extra puzzle published with a daily
- **variety** — non-standard / variety crossword
- **diagramless** — no block pattern given; mostly 17×17

British / cryptic family:

- **cryptic** — British cryptic, mostly 15×15
- **quick** — easy straight-definition clues, 13×13 (Guardian Quick, Simply Daily Quick)
- **quiptic** — Guardian beginner cryptic, 15×15
- **speedy** — Guardian Speedy, 13×13
- **everyman** — Guardian Everyman cryptic, 15×15
- **prize** — Guardian Prize cryptic, 15×15
- **weekend** — Guardian Weekend, 13×13
- **jumbo** — oversized Independent, 23×23
- **special** — occasional Guardian special

Other series names, kept as published:

- **sheffer** / **joseph** / **premier** — King Features (13×13, 11×13, 21×21)
- **plus** / **celebrity** — AV Crosswords extras
- **caleb** — Atlantic “Caleb” puzzles, often a tall 7×N grid

## Publishers

| Publisher | Puzzles | Types |
|---|---:|---|
| nytimes | 33,427 | classic, mini, sundays, bonus, variety, midi, diagramless |
| guardian | 21,023 | quick, cryptic, quiptic, prize, everyman, speedy, weekend, mini, special |
| independent | 8,261 | midi, cryptic, jumbo |
| latimes | 5,774 | classic, mini, sundays |
| usatoday | 3,698 | classic, mini |
| newsday | 3,366 | classic, sundays |
| universal | 2,776 | classic |
| dailypop | 2,702 | midi, classic |
| atlantic | 2,376 | mini, classic, midi, caleb |
| wsj | 2,375 | classic, sundays |
| apple | 2,295 | mini, classic, bonus |
| vox | 2,132 | mini, classic, midi |
| avcrosswords | 1,682 | classic, mini, cryptic, plus, sundays, bonus, celebrity |
| crosswordclub | 1,468 | mini, midi, classic |
| newyorker | 1,331 | classic, mini, sundays |
| kingfeatures | 1,003 | sheffer, joseph, premier |
| slate | 826 | mini, midi, classic |
| mondayfills | 748 | classic, sundays |
| vulture | 639 | midi |
| princetonian | 275 | mini |
| simplydaily | 271 | quick |
| inkubator | 101 | classic, bonus, sundays |
