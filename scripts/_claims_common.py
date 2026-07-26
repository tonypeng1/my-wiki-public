#!/usr/bin/env python3
"""
Shared machinery for the claim-extraction checkers.

Two scripts ask the same structural question — "which concept is this line
making a claim about?" — and differ only in what counts as a claim:

  extract-claims.py         numeric/date values   -> contradiction check
  extract-status-claims.py  state words           -> status contradiction check

Everything neutral to that choice lives here: frontmatter parsing, the
title/alias mention map, backlink masking, the proximity test, and line
condensing. Neither checker's notion of a "claim" belongs in this module.

Not a CLI — importing scripts run it, and it prints nothing on its own.
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

TABLE_ROW_RE = re.compile(r"^\s*\|")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|[\s|:-]+$")

CJK_RE = re.compile(r"[一-鿿]")
HAS_UPPER_RE = re.compile(r"[A-Z]")
MAX_CLAIM_CHARS = 200
MIN_ALIAS_LEN = 4
# How near a claim must sit to a concept mention to count as a claim about
# that concept, rather than an unrelated assertion elsewhere on the line.
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


# Aliases naming a drug CLASS rather than the drug itself. Every medication
# concept here lists its class among its aliases, which is right for Obsidian
# search but wrong as a join key: it makes a general statement like "statins
# are usually continued indefinitely" look like a claim about whichever statin
# concept carries that alias. Harmless while exactly one drug per class is on
# the list, misleading in general-knowledge prose — and wrong outright the day
# a second one is added.
CLASS_ALIASES = frozenset({
    "statin", "hmg-coa reductase inhibitor", "史他汀類藥物", "hmg-coa 還原酶抑制劑",
    "beta-blocker", "beta blocker", "β-blocker", "β1-blocker",
    "cardioselective beta blocker", "β阻斷劑", "心臟選擇性β阻斷劑",
    "benzodiazepine", "bzd", "苯二氮平類",
    "tricyclic antidepressant", "tca",
    "biguanide", "雙胍類",
    "sari", "serotonin antagonist reuptake inhibitor",
})


def build_mention_map(files: list[Path],
                      exclude: frozenset = frozenset()) -> dict[str, str]:
    """Map title/alias -> concept stem.

    `exclude` drops names (compared lowercased) from the map — see
    CLASS_ALIASES. It defaults to empty so callers opt in deliberately.

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
            if not name or name.lower() in exclude:
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

    Dates and words inside targets ([[lab-a1c-2025-10-10]], [[fatty-liver]])
    are file references, not claims. Padding keeps offsets aligned with the
    original text.
    """
    return BACKLINK_RE.sub(lambda m: " " * len(m.group(0)), line)


def condense(line: str, limit: int = MAX_CLAIM_CHARS) -> str:
    line = " ".join(line.split())
    if len(line) > limit:
        line = line[:limit].rstrip() + " …"
    return line
