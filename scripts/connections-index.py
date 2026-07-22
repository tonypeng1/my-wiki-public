#!/usr/bin/env python3
"""
Generate a compact connections view of all wiki concept files for Task 3
(Missing Backlinks analysis).

For each concept, outputs:
  - filename, title, tags  (one-line header from tag-index format)
  - the existing ## Connections section verbatim

This gives the LLM everything it needs to identify missing substantive
backlinks — what each concept covers and what it already links to —
without loading 191 KB of full article bodies.

Approximate size: ~35 KB vs ~190 KB for full concept files (~80% savings).
"""

import re
from pathlib import Path

WIKI_ROOT = Path(__file__).parent.parent / "wiki"
CONCEPTS_DIR = WIKI_ROOT / "concepts"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
FIELD_RE = re.compile(r"^(\w[\w-]*):\s*(.+)$", re.MULTILINE)
OVERVIEW_RE = re.compile(r"## Overview\s*\n(.*?)(?:\n## |\Z)", re.DOTALL)
CONNECTIONS_RE = re.compile(r"## Connections\s*\n(.*?)(?:\n## |\Z)", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, str]:
    m = FRONTMATTER_RE.match(text)
    return dict(FIELD_RE.findall(m.group(1))) if m else {}


def first_sentence(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    for s in sentences:
        s = s.strip().replace("\n", " ")
        if s:
            return s[:120] + ("…" if len(s) > 120 else "")
    return ""


def section_text(text: str, pattern: re.Pattern) -> str:
    m = pattern.search(text)
    return m.group(1).strip() if m else "(none)"


def main() -> None:
    entries = []
    for md_file in sorted(CONCEPTS_DIR.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)

        title = fm.get("title", md_file.stem)
        tags = fm.get("tags", "").strip("[]")
        overview_hint = first_sentence(section_text(text, OVERVIEW_RE))
        connections = section_text(text, CONNECTIONS_RE)

        entries.append(
            f"### {md_file.name}  [{tags}]\n"
            f"{title} — {overview_hint}\n"
            f"Connections:\n{connections}\n"
        )

    print("\n".join(entries))


if __name__ == "__main__":
    main()
