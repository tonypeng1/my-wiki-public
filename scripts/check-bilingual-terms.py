#!/usr/bin/env python3
"""
Heuristic checker for English medical terms that appear without their
Traditional Chinese glossary translations in the same paragraph.

Usage:
  python3 scripts/check-bilingual-terms.py PATH [PATH ...]

Each PATH may be a markdown file or a directory. Directories are searched
recursively for .md files. If no path is given, the script scans the main
wiki content locations.

Output is intended as a suspect list for human or LLM review. The checker only
knows terms already present in memory/medical-term-translations.md. Exit code is
always 0.

Enforcement model (mirrors the Traditional Chinese Medical Terms policy in
CLAUDE.md):
  - A term and its abbreviations are one term (all variants on a glossary line).
  - The term's FIRST meaningful mention in an article must carry a Chinese
    translation. A missing first-mention translation is flagged.
  - When the term REAPPEARS in a later major section (a later top-level "##"
    heading), a second translation is expected in one of those later-section
    mentions. If none of them is translated, the earliest later-section mention
    is flagged. Nothing beyond the second translation is required or flagged.
  - Within a single counting unit, a term that occurs TWO or more times must
    carry at least two translations (first AND second occurrence; the maximum is
    two). A unit with >=2 occurrences but fewer than two translations is flagged
    with a "(2nd)" suffix on the earliest untranslated later occurrence. The
    counting unit is the innermost heading section for concept/summary/MOC/slide
    files; for wiki/index.md it is the paragraph (in the Compilation Summary) or
    the individual "## {file}.md" entry block. Query files are exempt from this
    within-unit rule — they keep the more aggressive per-subsection exception
    below.
  - Abbreviations are matched case-sensitively. A glossary variant marked
    "(no-match)" is documented but never machine-matched (used to silence
    ambiguous abbreviations such as PA / CT / MI).
  - Query-file exception: selected recurring clinical terms (common
    abbreviations plus a curated set of skim-critical terms) must also be
    translated on the first mention in each `###` subsection, with fallback to
    the enclosing `##` section when no `###` heading is present.
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

SKIP_SECTIONS = {
    "Key Concepts",
    "Backlinks",
    "Sources",
    "Source Articles Consulted",
}
QUERY_SUBSECTION_EXTRA_LABELS = {
    "Estimated glomerular filtration rate",
    "Fasting glucose",
    "Gluconeogenesis",
    "Non-alcoholic fatty liver disease",
    "Obstructive sleep apnea",
    "Post-prandial",
    "Prediabetes",
}


def _blank_but_keep_lines(match: re.Match[str]) -> str:
    # Replace a matched region with as many blank lines as it spanned so that
    # every following line keeps its original 1-based number in the file.
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
    return compact.isupper() and 1 < len(compact) <= 6


def derive_acronym_tokens(variant: str) -> list[str]:
    """Bare acronym tokens embedded in a multi-word glossary variant.

    Lets a glossary form like "REM sleep" or "NREM sleep" also match the bare
    acronym ("REM", "NREM") that prose actually uses. Restricted to all-caps
    alphabetic tokens of 3-6 characters, so short or ambiguous acronyms (AV, MI)
    and stage codes (N3) are not auto-matched against ordinary prose.
    """
    tokens = variant.split()
    if len(tokens) < 2:
        return []
    derived: list[str] = []
    for token in tokens:
        compact = token.replace("-", "").replace(".", "")
        if compact.isupper() and compact.isalpha() and 3 <= len(compact) <= 6:
            derived.append(token)
    return derived


def leading_acronym_token(variant: str) -> str | None:
    """The acronym a multi-word variant *leads* with, if any.

    "REM sleep" -> "REM"; "OMFS surgeon" -> "OMFS". Returns None when the first
    token is not a 3-6 letter all-caps acronym, so a compound where the acronym
    is not leading ("nucleated RBC") does not yield a bare-acronym match.
    """
    tokens = variant.split()
    if len(tokens) < 2:
        return None
    lead = tokens[0]
    compact = lead.replace("-", "").replace(".", "")
    if compact.isupper() and compact.isalpha() and 3 <= len(compact) <= 6:
        return lead
    return None


def build_term_regex(term: str, case_sensitive: bool = False) -> re.Pattern[str]:
    escaped = re.escape(term)
    if re.search(r"[A-Za-z0-9]", term[0]) and re.search(r"[A-Za-z0-9]", term[-1]):
        pattern = rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])"
    else:
        pattern = escaped
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(pattern, flags)


def load_glossary(path: Path) -> list[dict[str, object]]:
    # First pass: parse each line's explicit variants, and collect every
    # acronym that is listed standalone anywhere (e.g. "ECG", "CAC") so the
    # derivation pass never re-derives one that already has its own entry.
    parsed: list[dict[str, object]] = []
    standalone_acronyms: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        match = GLOSSARY_LINE_RE.match(raw_line)
        if not match:
            continue

        english_raw = match.group(1).strip()
        chinese_raw = match.group(2).strip()

        raw_variants = split_variants(english_raw)
        label = NO_MATCH_RE.sub("", raw_variants[0]).strip()

        english_variants = []
        english_regexes = []
        for variant in raw_variants:
            if NO_MATCH_RE.search(variant):
                # Documented for the reader, but never machine-matched
                # (used to silence ambiguous abbreviations like PA / CT / MI).
                continue
            abbrev = is_pure_abbreviation(variant)
            # Skip very short non-abbreviation words (e.g. single-letter analyte
            # symbols) that would collide with ordinary prose. Abbreviations are
            # kept and matched case-sensitively as a false-positive guard.
            if not abbrev and len(variant) < 4 and " " not in variant:
                continue
            english_variants.append(variant)
            english_regexes.append(build_term_regex(variant, case_sensitive=abbrev))
            if abbrev:
                standalone_acronyms.add(variant)

        if not english_regexes:
            continue

        parsed.append(
            {
                "label": label,
                "raw_variants": raw_variants,
                "chinese_raw": chinese_raw,
                "english_variants": english_variants,
                "english_regexes": english_regexes,
            }
        )

    # Second pass: also match bare acronyms embedded in multi-word variants
    # (e.g. "REM sleep" -> "REM") that prose uses without the trailing word.
    # Guarded four ways so compound qualifiers (ECG in "Resting 12-lead ECG",
    # LDL in "LDL particle", RBC in "nucleated RBC") are NOT derived:
    #   1. the acronym must be the LEADING token of an abbreviated variant
    #      ("REM sleep"), not a mid-phrase qualifier ("nucleated RBC");
    #   2. the entry must pair it with a spelled-out expansion
    #      (e.g. "Rapid eye movement sleep"), which qualifier compounds lack;
    #   3. the acronym must not already be a standalone entry elsewhere; and
    #   4. the acronym must not appear in this entry's own Chinese (e.g.
    #      "REM latency" -> "REM 潛伏期", where the entry keeps it untranslated).
    entries: list[dict[str, object]] = []
    for item in parsed:
        raw_variants = item["raw_variants"]  # type: ignore[assignment]
        chinese_raw = str(item["chinese_raw"])
        english_variants = item["english_variants"]  # type: ignore[assignment]
        english_regexes = item["english_regexes"]  # type: ignore[assignment]

        has_expansion = any(
            " " in variant
            and not NO_MATCH_RE.search(variant)
            and not derive_acronym_tokens(variant)
            for variant in raw_variants
        )
        if has_expansion:
            for variant in raw_variants:
                if NO_MATCH_RE.search(variant):
                    continue
                token = leading_acronym_token(variant)
                if token is None:
                    continue
                if token in english_variants or token in chinese_raw:
                    continue
                if token in standalone_acronyms:
                    continue
                english_variants.append(token)
                english_regexes.append(build_term_regex(token, case_sensitive=True))

        entries.append(
            {
                "label": item["label"],
                "english_variants": english_variants,
                "english_regexes": english_regexes,
                "chinese_variants": split_variants(chinese_raw),
                "has_abbreviation": any(is_pure_abbreviation(v) for v in english_variants),
            }
        )

    return entries


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
    """Split markdown into paragraph / list-item blocks.

    Each block records its 1-based start and end line, its section heading, a
    ``major`` ordinal that increments at every top-level ("#" or "##") heading,
    and a ``subsection`` ordinal that increments at every heading up to "###".
    """
    lines = text.splitlines()
    blocks: list[dict[str, object]] = []
    current: list[str] = []
    start_line = 1
    current_section = "(preamble)"
    major_section = 0
    subsection = 0

    def flush() -> None:
        nonlocal current
        if current:
            blocks.append(
                {
                    "start": start_line,
                    "end": start_line + len(current) - 1,
                    "section": current_section,
                    "major": major_section,
                    "subsection": subsection,
                    "text": "\n".join(current),
                }
            )
            current = []

    for index, line in enumerate(lines, start=1):
        heading_match = HEADING_RE.match(line)
        if heading_match:
            flush()
            heading_level = len(heading_match.group(1))
            if heading_level <= 2:
                major_section += 1
            if heading_level <= 3:
                subsection += 1
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
                        "major": major_section,
                        "subsection": subsection,
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


def clean_for_occurrences(text: str) -> str:
    # Drop [[backlinks]] entirely (not unwrap): backlinks are English and do not
    # count as term occurrences per the translation policy, so their inner text
    # must not inflate occurrence counts or trigger first-mention flags.
    text = WIKILINK_RE.sub(" ", text)
    return normalize_spaces(text)


# How far past an English mention to look for its inline "(中文)" translation.
# Bounded (and further clamped to the next English occurrence) so a later term's
# translation is never mis-attributed to an earlier, untranslated mention.
TRANSLATION_WINDOW = 80


def resolve_occurrences(
    clean_text: str, entries: list[dict[str, object]]
) -> list[tuple[int, int, bool]]:
    """Ordered term occurrences in one unit, with longest-match-wins resolution.

    Returns ``(start_offset, entry_index, translated?)`` for every surviving
    mention. A mention is "translated" when it is immediately followed by a
    parenthetical containing one of that entry's glossary Chinese variants — the
    ``English (中文)`` inline form the policy requires.

    Longest-match-wins across ALL entries prevents a shorter term's mention from
    being counted when it sits inside a longer, separately-translated term
    (e.g. bare "sleep apnea" inside "obstructive sleep apnea"; "LDL" inside
    "LDL cholesterol").
    """
    spans: list[tuple[int, int, int]] = []
    for idx, entry in enumerate(entries):
        for regex in entry["english_regexes"]:  # type: ignore[union-attr]
            for match in regex.finditer(clean_text):
                spans.append((match.start(), match.end(), idx))
    if not spans:
        return []

    # Sort by start, then longest first, so a containing span is seen before the
    # shorter spans nested inside it.
    spans.sort(key=lambda s: (s[0], -(s[1] - s[0])))
    kept: list[tuple[int, int, int]] = []
    for start, end, idx in spans:
        dominated = any(
            (start >= ks and end <= ke and (ke - ks) > (end - start))
            or (start == ks and end == ke)
            for ks, ke, _ in kept
        )
        if dominated:
            continue
        kept.append((start, end, idx))

    kept.sort()
    result: list[tuple[int, int, bool]] = []
    for i, (start, end, idx) in enumerate(kept):
        next_start = kept[i + 1][0] if i + 1 < len(kept) else len(clean_text)
        window = clean_text[end : min(next_start, end + TRANSLATION_WINDOW)]
        zh_variants = entries[idx]["chinese_variants"]  # type: ignore[assignment]
        translated = any(zh in window for zh in zh_variants)  # type: ignore[union-attr]
        result.append((start, idx, translated))
    return result


def second_occurrence_labels(
    occurrences: list[tuple[int, int, bool]], entries: list[dict[str, object]]
) -> dict[int, int]:
    """Map entry_index -> offset-of-second-occurrence for entries that occur >=2
    times in the unit but carry fewer than two translations."""
    grouped: dict[int, list[tuple[int, bool]]] = {}
    for offset, idx, translated in occurrences:
        grouped.setdefault(idx, []).append((offset, translated))
    flagged: dict[int, int] = {}
    for idx, occ in grouped.items():
        if len(occ) >= 2 and sum(t for _, t in occ) < 2:
            flagged[idx] = occ[1][0]
    return flagged


def paragraph_suspects(paragraph: str, entries: list[dict[str, object]]) -> list[str]:
    suspects: list[str] = []
    for entry in entries:
        regexes = entry["english_regexes"]
        zh_variants = entry["chinese_variants"]
        if not any(regex.search(paragraph) for regex in regexes):
            continue
        if any(zh in paragraph for zh in zh_variants):
            continue
        suspects.append(str(entry["label"]))
    return suspects


def scan_index_file(
    md_file: Path, text: str, entries: list[dict[str, object]]
) -> list[tuple[int, int, list[str], str]]:
    # index.md counting units: each Compilation Summary paragraph, and each
    # "## {file}.md" entry block's "- **Summary:**" line. Both get first-mention
    # checking (paragraph_suspects) and the within-unit second-occurrence check.
    findings: list[tuple[int, int, list[str], str]] = []
    for block in sectioned_blocks(text):
        raw = str(block["text"])
        is_compilation = str(block["section"]) == "Compilation Summary"
        is_summary_line = "- **Summary:**" in raw
        if not (is_compilation or is_summary_line):
            continue
        cleaned = clean_paragraph(raw)
        occ_text = clean_for_occurrences(raw)
        if not occ_text:
            continue

        suspects = paragraph_suspects(occ_text, entries)
        labels = list(suspects)
        already = set(suspects)
        flagged = second_occurrence_labels(resolve_occurrences(occ_text, entries), entries)
        for idx in flagged:
            label = str(entries[idx]["label"])
            if label not in already:
                labels.append(f"{label} (2nd)")

        if labels:
            findings.append((int(block["start"]), int(block["end"]), labels, cleaned))
    return findings


def scan_regular_file(
    md_file: Path, text: str, entries: list[dict[str, object]]
) -> list[tuple[int, int, list[str], str]]:
    # Scannable blocks in document order, with cleaned text attached.
    scan_blocks: list[dict[str, object]] = []
    for block in sectioned_blocks(text):
        if block["section"] in SKIP_SECTIONS:
            continue
        cleaned = clean_paragraph(str(block["text"]))
        if not cleaned:
            continue
        block["clean"] = cleaned
        block["clean_occ"] = clean_for_occurrences(str(block["text"]))
        scan_blocks.append(block)

    # Collect flags per term, then group by the block they land on so the output
    # keeps one line per suspect location (matching the index-file scanner).
    grouped: dict[tuple[int, int], dict[str, object]] = {}

    def flag(block: dict[str, object], label: str) -> None:
        key = (int(block["start"]), int(block["end"]))
        bucket = grouped.setdefault(key, {"labels": [], "clean": block["clean"]})
        bucket["labels"].append(label)  # type: ignore[union-attr]

    rel_path = md_file.relative_to(ROOT).as_posix()
    is_query_file = rel_path.startswith("wiki/queries/")

    for entry in entries:
        regexes = entry["english_regexes"]
        zh_variants = entry["chinese_variants"]

        occurrences = []
        for block in scan_blocks:
            clean = str(block["clean"])
            if not any(regex.search(clean) for regex in regexes):
                continue
            translated = any(zh in clean for zh in zh_variants)
            occurrences.append((block, translated))

        if not occurrences:
            continue

        first_block, first_translated = occurrences[0]
        first_major = int(first_block["major"])

        # First meaningful mention must be translated.
        if not first_translated:
            flag(first_block, str(entry["label"]))

        # If the term reappears in a later major section, one of those later
        # mentions must be translated; otherwise flag the earliest one.
        later = [(b, t) for (b, t) in occurrences if int(b["major"]) > first_major]
        if later and not any(t for (_, t) in later):
            flag(later[0][0], str(entry["label"]))

        # Query-file exception: selected recurring terms should re-show their
        # Chinese on first mention in each ### subsection (with automatic ## fallback
        # because subsection scopes also increment on ## headings).
        selected_query_term = bool(entry.get("has_abbreviation")) or str(entry["label"]) in QUERY_SUBSECTION_EXTRA_LABELS
        if is_query_file and selected_query_term:
            by_subsection: dict[int, list[tuple[dict[str, object], bool]]] = {}
            for block, translated in occurrences:
                by_subsection.setdefault(int(block["subsection"]), []).append((block, translated))
            for subsection_occurrences in by_subsection.values():
                if any(translated for (_, translated) in subsection_occurrences):
                    continue
                flag(subsection_occurrences[0][0], str(entry["label"]))

    # Within-section second-occurrence rule (concept/summary/MOC/slide files;
    # query files keep their own aggressive exception above). The counting unit
    # is the innermost heading section (subsection ordinal). A term occurring
    # twice or more in one unit must carry at least two inline translations.
    if not is_query_file:
        by_subsection_blocks: dict[int, list[dict[str, object]]] = {}
        for block in scan_blocks:
            by_subsection_blocks.setdefault(int(block["subsection"]), []).append(block)
        for unit_blocks in by_subsection_blocks.values():
            # Concatenate the section's blocks into one unit text, remembering
            # each block's char offset so a flagged 2nd occurrence maps back to
            # the line it actually sits on.
            offsets: list[tuple[int, dict[str, object]]] = []
            segments: list[str] = []
            cursor = 0
            for block in unit_blocks:
                segment = str(block["clean_occ"])
                offsets.append((cursor, block))
                segments.append(segment)
                cursor += len(segment) + 1
            unit_text = " ".join(segments)

            flagged = second_occurrence_labels(resolve_occurrences(unit_text, entries), entries)
            for idx, second_offset in flagged.items():
                block = unit_blocks[0]
                for start_offset, candidate in offsets:
                    if second_offset >= start_offset:
                        block = candidate
                    else:
                        break
                label = f"{str(entries[idx]['label'])} (2nd)"
                key = (int(block["start"]), int(block["end"]))
                bucket = grouped.setdefault(key, {"labels": [], "clean": block["clean"]})
                if label not in bucket["labels"]:  # type: ignore[operator]
                    bucket["labels"].append(label)  # type: ignore[union-attr]

    findings: list[tuple[int, int, list[str], str]] = []
    for (start, end) in sorted(grouped):
        bucket = grouped[(start, end)]
        findings.append((start, end, list(bucket["labels"]), str(bucket["clean"])))
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
    diff_cmd = ["git", "diff", "--unified=0", "--", *relative_paths]
    diff = subprocess.run(
        diff_cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    changed = parse_unified_zero_diff(diff.stdout)

    status_cmd = ["git", "status", "--short", "--", *relative_paths]
    status = subprocess.run(
        status_cmd,
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
        description="List suspect untranslated medical terms in markdown files."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Markdown files or directories to scan. Defaults to main wiki content.",
    )
    parser.add_argument(
        "--glossary",
        default=str(DEFAULT_GLOSSARY),
        help="Path to the bilingual glossary file.",
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
    entries = load_glossary(glossary_path)

    if not markdown_files:
        print("No markdown files found.")
        return

    changed_lines_by_file = git_changed_lines(markdown_files) if args.git_diff else {}
    findings: list[tuple[Path, int, list[str], str]] = []

    for md_file in markdown_files:
        raw_text = md_file.read_text(encoding="utf-8")
        body = strip_code_fences(strip_frontmatter(raw_text))
        if args.git_diff and md_file not in changed_lines_by_file:
            continue
        rel_path = md_file.relative_to(ROOT).as_posix()
        if rel_path == "wiki/index.md":
            file_findings = scan_index_file(md_file, body, entries)
        else:
            file_findings = scan_regular_file(md_file, body, entries)
        changed_lines = changed_lines_by_file.get(md_file)
        for line_no, end_line, suspects, cleaned in file_findings:
            if changed_lines is not None and not overlaps_changed_lines(line_no, end_line, changed_lines):
                continue
            findings.append((md_file, line_no, suspects, cleaned))

    if not findings:
        print("No suspect bilingual term gaps found.")
        return

    print("SUSPECT BILINGUAL TERM GAPS")
    print("(Heuristic output; review before editing.)")
    print()
    for md_file, line_no, suspects, cleaned in findings:
        rel_path = md_file.relative_to(ROOT)
        snippet = cleaned[:180]
        if len(cleaned) > 180:
            snippet += "..."
        term_list = ", ".join(sorted(set(suspects)))
        print(f"{rel_path}:{line_no}  {term_list}")
        print(f"  {snippet}")

    # Trailing total. The findings above end on a raw snippet row, so a reader
    # who pipes this through `tail` cannot tell a truncated list from a short
    # one. Repeating the count last means the number survives truncation and
    # stops matching the visible rows, which is the signal that the read was
    # partial. Keep this the final line.
    print()
    print(
        f"TOTAL: {len(findings)} flagged line(s) across "
        f"{len({f for f, _, _, _ in findings})} file(s)."
    )


if __name__ == "__main__":
    main()
