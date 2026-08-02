#!/usr/bin/env python3
"""Validate the structural contract for MOC Key Relationships sections.

Each MOC must contain exactly one ``## Key Relationships`` section whose body
is one prose paragraph of two or three sentences. The checker also flags a
small, conservative set of open-question and document-acquisition phrases that
belong in concept articles rather than a MOC relationship summary.

Usage:
  python3 scripts/check-moc-key-relationships.py [PATH ...] [--git-diff]

With no PATH, scan wiki/mocs/. ``--git-diff`` checks new MOCs in full and checks
an existing MOC only when its Key Relationships section intersects a changed
line. A touched MOC whose section is missing is always reported. Read-only;
exit code is always 0.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).parent.parent
MOCS = ROOT / "wiki" / "mocs"

KEY_HEADING = "## Key Relationships"
SECTION_HEADING_RE = re.compile(r"^##\s+")
LIST_RE = re.compile(r"^\s*(?:[-+*]|\d+[.)])\s+")
TABLE_RE = re.compile(r"^\s*\|")

ADVISORY_PATTERNS = [
    (re.compile(r"\?"), "question language"),
    (re.compile(r"\bopen questions?\b", re.IGNORECASE), "open-question label"),
    (re.compile(r"\bfirst thing to fix\b", re.IGNORECASE), "action advice"),
    (
        re.compile(
            r"\buntil\b[^.!?]{0,160}\b(?:arrives?|is (?:added|available|obtained|provided))\b",
            re.IGNORECASE,
        ),
        "missing-document advice",
    ),
    (
        re.compile(
            r"\b(?:should|must|needs? to)\s+(?:be\s+)?"
            r"(?:obtained|added|measured|ordered|requested|tracked|followed|"
            r"repeated|clarified|confirmed|fixed)\b",
            re.IGNORECASE,
        ),
        "recommendation or action item",
    ),
    (
        re.compile(
            r"\b(?:obtain|acquire|request|add)\s+(?:the\s+|an?\s+)?"
            r"(?:missing|additional|paired|follow-up|source|report|document|"
            r"imaging|test|measurement)\b",
            re.IGNORECASE,
        ),
        "document-acquisition advice",
    ),
]

COMMON_ABBREVIATIONS = (
    "e.g.",
    "i.e.",
    "Dr.",
    "Mr.",
    "Mrs.",
    "Ms.",
    "Prof.",
    "vs.",
    "etc.",
)


@dataclass(frozen=True)
class Section:
    heading_line: int
    end_line: int
    content_lines: list[str]


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    kind: str
    message: str


def iter_moc_files(paths: list[Path]) -> list[Path]:
    files: set[Path] = set()
    for path in paths:
        if path.is_file() and path.suffix == ".md" and path.name.startswith("moc-"):
            files.add(path.resolve())
        elif path.is_dir():
            files.update(
                md_file.resolve()
                for md_file in path.rglob("moc-*.md")
                if md_file.is_file()
            )
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


def git_changed_lines(paths: list[Path]) -> tuple[dict[Path, set[int]], set[Path]]:
    relative_paths = [str(path.relative_to(ROOT)) for path in paths]
    diff = subprocess.run(
        ["git", "diff", "--unified=0", "--", *relative_paths],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    changed = parse_unified_zero_diff(diff.stdout)
    untracked: set[Path] = set()

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
        untracked.add(path)
        try:
            total = len(path.read_text(encoding="utf-8").splitlines())
        except FileNotFoundError:
            continue
        changed[path] = set(range(1, total + 1))
    return changed, untracked


def extract_sections(lines: list[str]) -> list[Section]:
    sections: list[Section] = []
    for index, line in enumerate(lines):
        if line.strip() != KEY_HEADING:
            continue
        end = index + 1
        while end < len(lines) and not SECTION_HEADING_RE.match(lines[end]):
            end += 1
        sections.append(
            Section(
                heading_line=index + 1,
                end_line=end,
                content_lines=lines[index + 1 : end],
            )
        )
    return sections


def paragraph_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.strip():
            current.append(line)
            continue
        if current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def mask_nonterminal_periods(text: str) -> str:
    masked = re.sub(r"(?<=\d)\.(?=\d)", "∯", text)
    masked = re.sub(r"\b([A-Z])\.(?=\s*[A-Z])", r"\1∯", masked)
    for abbreviation in COMMON_ABBREVIATIONS:
        pattern = re.compile(re.escape(abbreviation), re.IGNORECASE)
        masked = pattern.sub(abbreviation.replace(".", "∯"), masked)
    return masked


def sentence_count(text: str) -> int:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return 0
    masked = mask_nonterminal_periods(normalized)
    sentences = re.split(
        r"(?<=[.!?])\s+(?=(?:\[\[[^\]\n]+\]\]|[(*_~]*[A-Z0-9]))",
        masked,
    )
    return len([sentence for sentence in sentences if sentence.strip()])


def inspect_file(path: Path, sections: list[Section]) -> list[Finding]:
    if len(sections) != 1:
        return [
            Finding(
                path=path,
                line=1,
                kind="section count",
                message=f"expected exactly one {KEY_HEADING!r} section; found {len(sections)}",
            )
        ]

    section = sections[0]
    blocks = paragraph_blocks(section.content_lines)
    findings: list[Finding] = []
    if len(blocks) != 1:
        findings.append(
            Finding(
                path=path,
                line=section.heading_line,
                kind="paragraph count",
                message=f"expected one paragraph; found {len(blocks)}",
            )
        )

    nonempty_lines = [line for line in section.content_lines if line.strip()]
    if any(LIST_RE.match(line) or TABLE_RE.match(line) or line.lstrip().startswith("#") for line in nonempty_lines):
        findings.append(
            Finding(
                path=path,
                line=section.heading_line,
                kind="non-prose content",
                message="Key Relationships must be a prose paragraph, not a list, table, or nested section",
            )
        )

    prose = re.sub(r"\s+", " ", " ".join(nonempty_lines)).strip()
    count = sentence_count(prose)
    if count not in {2, 3}:
        findings.append(
            Finding(
                path=path,
                line=section.heading_line,
                kind="sentence count",
                message=f"expected 2-3 sentences; found {count}",
            )
        )

    for pattern, label in ADVISORY_PATTERNS:
        match = pattern.search(prose)
        if not match:
            continue
        excerpt = prose[max(0, match.start() - 45) : match.end() + 70]
        findings.append(
            Finding(
                path=path,
                line=section.heading_line,
                kind=label,
                message=f"move this out of Key Relationships: {excerpt!r}",
            )
        )

    return findings


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate MOC Key Relationships structure and scope."
    )
    parser.add_argument("paths", nargs="*", help="MOC files or directories to scan.")
    parser.add_argument(
        "--git-diff",
        action="store_true",
        help="Check new MOCs and changed Key Relationships sections only.",
    )
    args = parser.parse_args()

    scan_paths = [Path(path).resolve() for path in args.paths] if args.paths else [MOCS]
    moc_files = iter_moc_files(scan_paths)
    if not moc_files:
        print("No MOC files found.")
        return

    if args.git_diff and any(ROOT not in path.parents for path in moc_files):
        parser.error("--git-diff paths must be inside the repository")

    changed: dict[Path, set[int]] = {}
    untracked: set[Path] = set()
    if args.git_diff:
        changed, untracked = git_changed_lines(moc_files)

    findings: list[Finding] = []
    scanned = 0
    for path in moc_files:
        lines = path.read_text(encoding="utf-8").splitlines()
        sections = extract_sections(lines)
        if args.git_diff:
            if path not in changed:
                continue
            if sections and path not in untracked:
                relationship_lines = set(
                    range(sections[0].heading_line, sections[0].end_line + 1)
                )
                if not relationship_lines.intersection(changed[path]):
                    continue
        scanned += 1
        findings.extend(inspect_file(path, sections))

    if not findings:
        print(f"MOC Key Relationships check clean ({scanned} section(s) checked).")
        return

    print("MOC KEY RELATIONSHIPS FINDINGS")
    print()
    for finding in findings:
        print(f"{display_path(finding.path)}:{finding.line}  [{finding.kind}]")
        print(f"  {finding.message}")

    print()
    print(
        f"TOTAL: {len(findings)} finding(s) across "
        f"{len({finding.path for finding in findings})} file(s)."
    )


if __name__ == "__main__":
    main()
