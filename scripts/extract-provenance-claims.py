#!/usr/bin/env python3
"""
Cross-check the provenance stated in concept tables against the summaries
those rows cite.

A concept's canonical table restates provenance the summary already records in
frontmatter: the `Lab` cell names the site, the `Notes` cell often names the
ordering physician, and the row backlinks to the summary for that draw. That
makes every such row a claim that can disagree with its source — the same drift
shape the numeric pass catches, on a different field.

  | 2011-03-14 | <lab> | ... | Dr. <name> ([[lab-lipid-panel-2011-03-14]]) |
                 ^^^^^              ^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^^^^^
                 facility           physician    the summary being cited

NEITHER SIDE IS AUTHORITY. Unlike the numeric pass, there is no canonical row
to referee this: the summary fields were migrated from a hand-written tag layer
that was demonstrably lossy (one clinic appears in five concept rows and was
never a tag at all), while the concept cell was hand-written too. Every finding
here is Tier B by construction. The script reports; it never rewrites.

Three kinds:

  MISMATCH   — row and summary both state a value and they differ. The most
               common benign cause is NOT an error: `facility` is the site that
               PERFORMED the study while a concept row may name the ordering
               clinic, so a clinic-vs-reference-lab disagreement on a specimen
               one drew and the other ran is correct on both sides. Check that
               before treating it as drift.

  UNRECORDED — the row names a site or clinician and the cited summary has no
               such field. These are the backfill leads: the concept table is
               the only place the wiki still records that provenance.

  UNKNOWN     — the row names a site outside the closed vocabulary in CLAUDE.md.
                Either a real facility never added, or a display form this
                script does not know.

Rows with no backlink to a summary are skipped: a claim with no source cannot
be compared to one.
"""

import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).parent))
from _claims_common import (  # noqa: E402
    BACKLINK_RE,
    CONCEPTS_DIR,
    TABLE_ROW_RE,
    TABLE_SEPARATOR_RE,
    WIKI_ROOT,
    condense,
    frontmatter_line_count,
    parse_frontmatter,
)

sys.path.insert(0, str(Path(__file__).parent))
from _provenance_vocab import (  # noqa: E402
    VocabularyError,
    facility_forms,
    physician_forms,
)

SUMMARIES_DIR = WIKI_ROOT / "summaries"


class Matchers(NamedTuple):
    """Compiled recognizers for the two vocabularies, built from CLAUDE.md.

    The facility and physician rosters are the patient's real clinics and
    clinicians, and this file ships to the public repo — so they are read from
    CLAUDE.md, which does not ship. See _provenance_vocab.py.
    """

    facility: dict[str, re.Pattern[str]]   # slug -> recognizer for its Lab cell
    physician: re.Pattern[str]             # one alternation over every name form
    physician_slug: dict[str, str]         # matched name form -> slug


def load_matchers() -> Matchers:
    forms = facility_forms()
    names = physician_forms()
    return Matchers(
        facility={
            slug: re.compile(
                r"(?<![A-Za-z])(?:%s)(?![A-Za-z])" % "|".join(map(re.escape, f))
            )
            for slug, f in forms.items()
        },
        # Longest-first so `Dr. Chen Wei-Ming` cannot match a shorter form that
        # is a prefix of the name actually written.
        physician=re.compile(
            r"Dr\.?\s+(?:[A-Z][a-z]+\s+)?(%s)\b"
            % "|".join(map(re.escape, sorted(names, key=len, reverse=True)))
        ),
        physician_slug=names,
    )


def field_values(raw: str) -> set[str]:
    """Parse a field value into its slugs; `physician` may be a flow-style list."""
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        return {v.strip().strip("\"'") for v in raw[1:-1].split(",") if v.strip()}
    return {raw.strip("\"'")}


def load_summaries() -> dict[str, dict[str, set[str]]]:
    out: dict[str, dict[str, set[str]]] = {}
    for md in sorted(SUMMARIES_DIR.glob("*.md")):
        fm = parse_frontmatter(md.read_text(encoding="utf-8"))
        out[md.stem] = {
            k: field_values(fm[k]) for k in ("facility", "physician") if k in fm
        }
    return out


# Header cell naming the column that records where the study was performed.
# NOT `Site`: in this vault a Site column is anatomical — `L2–L4`, `Left CCA
# bulb`, `Sigmoid colon (乙狀結腸)` — and reading it as a facility column makes
# every body part an unknown clinic.
LAB_HEADER_RE = re.compile(r"^\**\s*(lab|facility)\s*\**$", re.I)


def cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def lab_column(header: list[str]) -> int | None:
    for i, cell in enumerate(header):
        if LAB_HEADER_RE.match(cell):
            return i
    return None


def claims_in_row(cells_: list[str], lab_col: int | None,
                  mx: Matchers) -> tuple[set[str], set[str]]:
    """Facility slugs and physician slugs asserted by one table row.

    The facility is read ONLY from the Lab column. A facility named anywhere
    else in the row is usually a reference-range attribution — a value written
    `1.00 (<lab> equiv.)` says whose normal range is being applied, not who ran
    the test — and reading the whole row turns every one of those into a false
    claim. A physician is read row-wide: a `Dr. <name>` in a Notes cell is
    unambiguous, and no table column attributes a range to a clinician.
    """
    row = " | ".join(cells_)
    facilities: set[str] = set()
    if lab_col is not None and lab_col < len(cells_):
        cell = cells_[lab_col]
        facilities = {slug for slug, rx in mx.facility.items() if rx.search(cell)}
    physicians = {mx.physician_slug[m] for m in mx.physician.findall(row)}
    return facilities, physicians


NULL_CELLS = {"", "—", "-", "–", "?", "n/a", "N/A"}


def unknown_facility(cells_: list[str], lab_col: int | None,
                     mx: Matchers) -> str | None:
    """A Lab-column cell naming no known facility, or None."""
    if lab_col is None or lab_col >= len(cells_):
        return None
    cell = cells_[lab_col]
    if cell in NULL_CELLS:
        return None
    if any(rx.search(cell) for rx in mx.facility.values()):
        return None
    return cell


def main() -> int:
    try:
        mx = load_matchers()
    except VocabularyError as exc:
        print(f"CANNOT CHECK: {exc}")
        return 1

    summaries = load_summaries()

    mismatch: list[str] = []
    unrecorded: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    unknown: dict[str, list[str]] = defaultdict(list)
    n_rows = 0
    n_compared = 0

    for md in sorted(CONCEPTS_DIR.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        offset = frontmatter_line_count(text)
        rel = md.relative_to(WIKI_ROOT.parent)

        lab_col: int | None = None
        prev_cells: list[str] = []

        for i, line in enumerate(text.split("\n")[offset:], start=offset + 1):
            if not TABLE_ROW_RE.match(line):
                lab_col, prev_cells = None, []
                continue
            if TABLE_SEPARATOR_RE.match(line):
                lab_col = lab_column(prev_cells)
                continue
            row_cells = cells(line)
            prev_cells = row_cells

            cited = [t for t in BACKLINK_RE.findall(line) if t in summaries]
            if not cited:
                continue
            n_rows += 1

            odd = unknown_facility(row_cells, lab_col, mx)
            if odd is not None:
                unknown[odd].append(f"{rel}:{i}")

            row_fac, row_phys = claims_in_row(row_cells, lab_col, mx)
            if not row_fac and not row_phys:
                continue
            n_compared += 1

            for field, claimed in (("facility", row_fac), ("physician", row_phys)):
                if not claimed:
                    continue
                recorded = {
                    v for c in cited for v in summaries[c].get(field, ())
                }
                where = f"{rel}:{i}"
                shown = ", ".join(sorted(claimed))
                if not recorded:
                    for c in cited:
                        unrecorded[(field, c)].append((shown, where))
                elif not (claimed & recorded):
                    mismatch.append(
                        f"  {where}\n"
                        f"    concept row says   {field}: {shown}\n"
                        f"    cited summary says {field}: {', '.join(sorted(recorded))}\n"
                        f"    cites             {', '.join(cited)}\n"
                        f"    {condense(line.strip())}"
                    )

    print(
        f"Scanned {n_rows} concept table row(s) citing a summary; "
        f"{n_compared} state a facility or physician."
    )

    if mismatch:
        print(f"\nMISMATCH — {len(mismatch)} row(s) disagree with the summary they cite.")
        print("Neither side is authority. Before calling it drift, check whether the")
        print("concept row names the ORDERING clinic while `facility` records the")
        print("PERFORMING site — that pairing is correct on both sides.\n")
        print("\n\n".join(mismatch))
    else:
        print("\nMISMATCH: none.")

    if unrecorded:
        conflicted = sum(1 for v in unrecorded.values() if len({c for c, _ in v}) > 1)
        print(
            f"\nUNRECORDED — {len(unrecorded)} field(s) the concept tables assert and "
            f"the cited summary does not record."
        )
        print("These are backfill leads: confirm against the raw/ source, then set the")
        print("field on the summary. Do not copy the concept cell across unverified.")
        if conflicted:
            print(
                f"{conflicted} of them {'is' if conflicted == 1 else 'are'} marked "
                f"CONFLICTING — the concept rows do not "
                f"agree with\neach other, so at most one can be copied and the source "
                f"has to settle it."
            )
        print()
        for (field, summary), rows in sorted(unrecorded.items()):
            values = sorted({c for c, _ in rows})
            flag = "  ← CONFLICTING" if len(values) > 1 else ""
            print(f"  {summary}  has no {field}{flag}")
            for value in values:
                wheres = sorted({w for c, w in rows if c == value})
                print(f"    concept rows say {field}: {value}")
                for w in wheres[:4]:
                    print(f"      {w}")
                if len(wheres) > 4:
                    print(f"      +{len(wheres) - 4} more")
    else:
        print("\nUNRECORDED: none.")

    if unknown:
        print(f"\nUNKNOWN — {len(unknown)} Lab-column value(s) outside the vocabulary.")
        print("Either a real facility never added to CLAUDE.md, or a display form this")
        print("script does not know — add it to that row's `Also written` column rather")
        print("than editing the concept table to suit the checker.\n")
        for cell, wheres in sorted(unknown.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            print(f"  {cell!r}  {len(wheres)} row(s)")
            for w in wheres[:3]:
                print(f"      {w}")
    else:
        print("\nUNKNOWN: none.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
