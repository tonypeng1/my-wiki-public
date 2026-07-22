#!/usr/bin/env python3
"""
Canonicalize tags in wiki/concepts/ and wiki/summaries/ frontmatter.

Synonym → canonical mapping from CLAUDE.md:
  infectious-disease          → immunology
  renal, urology              → genitourinary
  lab-test, blood-test        → biomarker
  endocrinology               → metabolic
  cardiovascular, cardiac,
    atherosclerosis,
    calcium-scoring           → cardiology
  cbc, hemostasis, anemia     → hematology
  liver-function, nafld,
    biliary                   → hepatic
  atherogenic, lipid-management,
    ldl-cholesterol           → lipid
  serology, viral-immunity    → immunology
  cancer-screening            → screening
  clinical-category,
    clinical-diagnosis,
    risk-state, risk-marker,
    benign                    → clinical-finding
  statin, antihyperglycemic   → medication
  imaging, ultrasound, mri,
    ct  (concepts only)       → imaging-finding

Special rule for summaries:
  ultrasound, mri, ct are KEPT as-is, but imaging-finding is added
  alongside them if absent.
"""

import re
import sys
from pathlib import Path

WIKI_ROOT = Path(__file__).parent.parent / "wiki"

# Synonyms that apply to BOTH concepts and summaries
COMMON_SYNONYMS: dict[str, str] = {
    "infectious-disease": "immunology",
    "renal": "genitourinary",
    "urology": "genitourinary",
    "lab-test": "biomarker",
    "blood-test": "biomarker",
    "endocrinology": "metabolic",
    "cardiovascular": "cardiology",
    "cardiac": "cardiology",
    "atherosclerosis": "cardiology",
    "calcium-scoring": "cardiology",
    "cbc": "hematology",
    "hemostasis": "hematology",
    "anemia": "hematology",
    "liver-function": "hepatic",
    "nafld": "hepatic",
    "biliary": "hepatic",
    "atherogenic": "lipid",
    "lipid-management": "lipid",
    "ldl-cholesterol": "lipid",
    "serology": "immunology",
    "viral-immunity": "immunology",
    "cancer-screening": "screening",
    "clinical-category": "clinical-finding",
    "clinical-diagnosis": "clinical-finding",
    "risk-state": "clinical-finding",
    "risk-marker": "clinical-finding",
    "benign": "clinical-finding",
    "statin": "medication",
    "antihyperglycemic": "medication",
}

# Synonyms that apply to concepts only (on summaries, keep the modality tag)
CONCEPT_ONLY_SYNONYMS: dict[str, str] = {
    "imaging": "imaging-finding",
    "ultrasound": "imaging-finding",
    "mri": "imaging-finding",
    "ct": "imaging-finding",
}

# Modality tags kept on summaries; imaging-finding must accompany them
SUMMARY_MODALITY_TAGS = {"ultrasound", "mri", "ct"}

TAGS_RE = re.compile(r"^(tags:\s*\[)([^\]]*?)(\]\s*)$", re.MULTILINE)


def parse_tags(tags_str: str) -> list[str]:
    return [t.strip() for t in tags_str.split(",") if t.strip()]


def serialize_tags(tags: list[str]) -> str:
    return ", ".join(tags)


def canonicalize_for_concepts(tags: list[str]) -> tuple[list[str], list[tuple[str, str]]]:
    """Return (new_tags, replacements) where replacements is list of (old, new)."""
    all_synonyms = {**COMMON_SYNONYMS, **CONCEPT_ONLY_SYNONYMS}
    new_tags: list[str] = []
    replacements: list[tuple[str, str]] = []
    seen: set[str] = set()

    for tag in tags:
        canonical = all_synonyms.get(tag, tag)
        if canonical != tag:
            replacements.append((tag, canonical))
        if canonical not in seen:
            seen.add(canonical)
            new_tags.append(canonical)
        # else: duplicate after canonicalization — drop it

    return new_tags, replacements


def canonicalize_for_summaries(tags: list[str]) -> tuple[list[str], list[tuple[str, str]]]:
    """Return (new_tags, replacements). Modality tags are kept; imaging-finding added if needed."""
    new_tags: list[str] = []
    replacements: list[tuple[str, str]] = []
    seen: set[str] = set()

    for tag in tags:
        canonical = COMMON_SYNONYMS.get(tag, tag)
        if canonical != tag:
            replacements.append((tag, canonical))
        if canonical not in seen:
            seen.add(canonical)
            new_tags.append(canonical)

    # If any modality tag is present and imaging-finding is absent, add it
    has_modality = any(t in SUMMARY_MODALITY_TAGS for t in new_tags)
    if has_modality and "imaging-finding" not in seen:
        new_tags.append("imaging-finding")
        replacements.append(("(added)", "imaging-finding"))

    return new_tags, replacements


def process_file(path: Path, is_summary: bool) -> tuple[bool, list[tuple[str, str]]]:
    """Process one file. Returns (changed, replacements)."""
    text = path.read_text(encoding="utf-8")

    match = TAGS_RE.search(text)
    if not match:
        return False, []

    original_tags_str = match.group(2)
    tags = parse_tags(original_tags_str)

    if is_summary:
        new_tags, replacements = canonicalize_for_summaries(tags)
    else:
        new_tags, replacements = canonicalize_for_concepts(tags)

    if not replacements:
        return False, []

    new_tags_str = serialize_tags(new_tags)
    new_text = TAGS_RE.sub(
        lambda m: m.group(1) + new_tags_str + m.group(3),
        text,
        count=1,
    )
    path.write_text(new_text, encoding="utf-8")
    return True, replacements


def main() -> None:
    total_changed = 0
    report_lines: list[str] = []

    for folder, is_summary in [
        (WIKI_ROOT / "concepts", False),
        (WIKI_ROOT / "summaries", True),
    ]:
        for md_file in sorted(folder.glob("*.md")):
            changed, replacements = process_file(md_file, is_summary)
            if changed:
                total_changed += 1
                rel = md_file.relative_to(WIKI_ROOT.parent)
                report_lines.append(f"  {rel}")
                for old, new in replacements:
                    report_lines.append(f"    {old} → {new}")

    if total_changed:
        print(f"Updated {total_changed} file(s):")
        print("\n".join(report_lines))
    else:
        print("No non-canonical tags found. All tags are already canonical.")


if __name__ == "__main__":
    main()
