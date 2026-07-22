#!/usr/bin/env python3
"""
Heuristic checker for the repo-wide medication first-mention format:
`generic (Brand, Taiwan name)`.

Usage:
  python3 scripts/check-medication-first-mentions.py PATH [PATH ...]

Each PATH may be a markdown file or a directory. Directories are searched
recursively for .md files. If no path is given, the script scans the main wiki
content locations.

The checker derives medication mappings from `wiki/concepts/*.md` files tagged
`medication`. It enforces only medications whose concept frontmatter provides
explicit `brand` and `taiwan-brand-name` fields alongside the concept `title`
(the generic name). It resets medication first-mention scope at `###` headings,
falling back to the enclosing `##` section when no deeper heading is present.
Output is intended as a suspect list for human or LLM review. Exit code is
always 0.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
DEFAULT_PATHS = [
    ROOT / "wiki" / "concepts",
    ROOT / "wiki" / "summaries",
    ROOT / "wiki" / "mocs",
    ROOT / "wiki" / "queries",
    ROOT / "wiki" / "slides",
    ROOT / "wiki" / "index.md",
    ROOT / "wiki" / "home.md",
]
CONCEPTS_DIR = ROOT / "wiki" / "concepts"

FRONTMATTER_BLOCK_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
SKIP_SECTIONS = {
    "Backlinks",
    "Connections",
    "Key Concepts",
    "Related",
    "Source Articles Consulted",
    "Sources",
}
MEDICATION_SCOPE_LEVEL = 3


def _blank_but_keep_lines(match: re.Match[str]) -> str:
    return "\n" * match.group(0).count("\n")


def strip_frontmatter(text: str) -> str:
    return FRONTMATTER_RE.sub(_blank_but_keep_lines, text, count=1)


def strip_code_fences(text: str) -> str:
    return CODE_FENCE_RE.sub(_blank_but_keep_lines, text)


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_BLOCK_RE.match(text)
    if not match:
        return {}

    data: dict[str, str] = {}
    for raw_line in match.group(1).splitlines():
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def parse_bracket_list(raw: str) -> list[str]:
    text = raw.strip()
    if not (text.startswith("[") and text.endswith("]")):
        return []
    inner = text[1:-1].strip()
    if not inner:
        return []
    return [item.strip().strip("'\"") for item in inner.split(",") if item.strip()]


def iter_markdown_files(paths: list[Path]) -> list[Path]:
    files: set[Path] = set()
    for path in paths:
        if path.is_file() and path.suffix == ".md":
            files.add(path.resolve())
        elif path.is_dir():
            for md_file in path.rglob("*.md"):
                files.add(md_file.resolve())
    return sorted(files)


def load_medication_entries() -> list[dict[str, str | re.Pattern[str]]]:
    entries: list[dict[str, str | re.Pattern[str]]] = []

    for concept_file in sorted(CONCEPTS_DIR.glob("*.md")):
        raw_text = concept_file.read_text(encoding="utf-8")
        frontmatter = parse_frontmatter(raw_text)
        title = frontmatter.get("title", "").strip()
        tags = parse_bracket_list(frontmatter.get("tags", ""))
        if not title or "medication" not in tags:
            continue

        brand = frontmatter.get("brand", "").strip().strip("'\"")
        taiwan_name = frontmatter.get("taiwan-brand-name", "").strip().strip("'\"")
        if not brand or not taiwan_name:
            continue
        brand = normalize_spaces(brand)
        taiwan_name = normalize_spaces(taiwan_name)

        generic_re = re.compile(
            rf"(?<![A-Za-z0-9]){re.escape(title)}(?![A-Za-z0-9])",
            re.IGNORECASE,
        )
        expected_re = re.compile(
            rf"(?<![A-Za-z0-9]){re.escape(title)}\s*\(\s*{re.escape(brand)}\s*,\s*{re.escape(taiwan_name)}\s*\)(?![A-Za-z0-9])",
            re.IGNORECASE,
        )
        entries.append(
            {
                "generic": title,
                "brand": brand,
                "taiwan_name": taiwan_name,
                "generic_re": generic_re,
                "expected_re": expected_re,
            }
        )

    return entries


def sectioned_blocks(text: str) -> list[dict[str, object]]:
    lines = text.splitlines()
    blocks: list[dict[str, object]] = []
    current: list[str] = []
    start_line = 1
    current_section = "(preamble)"
    medication_scope = 0

    def flush(kind: str = "paragraph") -> None:
        nonlocal current
        if current:
            blocks.append(
                {
                    "start": start_line,
                    "end": start_line + len(current) - 1,
                    "section": current_section,
                    "scope": medication_scope,
                    "kind": kind,
                    "text": "\n".join(current),
                }
            )
            current = []

    for index, line in enumerate(lines, start=1):
        heading_match = HEADING_RE.match(line)
        if heading_match:
            flush()
            if len(heading_match.group(1)) <= MEDICATION_SCOPE_LEVEL:
                medication_scope += 1
            current_section = heading_match.group(2).strip()
            continue

        if line.strip():
            stripped = line.lstrip()
            if stripped.startswith(("- ", "* ")):
                flush()
                blocks.append(
                    {
                        "start": index,
                        "end": index,
                        "section": current_section,
                        "scope": medication_scope,
                        "kind": "list",
                        "text": line,
                    }
                )
                continue
            if stripped.startswith("|"):
                flush()
                blocks.append(
                    {
                        "start": index,
                        "end": index,
                        "section": current_section,
                        "scope": medication_scope,
                        "kind": "table",
                        "text": line,
                    }
                )
                continue
            if not current:
                start_line = index
            current.append(line)
            continue

        flush()

    flush()
    return blocks


def clean_block(text: str) -> str:
    text = WIKILINK_RE.sub(r"\1", text)
    return normalize_spaces(text)


def scan_file(
    md_file: Path, text: str, entries: list[dict[str, str | re.Pattern[str]]]
) -> list[tuple[int, int, list[str], str]]:
    scan_blocks: list[dict[str, object]] = []
    for block in sectioned_blocks(text):
        if block["section"] in SKIP_SECTIONS:
            continue
        cleaned = clean_block(str(block["text"]))
        if not cleaned:
            continue
        block["clean"] = cleaned
        scan_blocks.append(block)

    grouped: dict[tuple[int, int], dict[str, object]] = {}

    def flag(block: dict[str, object], expected: str) -> None:
        key = (int(block["start"]), int(block["end"]))
        bucket = grouped.setdefault(key, {"expected": [], "clean": block["clean"]})
        bucket["expected"].append(expected)  # type: ignore[union-attr]

    for entry in entries:
        generic = str(entry["generic"])
        brand = str(entry["brand"])
        taiwan_name = str(entry["taiwan_name"])
        generic_re = entry["generic_re"]
        expected_re = entry["expected_re"]

        first_by_group: dict[tuple[int, str], dict[str, object]] = {}
        for block in scan_blocks:
            clean = str(block["clean"])
            if not generic_re.search(clean):  # type: ignore[union-attr]
                continue
            kind = str(block["kind"])
            group = (int(block["scope"]), kind)
            first_by_group.setdefault(group, block)

        expected_text = f"{generic} ({brand}, {taiwan_name})"
        for block in first_by_group.values():
            clean = str(block["clean"])
            if expected_re.search(clean):  # type: ignore[union-attr]
                continue
            flag(block, expected_text)

    findings: list[tuple[int, int, list[str], str]] = []
    for (start, end) in sorted(grouped):
        bucket = grouped[(start, end)]
        expected = sorted(set(bucket["expected"]))  # type: ignore[arg-type]
        findings.append((start, end, expected, str(bucket["clean"])))
    return findings


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
            total_lines = path.read_text(encoding="utf-8").count("\n") + 1
        except FileNotFoundError:
            continue
        changed[path] = set(range(1, total_lines + 1))

    return changed


def overlaps_changed_lines(start: int, end: int, changed_lines: set[int]) -> bool:
    return any(line in changed_lines for line in range(start, end + 1))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List suspect medication first-mention format gaps in markdown files."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Markdown files or directories to scan. Defaults to main wiki content.",
    )
    parser.add_argument(
        "--git-diff",
        action="store_true",
        help="Only report findings whose lines overlap the current git diff. Untracked files are scanned in full.",
    )
    args = parser.parse_args()

    scan_paths = [Path(p).resolve() for p in args.paths] if args.paths else DEFAULT_PATHS
    markdown_files = iter_markdown_files(scan_paths)
    entries = load_medication_entries()

    if not markdown_files:
        print("No markdown files found.")
        return

    if not entries:
        print("No medication entries with enforceable Brand/Taiwan-name mappings found.")
        return

    changed_lines_by_file = git_changed_lines(markdown_files) if args.git_diff else {}
    findings: list[tuple[Path, int, list[str], str]] = []

    for md_file in markdown_files:
        if args.git_diff and md_file not in changed_lines_by_file:
            continue
        raw_text = md_file.read_text(encoding="utf-8")
        body = strip_code_fences(strip_frontmatter(raw_text))
        file_findings = scan_file(md_file, body, entries)
        changed_lines = changed_lines_by_file.get(md_file)
        for line_no, end_line, expected, cleaned in file_findings:
            if changed_lines is not None and not overlaps_changed_lines(line_no, end_line, changed_lines):
                continue
            findings.append((md_file, line_no, expected, cleaned))

    if not findings:
        print("No suspect medication first-mention gaps found.")
        return

    print("SUSPECT MEDICATION FIRST-MENTION GAPS")
    print("(Heuristic output; review before editing.)")
    print()
    for md_file, line_no, expected, cleaned in findings:
        rel_path = md_file.relative_to(ROOT)
        snippet = cleaned[:180]
        if len(cleaned) > 180:
            snippet += "..."
        expected_text = "; ".join(expected)
        print(f"{rel_path}:{line_no}  expected: {expected_text}")
        print(f"  {snippet}")


if __name__ == "__main__":
    main()
