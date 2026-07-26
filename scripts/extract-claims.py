#!/usr/bin/env python3
"""
Extract every numeric/date claim in wiki/concepts/, grouped by the concept
each claim is about.

Output is one block per concept:

  === vitamin-d ===
  CANONICAL  wiki/concepts/vitamin-d.md
    L27  | 2020-03-11 | LabA | VD-25OH | 28.4 | LOW | ...
  RESTATEMENTS
    bone-density.md:44  vitamin D has been below 30 at every draw ...

CANONICAL lines come from the concept's own file (its longitudinal table is
the authoritative record). RESTATEMENTS are claims other files make about the
same concept — that is where drift lives: the canonical table gets updated and
the restatement does not.

This replaces the bulk read in p4b-contradiction-check.md step 1. The prompt
only needs claims paired with their counterparts, not the whole concept corpus.
Blocks with no restatement are omitted: a concept nobody else cites cannot
have a cross-file contradiction.
"""

import re
from pathlib import Path

from _claims_common import (
    CONCEPTS_DIR,
    SOURCES_ENTRY_RE,
    TABLE_ROW_RE,
    TABLE_SEPARATOR_RE,
    PROXIMITY_CHARS,
    build_mention_map,
    condense,
    frontmatter_line_count,
    mask_backlinks,
    mentioned_concepts,
    strip_frontmatter_block,
)

UNITS = (
    r"mg/dL|mmol/L|U/L|IU/L|mg|mL|dL|mmHg|kg|lbs|bpm|BPM|ms|mm|cm|%|IU|g"
)
# What counts as a numeric claim in prose
CLAIM_RE = re.compile(
    r"""
      \d+\.\d+                      # decimal value: 28.4, 5.2
    | \d{4}-\d{2}-\d{2}             # ISO date
    | \d+\s*(?:""" + UNITS + r""")\b   # value with unit
    | \d+\s*[–—-]\s*\d+             # range: 100–125
    | \d+\s*(?:→|->)\s*\d+          # series: 110 → 92
    | \b\d{2,3}\s*(?:H|L|HIGH|LOW)\b   # flagged integer: 261 H
    """,
    re.VERBOSE,
)

def claim_positions(line: str) -> list[int]:
    """Offsets of numeric claims on the line."""
    return [m.start() for m in CLAIM_RE.finditer(mask_backlinks(line))]


def claim_values(line: str) -> list[str]:
    """The numeric claims themselves, deduped, in order of appearance.

    Used to sort peer blocks so that restatements asserting the same value
    cluster together and outliers stand out without reading the prose.
    """
    seen: dict[str, None] = {}
    for m in CLAIM_RE.finditer(mask_backlinks(line)):
        seen.setdefault(" ".join(m.group(0).split()), None)
    return list(seen)


def collect_claims(files: list[Path], mention_map: dict[str, str],
                   stems: set[str]) -> tuple[dict, dict]:
    """Return (canonical, restatements), each keyed by concept stem.

    Restatement entries are (values, label, text) so peer blocks can be
    sorted by asserted value.
    """
    canonical: dict[str, list[str]] = {}
    restatements: dict[str, list[tuple[list[str], str, str]]] = {}

    for md_file in files:
        text = md_file.read_text(encoding="utf-8")
        offset = frontmatter_line_count(text)

        for i, line in enumerate(strip_frontmatter_block(text).split("\n"),
                                 start=offset + 1):
            if not line.strip() or SOURCES_ENTRY_RE.match(line):
                continue
            claims = claim_positions(line)
            if not claims:
                continue

            # A table row in a concept's own file is its authoritative record
            if TABLE_ROW_RE.match(line) and not TABLE_SEPARATOR_RE.match(line):
                canonical.setdefault(md_file.stem, []).append(
                    f"  L{i:<4} {condense(line)}"
                )
                continue

            for subject, mentions in mentioned_concepts(line, mention_map, stems).items():
                if subject == md_file.stem:
                    continue  # own-file prose; the table above is the record
                # Only a claim standing near the mention is a claim ABOUT it
                if not any(abs(c - p) <= PROXIMITY_CHARS
                           for c in claims for p in mentions):
                    continue
                restatements.setdefault(subject, []).append(
                    (claim_values(line), f"{md_file.name}:{i}", condense(line))
                )
    return canonical, restatements


def main() -> None:
    files = sorted(CONCEPTS_DIR.glob("*.md"))
    stems = {f.stem for f in files}
    mention_map = build_mention_map(files)
    canonical, restatements = collect_claims(files, mention_map, stems)

    out: list[str] = []
    anchored = peer = 0
    for stem in sorted(restatements):
        own = canonical.get(stem, [])
        entries = restatements[stem]

        if own:
            # Anchored: the concept's own table is the record to compare against
            anchored += 1
            out.append(f"=== {stem} ===")
            out.append(f"CANONICAL  wiki/concepts/{stem}.md")
            out.extend(own)
            out.append("RESTATEMENTS")
            out.extend(f"  {label}  {text}" for _, label, text in entries)
            out.append("")
            continue

        # Peer: no table to referee, so the restatements judge each other.
        # A lone claim has nothing to disagree with — drop it.
        if len(entries) < 2:
            continue
        peer += 1
        out.append(f"=== {stem} ===")
        out.append(f"PEER CLAIMS  wiki/concepts/{stem}.md has no longitudinal table")
        out.append("  Compare these against EACH OTHER; none is authoritative.")
        for values, label, text in sorted(entries, key=lambda e: e[0]):
            out.append(f"  [{', '.join(values)}]")
            out.append(f"    {label}  {text}")
        out.append("")

    header = [
        f"Concept files scanned: {len(files)}",
        f"Blocks emitted: {anchored + peer}  ({anchored} anchored, {peer} peer)",
        f"Canonical claim lines: {sum(len(v) for v in canonical.values())}",
        f"Restatement claim lines: {sum(len(v) for v in restatements.values())}",
        "",
        "ANCHORED blocks: compare each RESTATEMENT against the CANONICAL rows.",
        "PEER blocks: no canonical table exists; compare the claims against each",
        "other. Asserted values are shown in [brackets] and sorted so that",
        "agreeing claims cluster and outliers stand apart.",
        "Claim text is condensed; open file:line for the verbatim statement.",
        "",
    ]
    try:
        print("\n".join(header + out))
    except BrokenPipeError:
        pass  # output was piped into head/grep and the reader closed early


if __name__ == "__main__":
    main()
