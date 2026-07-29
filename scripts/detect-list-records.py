#!/usr/bin/env python3
"""
Pre-filter for p4a-post-ingest and p4-lint: find concept files whose
recurring-measurement record is written as a bulleted list instead of a
Markdown table.

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
value: a number with a unit, a flagged value, a bare decimal, or a
score/ratio/index keyword with a number (see VALUE_RE — dimensionless results
are canonical too, per the Key Details rule in CLAUDE.md). Event bullets lead
with a label and are skipped.

Outputs:
  LIST-FORMAT RECORDS  — >= MEASUREMENT_MIN measurement bullets, no dated table
  PARTIALLY TABULAR    — measurement bullets alongside a dated table (split
                         series); any stray bullet counts, MEASUREMENT_MIN
                         does not gate this tier
  SINGLE VALUE AS BULLET — exactly one measurement bullet and no table

The three tiers are ordered by confidence, and the last is the weakest: one
bullet is one coincidence away from a false positive (a lone date-led decimal
such as "2020-01-03 followed for 2.5 years" lands here). It is reported anyway
because the Key Details rule in CLAUDE.md requires a one-row table even for a
single result, and because a value that never repeats is the one most likely to
be left as prose. Read this tier as a question, the other two as findings.

Known blind spots. This is a pre-filter, not a proof: a clean run means nothing
matched the shape below, not that every record is tabular. It does not see
  - a bare unit-less INTEGER with no flag and no SCORE_WORDS keyword nearby
    ("nodule count 3") — bare decimals and keyworded numbers do count;
  - integer values with units outside UNITS ("140 mEq/L") — extend the list as
    they appear (decimal values match the bare-decimal branch regardless of
    unit);
  - flagged values outside 2-4 digits ("5 H", "15000 H");
  - non-ISO dates ("Mar 2024"), which the row key does not recognize.
The date-led requirement above is a deliberate trade: it buys silence on event
bullets at the cost of missing a measurement bullet written behind a label.
The bare-decimal branch trades the other way: a date-led event bullet that
happens to carry a decimal counts as a measurement. MEASUREMENT_MIN keeps a
lone one out of the two stronger tiers, and the output is a candidate list for
the LLM, not a verdict.

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
# Dimensionless results (ratios, indices, scores) carry no unit but are
# canonical values all the same. Keyword labels seen in this vault's concepts;
# extend like UNITS as new ones appear.
SCORE_WORDS = r"ratio|score|index|AHI|RDI|ODI|BMI|PLMI"

# A measured value, any of:
#   number + unit      28.4 mg/dL, 9.47 %  (unit closed with a lookahead, not
#                      \b: `%` is a non-word char, so \b after it never matches)
#   flagged integer    318 H, 89 LOW
#   bare decimal       1.28, +0.37, -1.93  (dimensionless ratios and T-scores)
#   keyworded number   ratio 3.11, Agatston score 407, AHI 31 — tolerating the
#                      Chinese parenthetical the translation convention puts
#                      between term and value: "AHI (呼吸中止低通氣指數) 31"
# A bare unit-less INTEGER with neither flag nor keyword stays unmatched on
# purpose: a date-led event bullet ("2024-03-28 follow-up in 3 months") must
# not count as a measurement.
VALUE_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:" + UNITS + r")(?![A-Za-z0-9])"
    r"|\b\d{2,4}\s*(?:H|L|HIGH|LOW)\b"
    r"|\b\d+\.\d+\b"
    r"|\b(?i:" + SCORE_WORDS + r")(?:\s*\([^)]*\)){0,2}(?:\s+of)?\s*[:=]?\s*[-−+]?\d+(?:\.\d+)?"
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
    single: list[tuple[str, str]] = []

    for md_file in sorted(CONCEPTS_DIR.glob("*.md")):
        bullets, table_rows, sample = scan(md_file)
        if bullets == 0:
            continue
        rel = str(md_file.relative_to(WIKI_ROOT.parent))
        if table_rows:
            # A stray bullet beside a table is split-series drift whether it is
            # one row or ten, so this tier does not wait for MEASUREMENT_MIN.
            mixed.append((rel, bullets, table_rows, sample))
        elif bullets >= MEASUREMENT_MIN:
            list_only.append((rel, bullets, sample))
        else:
            single.append((rel, sample))

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

    print()

    if single:
        print("SINGLE VALUE AS BULLET (one measurement bullet, no table — the "
              "Key Details rule wants a one-row table even for one result):")
        for rel, sample in single:
            print(f"  {rel}")
            print(f"      {sample}")
    else:
        print("SINGLE VALUE AS BULLET: none")


if __name__ == "__main__":
    main()
