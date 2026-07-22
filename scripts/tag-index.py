#!/usr/bin/env python3
"""
Generate a compact tag/title index of all wiki concepts and summaries.

Output is a plain-text table with one line per file:
  <filename> | <title-or-source> | <date> | <tags>

For concepts:  title comes from the `title:` frontmatter field;
               first sentence of the Overview is appended as a hint.
For summaries: title comes from the `source:` field; date from `date-added:`.

This replaces bulk file loading for Task 6 (MOC Freshness): the LLM only
needs filename, tags, and a short description to check MOC coverage and
compose one-line MOC entries.
"""

import re
import sys
from pathlib import Path

WIKI_ROOT = Path(__file__).parent.parent / "wiki"
CONCEPTS_DIR = WIKI_ROOT / "concepts"
SUMMARIES_DIR = WIKI_ROOT / "summaries"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
FIELD_RE = re.compile(r"^(\w[\w-]*):\s*(.+)$", re.MULTILINE)
OVERVIEW_HEADING_RE = re.compile(r"## Overview\s*\n(.*?)(?:\n##|\Z)", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    return dict(FIELD_RE.findall(m.group(1)))


def first_sentence(text: str) -> str:
    """Return the first non-empty sentence (up to 120 chars)."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    for s in sentences:
        s = s.strip().replace("\n", " ")
        if s:
            return s[:120] + ("…" if len(s) > 120 else "")
    return ""


def overview_hint(text: str) -> str:
    """Extract first sentence of the ## Overview section."""
    m = OVERVIEW_HEADING_RE.search(text)
    if not m:
        return ""
    return first_sentence(m.group(1))


def strip_frontmatter_block(text: str) -> str:
    m = FRONTMATTER_RE.match(text)
    return text[m.end():] if m else text


def process_concepts() -> list[str]:
    lines = ["=== CONCEPTS ===",
             f"{'filename':<45} {'title':<40} {'tags'}"]
    lines.append("-" * 120)
    for md_file in sorted(CONCEPTS_DIR.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        title = fm.get("title", md_file.stem)
        tags = fm.get("tags", "").strip("[]")
        hint = overview_hint(text)
        # Pack title + hint into description column
        desc = title if not hint else f"{title} — {hint}"
        lines.append(f"{md_file.name:<45} {desc:<80} [{tags}]")
    return lines


def process_summaries() -> list[str]:
    lines = ["", "=== SUMMARIES ===",
             f"{'filename':<50} {'source / date':<45} {'tags'}"]
    lines.append("-" * 120)
    for md_file in sorted(SUMMARIES_DIR.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        source = fm.get("source", md_file.stem)
        date = fm.get("date-added", "")
        tags = fm.get("tags", "").strip("[]")
        label = f"{source}  {date}" if date else source
        lines.append(f"{md_file.name:<50} {label:<45} [{tags}]")
    return lines


def main() -> None:
    concept_lines = process_concepts()
    summary_lines = process_summaries()
    output = "\n".join(concept_lines + summary_lines)
    print(output)


if __name__ == "__main__":
    main()
