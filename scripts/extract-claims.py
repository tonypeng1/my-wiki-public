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

WIKI_ROOT = Path(__file__).parent.parent / "wiki"
CONCEPTS_DIR = WIKI_ROOT / "concepts"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
FIELD_RE = re.compile(r"^(\w[\w-]*):\s*(.+)$", re.MULTILINE)

# [[target]] or [[target|display]] — we want the target
BACKLINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
# A Sources-list entry is a bare bullet holding only a backlink
SOURCES_ENTRY_RE = re.compile(r"^\s*-\s*\[\[[^\]]+\]\](?:\s*\([^)]*\))?\s*$")

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

TABLE_ROW_RE = re.compile(r"^\s*\|")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|[\s|:-]+$")

CJK_RE = re.compile(r"[一-鿿]")
HAS_UPPER_RE = re.compile(r"[A-Z]")
MAX_CLAIM_CHARS = 200
MIN_ALIAS_LEN = 4
# How near a numeric claim must sit to a concept mention to count as a claim
# about that concept, rather than an unrelated number elsewhere on the line.
PROXIMITY_CHARS = 120


def parse_frontmatter(text: str) -> dict[str, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    return dict(FIELD_RE.findall(m.group(1)))


def frontmatter_line_count(text: str) -> int:
    """Number of lines occupied by the frontmatter block, for line offsets."""
    m = FRONTMATTER_RE.match(text)
    return text[: m.end()].count("\n") if m else 0


def strip_frontmatter_block(text: str) -> str:
    m = FRONTMATTER_RE.match(text)
    return text[m.end():] if m else text


def split_list_field(value: str) -> list[str]:
    return [item.strip() for item in value.strip("[]").split(",") if item.strip()]


def build_mention_map(files: list[Path]) -> dict[str, str]:
    """Map title/alias -> concept stem.

    Short Latin aliases match too much ordinary prose, so they are kept only
    when they carry an uppercase letter (A1C, AFP, LDL, eGFR) and are then
    matched case-sensitively. CJK is dense enough to keep at any length.

    Aliases claimed by more than one concept are dropped: an ambiguous name
    cannot serve as a join key, and guessing would manufacture false pairs.
    """
    claims: dict[str, set[str]] = {}
    for md_file in files:
        fm = parse_frontmatter(md_file.read_text(encoding="utf-8"))
        names = [md_file.stem, fm.get("title", "")]
        names.extend(split_list_field(fm.get("aliases", "")))
        for name in names:
            name = name.strip()
            if not name:
                continue
            if (len(name) < MIN_ALIAS_LEN and not CJK_RE.search(name)
                    and not HAS_UPPER_RE.search(name)):
                continue
            claims.setdefault(name, set()).add(md_file.stem)
    return {name: next(iter(owners)) for name, owners in claims.items()
            if len(owners) == 1}


def mentioned_concepts(line: str, mention_map: dict[str, str],
                       stems: set[str]) -> dict[str, list[int]]:
    """Concepts this line mentions, mapped to where on the line they appear."""
    found: dict[str, list[int]] = {}
    for m in BACKLINK_RE.finditer(line):
        target = m.group(1).strip()
        if target in stems:
            found.setdefault(target, []).append(m.start())

    lowered = line.lower()
    for name, stem in mention_map.items():
        if CJK_RE.search(name):
            spans = [m.start() for m in re.finditer(re.escape(name), line)]
        elif len(name) < MIN_ALIAS_LEN:
            # Abbreviation: case-sensitive, so "TG" does not match "tg" in prose
            spans = [m.start() for m in
                     re.finditer(rf"(?<!\w){re.escape(name)}(?!\w)", line)]
        else:
            spans = [m.start() for m in
                     re.finditer(rf"(?<!\w){re.escape(name.lower())}(?!\w)", lowered)]
        if spans:
            found.setdefault(stem, []).extend(spans)
    return found


def mask_backlinks(line: str) -> str:
    """Blank out backlink targets, preserving offsets.

    Dates inside targets ([[lab-a1c-2025-10-10]]) are file references, not
    claims. Padding keeps offsets aligned with the original text.
    """
    return BACKLINK_RE.sub(lambda m: " " * len(m.group(0)), line)


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


def condense(line: str) -> str:
    line = " ".join(line.split())
    if len(line) > MAX_CLAIM_CHARS:
        line = line[:MAX_CLAIM_CHARS].rstrip() + " …"
    return line


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
