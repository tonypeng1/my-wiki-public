#!/usr/bin/env python3
"""
Pre-filter for the thin-article pass in p4c-coverage-check.md and p4-lint.md:
identify under-developed concept pages without sending any file content to
the LLM.

Output:
  THIN CONCEPTS — concept files with fewer than 150 words of body content
                  (frontmatter excluded)

This script does NOT resolve [[wikilinks]]. Link validation — including the
"referenced but no file exists" case that names an article worth creating —
belongs to scripts/check-dangling-links.py, which resolves a target by
basename across the whole vault the way Obsidian does. An earlier version of
this script carried its own resolver that knew only wiki/concepts/ and
wiki/summaries/, so it reported every legitimate [[moc-*]] and query-file link
as missing. Two resolvers meant two answers; there is now one.

Exit code 0 in all cases. Output is intended to be read by the LLM
to scope which files actually need to be loaded.
"""

from pathlib import Path

WIKI_ROOT = Path(__file__).parent.parent / "wiki"
CONCEPTS_DIR = WIKI_ROOT / "concepts"
THIN_THRESHOLD = 150  # words


def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter block (between opening and closing ---)."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:]
    return text


def word_count(text: str) -> int:
    return len(text.split())


def main() -> None:
    thin: list[tuple[str, int]] = []  # (relative path, word count)

    for md_file in sorted(CONCEPTS_DIR.glob("*.md")):
        body = strip_frontmatter(md_file.read_text(encoding="utf-8"))
        wc = word_count(body)
        if wc < THIN_THRESHOLD:
            thin.append((str(md_file.relative_to(WIKI_ROOT.parent)), wc))

    if thin:
        print(f"THIN CONCEPTS (< {THIN_THRESHOLD} words of body content):")
        for path_str, wc in thin:
            print(f"  {path_str}  ({wc} words)")
    else:
        print("THIN CONCEPTS: none")


if __name__ == "__main__":
    main()
