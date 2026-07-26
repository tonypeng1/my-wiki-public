#!/usr/bin/env python3
"""
Flag dangling [[wikilinks]] — links whose target basename has no matching .md
file anywhere under wiki/.

Obsidian resolves [[name]] by basename across the whole vault, so a concept,
summary, MOC, or query file are ALL valid link targets. This checker resolves
against every .md under wiki/, so those legitimate links pass and only genuinely
unresolvable targets are flagged.

This is the repo's ONLY wikilink resolver. scripts/detect-thin.py used to carry
a second one that knew only wiki/concepts/ and wiki/summaries/, and reported
every [[moc-*]] and query-file link as "missing"; it was removed rather than
fixed, because a corrected version would have been a strict subset of this
checker. A flagged target is therefore both a link to repair and — when the
target names a genuine concept the wiki has not written yet — an article worth
creating, which is how p4c-coverage-check.md sources its missing-article list.

Usage:
  python3 scripts/check-dangling-links.py [PATH ...] [--git-diff]

With no PATH it scans the authored-content surfaces (concepts, summaries, MOCs,
query files, index.md, home.md). --git-diff restricts findings to lines in the
current git diff (untracked files are scanned in full), matching the per-ingest
post-ingest workflow. Read-only; exit code is always 0.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
WIKI = ROOT / "wiki"

# Files SCANNED for dangling links by default (the authored-content surfaces).
DEFAULT_PATHS = [
    WIKI / "concepts",
    WIKI / "summaries",
    WIKI / "mocs",
    WIKI / "queries",
    WIKI / "index.md",
    WIKI / "home.md",
]

FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
# [[target]], [[target|display]], [[target#heading]] — but NOT ![[embeds]].
WIKILINK_RE = re.compile(r"(?<!!)\[\[([^\]|#]+?)(?:[|#][^\]]*)?\]\]")


def _blank_but_keep_lines(match: re.Match[str]) -> str:
    # Replace a matched region with as many blank lines as it spanned so every
    # following line keeps its original 1-based number.
    return "\n" * match.group(0).count("\n")


def strip_frontmatter(text: str) -> str:
    return FRONTMATTER_RE.sub(_blank_but_keep_lines, text, count=1)


def strip_code_fences(text: str) -> str:
    return CODE_FENCE_RE.sub(_blank_but_keep_lines, text)


def normalize(name: str) -> str:
    # Mirror the filename convention (lowercase-hyphenated) so a link's target
    # and a file's stem compare equal regardless of spacing or case.
    return name.strip().lower().replace(" ", "-")


def valid_targets() -> set[str]:
    # Every .md anywhere under wiki/ is a resolvable link target, including the
    # transient sessions/ scratch — a link into it should not be flagged.
    return {normalize(p.stem) for p in WIKI.rglob("*.md")}


def iter_markdown_files(paths: list[Path]) -> list[Path]:
    files: set[Path] = set()
    for path in paths:
        if path.is_file() and path.suffix == ".md":
            files.add(path.resolve())
        elif path.is_dir():
            for md_file in path.rglob("*.md"):
                files.add(md_file.resolve())
    return sorted(files)


def parse_unified_zero_diff(diff_text: str) -> dict[Path, set[int]]:
    changed: dict[Path, set[int]] = {}
    current_file: Path | None = None
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = (ROOT / line[6:]).resolve()
            continue
        if not line.startswith("@@ ") or current_file is None:
            continue
        match = re.search(r"\+(\d+)(?:,(\d+))?", line)
        if not match:
            continue
        start = int(match.group(1))
        count = int(match.group(2) or "1")
        if count == 0:
            continue
        line_numbers = changed.setdefault(current_file, set())
        for number in range(start, start + count):
            line_numbers.add(number)
    return changed


def git_changed_lines(paths: list[Path]) -> dict[Path, set[int]]:
    relative_paths = [str(path.relative_to(ROOT)) for path in paths]
    diff = subprocess.run(
        ["git", "diff", "--unified=0", "--", *relative_paths],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    changed = parse_unified_zero_diff(diff.stdout)

    status = subprocess.run(
        ["git", "status", "--short", "--", *relative_paths],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    for raw_line in status.stdout.splitlines():
        if not raw_line.startswith("?? "):
            continue
        path = (ROOT / raw_line[3:]).resolve()
        try:
            total_lines = path.read_text(encoding="utf-8").count("\n") + 1
        except FileNotFoundError:
            continue
        changed[path] = set(range(1, total_lines + 1))
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List dangling [[wikilinks]] whose target has no .md file under wiki/."
    )
    parser.add_argument("paths", nargs="*", help="Markdown files or directories to scan.")
    parser.add_argument(
        "--git-diff",
        action="store_true",
        help="Only report links on lines in the current git diff. Untracked files are scanned in full.",
    )
    args = parser.parse_args()

    scan_paths = [Path(p).resolve() for p in args.paths] if args.paths else DEFAULT_PATHS
    markdown_files = iter_markdown_files(scan_paths)
    targets = valid_targets()

    if not markdown_files:
        print("No markdown files found.")
        return

    changed_lines_by_file = git_changed_lines(markdown_files) if args.git_diff else {}
    findings: list[tuple[str, int, str, str]] = []

    for md_file in markdown_files:
        if args.git_diff and md_file not in changed_lines_by_file:
            continue
        body = strip_code_fences(strip_frontmatter(md_file.read_text(encoding="utf-8")))
        changed_lines = changed_lines_by_file.get(md_file)
        rel_path = md_file.relative_to(ROOT).as_posix()
        for line_no, line in enumerate(body.splitlines(), start=1):
            if changed_lines is not None and line_no not in changed_lines:
                continue
            for match in WIKILINK_RE.finditer(line):
                target = match.group(1)
                if normalize(target) in targets:
                    continue
                findings.append((rel_path, line_no, target.strip(), line.strip()))

    if not findings:
        print("No dangling wikilinks found.")
        return

    print("DANGLING WIKILINKS")
    print("(Target basename matches no .md file anywhere under wiki/.)")
    print()
    for rel_path, line_no, target, context in findings:
        snippet = context[:160] + ("..." if len(context) > 160 else "")
        print(f"{rel_path}:{line_no}  [[{target}]]")
        print(f"  {snippet}")


if __name__ == "__main__":
    main()
