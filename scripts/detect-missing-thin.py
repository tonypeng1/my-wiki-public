#!/usr/bin/env python3
"""
Pre-filter for p4-lint Task 2: identify missing and thin concept pages
without sending any file content to the LLM.

Outputs:
  MISSING CONCEPTS — [[backlinks]] referenced in concept files that have
                     no corresponding file in wiki/concepts/
  THIN CONCEPTS    — concept files with fewer than 150 words of body
                     content (frontmatter excluded)

Exit code 0 in all cases. Output is intended to be read by the LLM
to scope which files actually need to be loaded.
"""

import re
import sys
from pathlib import Path

WIKI_ROOT = Path(__file__).parent.parent / "wiki"
CONCEPTS_DIR = WIKI_ROOT / "concepts"
SUMMARIES_DIR = WIKI_ROOT / "summaries"
THIN_THRESHOLD = 150  # words

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:[|#][^\]]*)?\]\]")


def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter block (between opening and closing ---)."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:]
    return text


def word_count(text: str) -> int:
    return len(text.split())


def filename_from_link(link: str) -> str:
    """Convert a [[wikilink]] target to an expected filename."""
    return link.strip().lower().replace(" ", "-") + ".md"


def main() -> None:
    concept_files = {f.name for f in CONCEPTS_DIR.glob("*.md")}
    summary_files = {f.name for f in SUMMARIES_DIR.glob("*.md")}
    all_wiki_files = concept_files | summary_files

    missing: dict[str, list[str]] = {}   # concept_filename → [referencing files]
    thin: list[tuple[str, int]] = []     # (relative path, word count)

    for md_file in sorted(CONCEPTS_DIR.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        body = strip_frontmatter(text)

        # --- thin detection ---
        wc = word_count(body)
        if wc < THIN_THRESHOLD:
            thin.append((str(md_file.relative_to(WIKI_ROOT.parent)), wc))

        # --- missing backlink detection ---
        for link in WIKILINK_RE.findall(body):
            target_file = filename_from_link(link)
            if target_file not in all_wiki_files:
                missing.setdefault(target_file, []).append(md_file.name)

    # --- report ---
    if missing:
        print("MISSING CONCEPTS (referenced but no file in wiki/concepts/):")
        for fname, refs in sorted(missing.items()):
            ref_str = ", ".join(sorted(set(refs)))
            print(f"  {fname}  ← referenced in: {ref_str}")
    else:
        print("MISSING CONCEPTS: none")

    print()

    if thin:
        print(f"THIN CONCEPTS (< {THIN_THRESHOLD} words of body content):")
        for path_str, wc in thin:
            print(f"  {path_str}  ({wc} words)")
    else:
        print("THIN CONCEPTS: none")


if __name__ == "__main__":
    main()
