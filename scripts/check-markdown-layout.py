#!/usr/bin/env python3
"""Flag manually hard-wrapped prose in authored wiki Markdown.

The wiki convention is one physical source line per prose paragraph or list
item. Obsidian performs visual soft wrapping. Keeping source blocks unwrapped
also prevents a later bilingual pass from lengthening only selected lines and
leaving an irregular staircase of hard wraps.

Usage:
  python3 scripts/check-markdown-layout.py [PATH ...] [--git-diff]

With no PATH, scan the authored wiki surfaces. ``--git-diff`` reports only a
hard-wrapped block that intersects a changed line; untracked files are scanned
in full. YAML frontmatter, tables, fenced code, blockquotes, headings, thematic
breaks, and nested list items are excluded. Read-only; exit code is always 0.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).parent.parent
WIKI = ROOT / "wiki"

DEFAULT_PATHS = [
    WIKI / "concepts",
    WIKI / "summaries",
    WIKI / "mocs",
    WIKI / "queries",
    WIKI / "index.md",
    WIKI / "home.md",
]

FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^\s*#{1,6}\s+")
LIST_RE = re.compile(r"^(\s*)(?:[-+*]|\d+[.)])\s+")
THEMATIC_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
HTML_RE = re.compile(r"^\s*</?[A-Za-z][^>]*>\s*$")


@dataclass(frozen=True)
class Finding:
    path: Path
    start: int
    end: int
    kind: str
    text: str


def iter_markdown_files(paths: list[Path]) -> list[Path]:
    files: set[Path] = set()
    for path in paths:
        if path.is_file() and path.suffix == ".md":
            files.add(path.resolve())
        elif path.is_dir():
            files.update(md_file.resolve() for md_file in path.rglob("*.md"))
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
        changed.setdefault(current_file, set()).update(range(start, start + count))
    return changed


def git_changed_lines(paths: list[Path]) -> dict[Path, set[int]]:
    relative_paths = [str(path.relative_to(ROOT)) for path in paths]
    diff = subprocess.run(
        ["git", "diff", "--unified=0", "--", *relative_paths],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    changed = parse_unified_zero_diff(diff.stdout)

    status = subprocess.run(
        ["git", "status", "--short", "--", *relative_paths],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    for raw_line in status.stdout.splitlines():
        if not raw_line.startswith("?? "):
            continue
        path = (ROOT / raw_line[3:]).resolve()
        try:
            total = len(path.read_text(encoding="utf-8").splitlines())
        except FileNotFoundError:
            continue
        changed[path] = set(range(1, total + 1))
    return changed


def leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def is_structural(line: str) -> bool:
    stripped = line.strip()
    return bool(
        not stripped
        or HEADING_RE.match(line)
        or THEMATIC_RE.match(line)
        or stripped.startswith("|")
        or stripped.startswith(">")
        or HTML_RE.match(line)
    )


def visible_lines(lines: list[str]) -> list[str | None]:
    """Blank frontmatter and fenced code while preserving line numbers."""
    visible: list[str | None] = []
    in_frontmatter = bool(lines and lines[0].strip() == "---")
    in_fence = False
    for index, line in enumerate(lines):
        if in_frontmatter:
            visible.append(None)
            if index > 0 and line.strip() == "---":
                in_frontmatter = False
            continue

        if FENCE_RE.match(line):
            in_fence = not in_fence
            visible.append(None)
            continue
        if in_fence:
            visible.append(None)
            continue
        visible.append(line)
    return visible


def normalize_excerpt(lines: list[str]) -> str:
    text = " ".join(line.strip() for line in lines)
    text = re.sub(r"\s+", " ", text)
    return text[:180] + ("..." if len(text) > 180 else "")


def scan_file(path: Path) -> list[Finding]:
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    lines = visible_lines(raw_lines)
    findings: list[Finding] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        if line is None or is_structural(line):
            index += 1
            continue

        list_match = LIST_RE.match(line)
        if list_match:
            base_indent = len(list_match.group(1))
            end = index + 1
            while end < len(lines):
                candidate = lines[end]
                if candidate is None or is_structural(candidate):
                    break
                if LIST_RE.match(candidate):
                    break
                if leading_spaces(candidate) <= base_indent:
                    break
                end += 1
            if end > index + 1:
                block = [raw_lines[n] for n in range(index, end)]
                findings.append(
                    Finding(
                        path=path,
                        start=index + 1,
                        end=end,
                        kind="list item",
                        text=normalize_excerpt(block),
                    )
                )
                index = end
                continue
            index += 1
            continue

        end = index + 1
        while end < len(lines):
            candidate = lines[end]
            if candidate is None or is_structural(candidate) or LIST_RE.match(candidate):
                break
            end += 1
        if end > index + 1:
            block = [raw_lines[n] for n in range(index, end)]
            findings.append(
                Finding(
                    path=path,
                    start=index + 1,
                    end=end,
                    kind="paragraph",
                    text=normalize_excerpt(block),
                )
            )
        index = end

    return findings


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Flag manually hard-wrapped prose and list items in wiki Markdown."
    )
    parser.add_argument("paths", nargs="*", help="Markdown files or directories to scan.")
    parser.add_argument(
        "--git-diff",
        action="store_true",
        help="Report only blocks intersecting changed lines; scan untracked files in full.",
    )
    args = parser.parse_args()

    scan_paths = [Path(path).resolve() for path in args.paths] if args.paths else DEFAULT_PATHS
    markdown_files = iter_markdown_files(scan_paths)
    if not markdown_files:
        print("No markdown files found.")
        return

    if args.git_diff and any(ROOT not in path.parents for path in markdown_files):
        parser.error("--git-diff paths must be inside the repository")

    changed = git_changed_lines(markdown_files) if args.git_diff else {}
    findings: list[Finding] = []
    for path in markdown_files:
        if args.git_diff and path not in changed:
            continue
        for finding in scan_file(path):
            if args.git_diff:
                block_lines = set(range(finding.start, finding.end + 1))
                if not block_lines.intersection(changed[path]):
                    continue
            findings.append(finding)

    if not findings:
        print("No manually hard-wrapped Markdown blocks found.")
        return

    print("MANUALLY HARD-WRAPPED MARKDOWN")
    print("(Keep each prose paragraph and list item on one physical source line.)")
    print()
    for finding in findings:
        line_range = (
            str(finding.start)
            if finding.start == finding.end
            else f"{finding.start}-{finding.end}"
        )
        print(f"{display_path(finding.path)}:{line_range}  {finding.kind}")
        print(f"  {finding.text}")

    print()
    print(
        f"TOTAL: {len(findings)} hard-wrapped block(s) across "
        f"{len({finding.path for finding in findings})} file(s)."
    )


if __name__ == "__main__":
    main()
