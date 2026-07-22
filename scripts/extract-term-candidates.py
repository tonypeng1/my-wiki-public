#!/usr/bin/env python3
"""Term-candidate worklist generator for the translation two-pass (Pass A).

Emits a per-file worklist of candidate clinical terms so a reviewer (or LLM) can
disposition each during Pass A of the translation-backfill / ingest find step.

It detects what a *pattern* can catch — acronyms (REM, SRT, CBT-I) and
"Capitalized phrase (ACRONYM)" definitions — and, crucially, surfaces candidates
that are NOT in the glossary. That is the class check-bilingual-terms.py is
structurally blind to: the dictionary checker can only re-check terms it already
knows, so a first-ever "SRT" or "CBT-I" is invisible to it but visible here.

This is a discovery aid, not a gate. Expect proper nouns and non-clinical
acronyms in the output — disposition each row, don't trust it. It does NOT catch
lowercase multi-word terms ("sleep pressure", "arousal threshold"); those are the
judgment residue Pass A adds by reading. Exit code is always 0.

Usage:
  python3 scripts/extract-term-candidates.py PATH [PATH ...]
  python3 scripts/extract-term-candidates.py --all PATH   # include handled terms

Glossary membership reuses check-bilingual-terms.py's loader, so it inherits the
same acronym-matching (including bare acronyms derived from "REM sleep" etc.).
"""

from __future__ import annotations

import argparse
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
CHECKER = ROOT / "scripts" / "check-bilingual-terms.py"
DEFAULT_GLOSSARY = ROOT / "memory" / "medical-term-translations.md"

CJK = r"[㐀-鿿]"
# All-caps/digit runs bounded by non-letters, so an uppercase stretch inside a
# mixed-case word is skipped ("PAT" in "WatchPAT", "RGC" in "ipRGCs") and a run
# is never truncated at a following capital ("TC" out of "TCAs").
ACRONYM_RE = re.compile(r"(?<![A-Za-z])[A-Z0-9]+(?:-[A-Z0-9]+)*(?![A-Za-z])")
# "Sleep restriction therapy (SRT)" — capitalized phrase then a bracketed acronym.
DEFINITION_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9'’-]+(?:\s+[A-Za-z0-9'’-]+){0,5})\s*\(([A-Z0-9][A-Z0-9-]{1,7})\)"
)

# Common non-clinical acronyms that are never medical vocabulary in this wiki.
# Ambiguous-but-clinical ones (US = ultrasound, ER = extended-release) are left
# out on purpose — they resolve to glossary entries and sort into "handled".
STOPLIST = {
    "AM", "PM", "TV", "OK", "OS", "APP", "RX", "ID", "URL", "PDF", "FAQ", "CEO",
    "FDA", "NHI", "AASM", "LCD", "OLED", "LED", "USB", "HTTP", "HTTPS", "DOB",
    "MRN", "ICD",
}


def load_checker_module():
    spec = importlib.util.spec_from_file_location("check_bilingual_terms", CHECKER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def is_candidate_acronym(token: str) -> bool:
    if token in STOPLIST:
        return False
    if not ACRONYM_RE.fullmatch(token):
        return False
    letters = [ch for ch in token if ch.isalpha()]
    return 2 <= len(letters) <= 6


def in_glossary(term: str, entries: list) -> bool:
    for entry in entries:
        for regex in entry["english_regexes"]:
            if regex.search(term):
                return True
    return False


def has_inline_translation(text: str, term: str) -> bool:
    # Chinese *immediately* after the term, separated only by punctuation/space/
    # digits (no intervening English word), so nearby Chinese belonging to a
    # neighbouring term does not count. Matches "REM (快速動眼睡眠)" and
    # "(SWS, 慢波睡眠)"; not "CSD)** ... monitoring (監測)".
    pattern = re.compile(re.escape(term) + r"[^A-Za-z㐀-鿿.。\n]*" + CJK)
    return bool(pattern.search(text))


def collect_candidates(body: str) -> dict[str, tuple[int, str]]:
    """First occurrence (line, snippet) for each candidate acronym token."""
    first: dict[str, tuple[int, str]] = {}
    # Definition patterns first — they carry the fullest context for the acronym.
    for line_no, line in enumerate(body.splitlines(), start=1):
        for phrase, acronym in DEFINITION_RE.findall(line):
            if is_candidate_acronym(acronym) and acronym not in first:
                first[acronym] = (line_no, f"{phrase.strip()} ({acronym})")
    for line_no, line in enumerate(body.splitlines(), start=1):
        for token in ACRONYM_RE.findall(line):
            if is_candidate_acronym(token) and token not in first:
                snippet = line.strip()
                if len(snippet) > 90:
                    idx = snippet.find(token)
                    start = max(0, idx - 35)
                    snippet = ("…" if start else "") + snippet[start:start + 90] + "…"
                first[token] = (line_no, snippet)
    return first


def classify(term: str, full_text: str, entries: list) -> str:
    known = in_glossary(term, entries)
    translated = has_inline_translation(full_text, term)
    if not known and not translated:
        return "new"
    if not known and translated:
        return "add-to-glossary"
    if known and not translated:
        return "verify-coverage"
    return "handled"


CATEGORY_TITLES = {
    "new": "NOT IN GLOSSARY, no inline translation — translate + add glossary, or mark intentional-English",
    "add-to-glossary": "TRANSLATED INLINE but not in glossary — add the reusable ones to the glossary",
    "verify-coverage": "IN GLOSSARY, no adjacent Chinese here — verify first-mention coverage (checker's job)",
}


def iter_markdown_files(paths: list[Path]) -> list[Path]:
    files: set[Path] = set()
    for path in paths:
        if path.is_file() and path.suffix == ".md":
            files.add(path.resolve())
        elif path.is_dir():
            for md_file in path.rglob("*.md"):
                files.add(md_file.resolve())
    return sorted(files)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List candidate clinical terms (acronyms/definitions) as a Pass A worklist."
    )
    parser.add_argument("paths", nargs="+", help="Markdown files or directories.")
    parser.add_argument("--glossary", default=str(DEFAULT_GLOSSARY))
    parser.add_argument(
        "--all", action="store_true", help="Also list already-handled terms."
    )
    args = parser.parse_args()

    checker = load_checker_module()
    entries = checker.load_glossary(Path(args.glossary))

    for md_file in iter_markdown_files([Path(p) for p in args.paths]):
        raw = md_file.read_text(encoding="utf-8")
        body = checker.strip_code_fences(checker.strip_frontmatter(raw))
        candidates = collect_candidates(body)

        buckets: dict[str, list[tuple[str, int, str]]] = {
            "new": [], "add-to-glossary": [], "verify-coverage": [], "handled": [],
        }
        for term, (line_no, snippet) in candidates.items():
            buckets[classify(term, body, entries)].append((term, line_no, snippet))

        try:
            display = md_file.relative_to(ROOT)
        except ValueError:
            display = md_file
        print(f"\n=== {display} ===")
        actionable = sum(len(buckets[c]) for c in CATEGORY_TITLES)
        if not actionable and not args.all:
            print("  No unhandled term candidates. (Use --all to list handled terms.)")
        for category, title in CATEGORY_TITLES.items():
            rows = sorted(buckets[category], key=lambda r: r[1])
            if not rows:
                continue
            print(f"\n  {title}:")
            for term, line_no, snippet in rows:
                print(f"    L{line_no:<4} {term:<8} {snippet}")

        if args.all and buckets["handled"]:
            handled = ", ".join(sorted(t for t, _, _ in buckets["handled"]))
            print(f"\n  HANDLED (in glossary + translated inline): {handled}")


if __name__ == "__main__":
    main()
