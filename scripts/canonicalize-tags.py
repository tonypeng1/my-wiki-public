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
  ultrasound, mri, ct, x-ray are KEPT as-is, but imaging-finding is added
  alongside them if absent.

Two separate jobs, do not conflate them:
  1. REWRITE a known synonym to its canonical tag (the table above). Writes files.
  2. REPORT any tag that is neither canonical nor a known synonym. Read-only.

Job 2 exists because a dict lookup with a fallback (`SYNONYMS.get(tag, tag)`)
silently passes unknown tags through unchanged — so before this check the
script could only ever find tags someone had already thought to enumerate,
and reported "all tags are already canonical" over everything else.
Unknown tags are reported, never auto-stripped: deciding whether a tag is
junk or a miscategorized real domain needs a human. Exit status is 1 when
any are found, so /lint and /post-ingest can actually fail on this.
"""

import re
import sys
from pathlib import Path

WIKI_ROOT = Path(__file__).parent.parent / "wiki"

# The closed canonical set from CLAUDE.md. Keep in sync with the "Canonical Tags"
# section there — that document is the source of truth, this is its executable copy.
CANONICAL_DOMAINS: set[str] = {
    "biomarker", "cardiology", "hematology", "hepatic", "metabolic", "glycemic",
    "lipid", "genitourinary", "immunology", "gastrointestinal", "dermatology",
    "musculoskeletal", "sleep-medicine", "sexual-health", "neurology", "respiratory",
}

CANONICAL_CROSS_CUTTING: set[str] = {
    "screening", "imaging-finding", "clinical-finding", "medication", "procedure",
}

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
    # Generic "imaging" means imaging-finding in both file types. The specific
    # modality tags below are concept-only, because summaries keep the modality.
    "imaging": "imaging-finding",
}

# Synonyms that apply to concepts only (on summaries, keep the modality tag)
CONCEPT_ONLY_SYNONYMS: dict[str, str] = {
    "ultrasound": "imaging-finding",
    "mri": "imaging-finding",
    "ct": "imaging-finding",
    "x-ray": "imaging-finding",
}

# Modality tags kept on summaries; imaging-finding must accompany them
SUMMARY_MODALITY_TAGS = {"ultrasound", "mri", "ct", "x-ray"}

# What each file type is allowed to carry. Modality tags are summary-only:
# on a concept they canonicalize to imaging-finding (CONCEPT_ONLY_SYNONYMS).
CANONICAL_CONCEPT_TAGS = CANONICAL_DOMAINS | CANONICAL_CROSS_CUTTING
CANONICAL_SUMMARY_TAGS = CANONICAL_CONCEPT_TAGS | SUMMARY_MODALITY_TAGS

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


def process_file(
    path: Path, is_summary: bool
) -> tuple[bool, list[tuple[str, str]], list[str]]:
    """Process one file. Returns (changed, replacements, unknown_tags).

    unknown_tags are reported to the caller, never rewritten — see module docstring.
    """
    text = path.read_text(encoding="utf-8")

    match = TAGS_RE.search(text)
    if not match:
        return False, [], []

    original_tags_str = match.group(2)
    tags = parse_tags(original_tags_str)

    if is_summary:
        new_tags, replacements = canonicalize_for_summaries(tags)
        allowed = CANONICAL_SUMMARY_TAGS
    else:
        new_tags, replacements = canonicalize_for_concepts(tags)
        allowed = CANONICAL_CONCEPT_TAGS

    # Check AFTER canonicalization so a known synonym is not reported as unknown.
    unknown = [t for t in new_tags if t not in allowed]

    if not replacements:
        return False, [], unknown

    new_tags_str = serialize_tags(new_tags)
    new_text = TAGS_RE.sub(
        lambda m: m.group(1) + new_tags_str + m.group(3),
        text,
        count=1,
    )
    path.write_text(new_text, encoding="utf-8")
    return True, replacements, unknown


def main() -> int:
    total_changed = 0
    report_lines: list[str] = []
    unknown_by_tag: dict[str, list[str]] = {}

    for folder, is_summary in [
        (WIKI_ROOT / "concepts", False),
        (WIKI_ROOT / "summaries", True),
    ]:
        for md_file in sorted(folder.glob("*.md")):
            changed, replacements, unknown = process_file(md_file, is_summary)
            rel = md_file.relative_to(WIKI_ROOT.parent)
            if changed:
                total_changed += 1
                report_lines.append(f"  {rel}")
                for old, new in replacements:
                    report_lines.append(f"    {old} → {new}")
            for tag in unknown:
                unknown_by_tag.setdefault(tag, []).append(str(rel))

    if total_changed:
        print(f"Rewrote known synonyms in {total_changed} file(s):")
        print("\n".join(report_lines))
    else:
        print("No known synonyms to rewrite.")

    if not unknown_by_tag:
        print("\nAll tags are canonical.")
        return 0

    n_files = len({f for files in unknown_by_tag.values() for f in files})
    print(
        f"\nUNKNOWN TAGS: {len(unknown_by_tag)} distinct tag(s) across {n_files} file(s). "
        f"Not in the canonical set and not a known synonym."
    )
    print("Nothing was changed for these — decide each one, then either add it to "
          "CLAUDE.md, map it in COMMON_SYNONYMS, or remove it from the file.\n")
    for tag, files in sorted(unknown_by_tag.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        shown = ", ".join(files[:3])
        more = f", +{len(files) - 3} more" if len(files) > 3 else ""
        print(f"  {tag:<26} {len(files):>3} file(s)  {shown}{more}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
