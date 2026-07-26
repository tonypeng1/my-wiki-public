#!/usr/bin/env python3
"""
Pre-filter for p4-lint: find concept files whose recurring-measurement record
is written as a bulleted list instead of a Markdown table.

A concept's own table is its CANONICAL record for the contradiction check
(scripts/extract-claims.py): table rows are recognized as the authority, and
prose restatements elsewhere are compared against them. A date-indexed series
written as bullets does NOT anchor — it is skipped as authority and its rows get
misattributed as restatements of neighboring concepts. This checker flags that
shape so it can be converted to a table (see the Key Details rule in CLAUDE.md).

To avoid flagging dated *events* that are legitimately prose (a medication's
prescribe/discontinue dates, a diagnosis timeline), a bullet only counts as a
measurement row when it is BOTH date-led (its content begins with an ISO date —
the row's key — rather than a label like "Prescribed:") AND carries a measured
value+unit or flagged value. Event bullets lead with a label and are skipped.

Outputs:
  LIST-FORMAT RECORDS  — >= MEASUREMENT_MIN measurement bullets, no dated table
  PARTIALLY TABULAR    — measurement bullets alongside a dated table (split series)

Exit code 0 in all cases. Output is intended to be read by the LLM to scope
which files need conversion.
"""

import re
from pathlib import Path

WIKI_ROOT = Path(__file__).parent.parent / "wiki"
CONCEPTS_DIR = WIKI_ROOT / "concepts"
MEASUREMENT_MIN = 2  # a series is two or more re-measurements of the same value

FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
BACKLINK_RE = re.compile(r"\[\[[^\]]+\]\]")
ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
# A date-led bullet: marker, optional leading emphasis/backticks, then the date.
# This is a record's row key ("- 2015-08-20 ...", "- **2024-03-28 ...**") and
# distinguishes it from a label-led event bullet ("- **Prescribed:** 2026-...").
ROW_KEY_RE = re.compile(r"^\s*[-*]\s+(?:[*_`]+\s*)?\d{4}-\d{2}-\d{2}")
TABLE_ROW_RE = re.compile(r"^\s*\|")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|[\s|:-]+\|?\s*$")

# Units that mark a measured value. Kept close to scripts/extract-claims.py,
# with the extra lab units that appear in this vault (pg/mL, fL, ng/mL, ...).
UNITS = (
    r"mg/dL|mmol/L|mIU/L|µIU/mL|uIU/mL|ng/dL|ng/mL|pg/mL|g/dL|U/L|IU/L|"
    r"mmHg|bpm|BPM|mg|mL|dL|fL|kg|lbs|ms|mm|cm|%|IU|g"
)
# A measured value: number+unit (28.4 mg/dL, 5.6 %), or a flagged integer (261 H)
VALUE_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:" + UNITS + r")\b"
    r"|\b\d{2,4}\s*(?:H|L|HIGH|LOW)\b"
)


def strip_frontmatter(text: str) -> str:
    m = FRONTMATTER_RE.match(text)
    return text[m.end():] if m else text


def scan(md_file: Path) -> tuple[int, int, str]:
    """Return (measurement_bullets, dated_table_rows, first_sample_line)."""
    body = strip_frontmatter(md_file.read_text(encoding="utf-8"))
    measurement_bullets = dated_table_rows = 0
    sample = ""
    for line in body.split("\n"):
        masked = BACKLINK_RE.sub("  ", line)  # dates inside links are references
        if not ISO_DATE_RE.search(masked):
            continue
        if TABLE_ROW_RE.match(line) and not TABLE_SEPARATOR_RE.match(line):
            dated_table_rows += 1
        elif ROW_KEY_RE.match(line) and VALUE_RE.search(masked):
            measurement_bullets += 1
            if not sample:
                sample = " ".join(line.split())[:100]
    return measurement_bullets, dated_table_rows, sample


def main() -> None:
    list_only: list[tuple[str, int, str]] = []
    mixed: list[tuple[str, int, int, str]] = []

    for md_file in sorted(CONCEPTS_DIR.glob("*.md")):
        bullets, table_rows, sample = scan(md_file)
        if bullets < MEASUREMENT_MIN:
            continue
        rel = str(md_file.relative_to(WIKI_ROOT.parent))
        if table_rows == 0:
            list_only.append((rel, bullets, sample))
        else:
            mixed.append((rel, bullets, table_rows, sample))

    if list_only:
        print("LIST-FORMAT RECORDS (measurement series as bullets, no table — "
              "convert to a Markdown table so they anchor as CANONICAL):")
        for rel, bullets, sample in list_only:
            print(f"  {rel}  ({bullets} measurement bullets)")
            print(f"      e.g. {sample}")
    else:
        print("LIST-FORMAT RECORDS: none")

    print()

    if mixed:
        print("PARTIALLY TABULAR (measurement bullets alongside a dated table — "
              "a series may be split; fold the bullets into the table):")
        for rel, bullets, table_rows, sample in mixed:
            print(f"  {rel}  ({bullets} bullets, {table_rows} table rows)")
            print(f"      e.g. {sample}")
    else:
        print("PARTIALLY TABULAR: none")


if __name__ == "__main__":
    main()
