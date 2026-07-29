#!/usr/bin/env python3
"""
Heuristic checker for bilingual inline terms that are missing from the shared
Traditional Chinese medical glossary.

Usage:
  python3 scripts/check-glossary-delta.py PATH [PATH ...]

Each PATH may be a markdown file or a directory. Directories are searched
recursively for .md files. If no path is given, the script scans the main wiki
content locations.

The checker looks for inline English -> Chinese patterns such as
"paresthesia (感覺異常)" and reports the English term when it does not already
exist in memory/medical-term-translations.md. Output is a suspect list for
human or LLM review. Exit code is always 0.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
DEFAULT_GLOSSARY = ROOT / "memory" / "medical-term-translations.md"
DEFAULT_PATHS = [
    ROOT / "wiki" / "concepts",
    ROOT / "wiki" / "summaries",
    ROOT / "wiki" / "mocs",
    ROOT / "wiki" / "index.md",
    ROOT / "wiki" / "home.md",
]

FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
GLOSSARY_LINE_RE = re.compile(r"^- ([^:]+): (.+)$")
CJK_RE = re.compile(r"[\u3400-\u9fff]")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
NO_MATCH_RE = re.compile(r"\s*\(no-match\)\s*$", re.IGNORECASE)
PAREN_RE = re.compile(r"\(([^()\n]*[\u3400-\u9fff][^()\n]*)\)")
CLAUSE_SPLIT_RE = re.compile(r"[.!?;:]")
LEADING_ARTICLE_RE = re.compile(r"^(?:a|an|the)\s+", re.IGNORECASE)
LEADING_FILLER_RE = re.compile(
    r"^(?:and|or|all|other|likely|collectively|serial)\s+", re.IGNORECASE
)
TRAILING_VALUE_RE = re.compile(
    r"\s+\d+(?:\.\d+)?(?:\s*(?:[A-Za-z/%]+|->)\s*\d*(?:\.\d+)?)?(?:\s*[HL])?$"
)

SKIP_SECTIONS = {
    "Key Concepts",
    "Backlinks",
    "Sources",
    "Source Articles Consulted",
}

BOUNDARY_MARKERS = [
    " with ",
    " without ",
    " including ",
    " included ",
    " include ",
    " shows ",
    " showed ",
    " showing ",
    " demonstrates ",
    " demonstrated ",
    " reveals ",
    " revealed ",
    " indicates ",
    " indicated ",
    " notes ",
    " noted ",
    " lists ",
    " listed ",
    " ruling out ",
    " ruled out ",
    " excluding ",
    " excluded ",
    " was ",
    " were ",
    " is ",
    " are ",
    " had ",
    " has ",
    " have ",
]


def _blank_but_keep_lines(match: re.Match[str]) -> str:
    return "\n" * match.group(0).count("\n")


def strip_frontmatter(text: str) -> str:
    return FRONTMATTER_RE.sub(_blank_but_keep_lines, text, count=1)


def strip_code_fences(text: str) -> str:
    return CODE_FENCE_RE.sub(_blank_but_keep_lines, text)


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_variants(text: str) -> list[str]:
    parts = [p.strip() for p in text.split(" / ") if p.strip()]
    if not parts:
        return [text.strip()]
    if text.strip() not in parts:
        parts.append(text.strip())
    return parts


def is_pure_abbreviation(term: str) -> bool:
    compact = term.replace("-", "").replace(".", "").replace("/", "").strip()
    return compact.isupper() and 1 < len(compact) <= 8


def normalize_term(term: str) -> str:
    cleaned = normalize_spaces(
        term.replace("–", "-").replace("—", "-").replace("／", "/").strip(" ,;:.()[]")
    )
    if is_pure_abbreviation(cleaned):
        return cleaned
    return cleaned.lower()


def singularize_last_word(term: str) -> str:
    parts = term.split()
    if not parts:
        return term
    last = parts[-1]
    lower = last.lower()
    if lower.endswith("ies") and len(last) > 4:
        parts[-1] = last[:-3] + "y"
    elif lower.endswith("s") and len(last) > 3 and not lower.endswith("ss"):
        parts[-1] = last[:-1]
    return " ".join(parts)


def load_glossary_terms(path: Path) -> set[str]:
    known: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        match = GLOSSARY_LINE_RE.match(raw_line)
        if not match:
            continue
        for variant in split_variants(match.group(1).strip()):
            if NO_MATCH_RE.search(variant):
                continue
            normalized = normalize_term(NO_MATCH_RE.sub("", variant).strip())
            if normalized:
                known.add(normalized)
                singular = singularize_last_word(normalized)
                if singular:
                    known.add(singular)
    return known


def iter_markdown_files(paths: list[Path]) -> list[Path]:
    files: set[Path] = set()
    for path in paths:
        if path.is_file() and path.suffix == ".md":
            files.add(path.resolve())
        elif path.is_dir():
            for md_file in path.rglob("*.md"):
                files.add(md_file.resolve())
    return sorted(files)


def sectioned_blocks(text: str) -> list[dict[str, object]]:
    lines = text.splitlines()
    blocks: list[dict[str, object]] = []
    current: list[str] = []
    start_line = 1
    current_section = "(preamble)"

    def flush() -> None:
        nonlocal current
        if current:
            blocks.append(
                {
                    "start": start_line,
                    "end": start_line + len(current) - 1,
                    "section": current_section,
                    "text": "\n".join(current),
                }
            )
            current = []

    for index, line in enumerate(lines, start=1):
        heading_match = HEADING_RE.match(line)
        if heading_match:
            flush()
            current_section = heading_match.group(2).strip()
            continue

        if line.strip():
            if line.lstrip().startswith(("- ", "* ")):
                flush()
                blocks.append(
                    {
                        "start": index,
                        "end": index,
                        "section": current_section,
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


def clean_paragraph(text: str) -> str:
    text = WIKILINK_RE.sub(r"\1", text)
    return normalize_spaces(text)


def extract_candidate(fragment: str) -> str | None:
    candidate = CLAUSE_SPLIT_RE.split(fragment)[-1]
    candidate = candidate.rsplit(", ", 1)[-1]

    lowered = candidate.lower()
    for marker in BOUNDARY_MARKERS:
        if marker in lowered:
            start = lowered.rfind(marker) + len(marker)
            candidate = candidate[start:]
            lowered = candidate.lower()

    candidate = candidate.strip(" ,-–—")
    candidate = LEADING_ARTICLE_RE.sub("", candidate)
    candidate = LEADING_FILLER_RE.sub("", candidate)
    candidate = TRAILING_VALUE_RE.sub("", candidate).strip(" ,-–—")
    if not candidate or not re.search(r"[A-Za-z]", candidate):
        return None

    words = candidate.split()
    if len(words) > 6:
        candidate = " ".join(words[-6:])

    candidate = normalize_spaces(candidate)
    if len(candidate) < 2:
        return None
    return candidate


def split_parenthetical_text(text: str) -> tuple[str | None, str]:
    parts = [normalize_spaces(part) for part in text.split(",") if normalize_spaces(part)]
    english_parts = [part for part in parts if re.search(r"[A-Za-z]", part) and not CJK_RE.search(part)]
    chinese_parts = [part for part in parts if CJK_RE.search(part)]
    english = english_parts[0] if english_parts else None
    chinese = chinese_parts[-1] if chinese_parts else normalize_spaces(text)
    return english, chinese


def is_known_candidate(candidate: str, known_terms: set[str]) -> bool:
    normalized = normalize_term(candidate)
    if not normalized:
        return True
    if normalized in known_terms or singularize_last_word(normalized) in known_terms:
        return True
    if "/" in candidate:
        parts = [normalize_term(part) for part in re.split(r"\s*/\s*", candidate) if part.strip()]
        if parts and all(part in known_terms or singularize_last_word(part) in known_terms for part in parts):
            return True
    return False


def scan_text_for_candidates(text: str, known_terms: set[str]) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for match in PAREN_RE.finditer(text):
        inline_english, zh = split_parenthetical_text(match.group(1))
        candidate = inline_english
        if candidate is None:
            window = text[max(0, match.start() - 120) : match.start()]
            candidate = extract_candidate(window)
        if candidate is None or is_known_candidate(candidate, known_terms):
            continue
        key = (normalize_term(candidate), zh)
        if key in seen:
            continue
        seen.add(key)
        findings.append((candidate, zh))

    return findings


def scan_file(
    md_file: Path, text: str, known_terms: set[str]
) -> list[tuple[int, int, list[tuple[str, str]], str]]:
    findings: list[tuple[int, int, list[tuple[str, str]], str]] = []

    for block in sectioned_blocks(text):
        if block["section"] in SKIP_SECTIONS:
            continue
        cleaned = clean_paragraph(str(block["text"]))
        if not cleaned:
            continue
        candidates = scan_text_for_candidates(cleaned, known_terms)
        if not candidates:
            continue
        findings.append((int(block["start"]), int(block["end"]), candidates, cleaned))

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
        description="List inline bilingual terms that are missing from the shared glossary."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Markdown files or directories to scan. Defaults to main wiki content.",
    )
    parser.add_argument(
        "--glossary",
        default=str(DEFAULT_GLOSSARY),
        help="Path to the shared medical glossary file.",
    )
    parser.add_argument(
        "--git-diff",
        action="store_true",
        help="Only report findings whose lines overlap the current git diff. Untracked files are scanned in full.",
    )
    args = parser.parse_args()

    glossary_path = Path(args.glossary)
    scan_paths = [Path(p).resolve() for p in args.paths] if args.paths else DEFAULT_PATHS
    markdown_files = iter_markdown_files(scan_paths)
    known_terms = load_glossary_terms(glossary_path)

    if not markdown_files:
        print("No markdown files found.")
        return

    changed_lines_by_file = git_changed_lines(markdown_files) if args.git_diff else {}
    findings: list[tuple[Path, int, list[tuple[str, str]], str]] = []

    for md_file in markdown_files:
        if args.git_diff and md_file not in changed_lines_by_file:
            continue
        raw_text = md_file.read_text(encoding="utf-8")
        body = strip_code_fences(strip_frontmatter(raw_text))
        file_findings = scan_file(md_file, body, known_terms)
        changed_lines = changed_lines_by_file.get(md_file)
        for line_no, end_line, candidates, cleaned in file_findings:
            if changed_lines is not None and not overlaps_changed_lines(line_no, end_line, changed_lines):
                continue
            findings.append((md_file, line_no, candidates, cleaned))

    if not findings:
        print("No glossary-delta candidates found.")
        return

    print("SUSPECT GLOSSARY-DELTA CANDIDATES")
    print("(Heuristic output; add only reusable standalone terms to the glossary.)")
    print()
    for md_file, line_no, candidates, cleaned in findings:
        rel_path = md_file.relative_to(ROOT)
        snippet = cleaned[:180]
        if len(cleaned) > 180:
            snippet += "..."
        pair_text = "; ".join(f"{english} => {zh}" for english, zh in candidates)
        print(f"{rel_path}:{line_no}  {pair_text}")
        print(f"  {snippet}")

    # Trailing total — see the note in check-bilingual-terms.py. Keep it last.
    print()
    print(
        f"TOTAL: {len(findings)} flagged line(s) across "
        f"{len({f for f, _, _, _ in findings})} file(s)."
    )


if __name__ == "__main__":
    main()
