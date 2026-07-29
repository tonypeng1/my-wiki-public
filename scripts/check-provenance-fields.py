#!/usr/bin/env python3
"""
Validate the provenance fields on wiki/summaries/ frontmatter.

Three fields record who produced a document and how it read — a different axis
from `tags`, which record what it is about:

  facility       the site that PERFORMED the study
  physician      the ordering or interpreting clinician
  result-status  normal | mixed | abnormal

The vocabularies are read from the tables in CLAUDE.md ("Provenance fields"
under Summary File Format) at run time — see _provenance_vocab.py. That
document is the source of truth in the literal sense: adding a row there is
the whole edit, and this file holds no copy to fall out of step with it.

Four checks. The first three FAIL (exit 1); the fourth is informational.

  1. UNKNOWN VALUE   — a value outside the closed vocabulary. Usually a new
     site or clinician that was never added to CLAUDE.md, or a typo'd slug that
     will silently never match.

  2. WRONG FILE TYPE — a provenance field on a concept. A summary describes one
     document from one site on one date, so it has a single provenance; a
     concept spans many draws across years and therefore has none. Provenance
     lives per-row in the concept's canonical table, not in its frontmatter.

  3. PROVENANCE AS TAG — a facility, physician, or status value found in a
     `tags:` list. This is the regression these fields exist to prevent: before
     the migration, provenance was tags (a clinic slug, a physician slug,
     `abnormal-result`), which polluted the closed clinical vocabulary and —
     because every facility clears the 3-article threshold — would have
     mechanically demanded a MOC for a clinic.

  4. MISSING (informational) — a summary with no facility / physician /
     result-status. Not a failure: the fields are omitted rather than guessed
     when the source document does not name a site or clinician, and a document
     that reports no test result (a medication list) correctly has no status.
     Listed so the gaps stay visible and can be backfilled from raw/.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _provenance_vocab import (  # noqa: E402
    LEGACY_STATUS_TAGS,
    RESULT_STATUSES,
    VocabularyError,
    facilities,
    physicians,
)

WIKI_ROOT = Path(__file__).parent.parent / "wiki"

FIELDS = ("facility", "physician", "result-status")

FIELD_RE = {
    field: re.compile(rf"^{re.escape(field)}:\s*(.+?)\s*$", re.MULTILINE)
    for field in FIELDS
}
TAGS_RE = re.compile(r"^tags:\s*\[([^\]]*?)\]\s*$", re.MULTILINE)


def load_vocab() -> tuple[dict[str, frozenset[str]], frozenset[str]]:
    """The closed vocabularies, and every value that must never be a tag again.

    Loaded here rather than at import so a malformed CLAUDE.md surfaces as the
    one-line error main() prints, not an import traceback.
    """
    vocab = {
        "facility": facilities(),
        "physician": physicians(),
        "result-status": RESULT_STATUSES,
    }
    # The pre-migration status tags are not current field values, but they are
    # what a regression would most likely reintroduce.
    forbidden = frozenset().union(*vocab.values(), LEGACY_STATUS_TAGS)
    return vocab, forbidden


def field_values(raw: str) -> list[str]:
    """Parse a field value into its slugs.

    `physician` accepts a flow-style list when one document has several authors
    — a prescription export written by two specialists four days apart. Every
    other case is a bare slug, and both shapes validate the same way.
    """
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        return [v.strip().strip("\"'") for v in raw[1:-1].split(",") if v.strip()]
    return [raw.strip("\"'")]


def frontmatter(text: str) -> str:
    """Return the YAML frontmatter block, or '' when the file has none."""
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[:end] if end != -1 else ""


def main() -> int:
    try:
        vocab, forbidden_tags = load_vocab()
    except VocabularyError as exc:
        print(f"CANNOT CHECK: {exc}")
        return 1

    unknown: list[tuple[str, str, str]] = []      # (file, field, value)
    wrong_type: list[tuple[str, str]] = []        # (file, field)
    as_tag: list[tuple[str, str]] = []            # (file, tag)
    missing: dict[str, list[str]] = {f: [] for f in vocab}
    n_summaries = 0

    for folder in ("concepts", "summaries"):
        is_summary = folder == "summaries"
        for md in sorted((WIKI_ROOT / folder).glob("*.md")):
            rel = str(md.relative_to(WIKI_ROOT.parent))
            fm = frontmatter(md.read_text(encoding="utf-8"))
            if not fm:
                continue
            if is_summary:
                n_summaries += 1

            for field, allowed in vocab.items():
                m = FIELD_RE[field].search(fm)
                if m is None:
                    if is_summary:
                        missing[field].append(rel)
                    continue
                if not is_summary:
                    wrong_type.append((rel, field))
                    continue
                for value in field_values(m.group(1)):
                    if value not in allowed:
                        unknown.append((rel, field, value))

            tm = TAGS_RE.search(fm)
            if tm:
                for tag in (t.strip() for t in tm.group(1).split(",")):
                    if tag in forbidden_tags:
                        as_tag.append((rel, tag))

    failed = False

    if unknown:
        failed = True
        print(f"UNKNOWN VALUE: {len(unknown)} field(s) outside the closed vocabulary.")
        print("Add the value to the tables in CLAUDE.md, or fix the slug.\n")
        for rel, field, value in unknown:
            print(f"  {rel}\n    {field}: {value}")
        print()

    if wrong_type:
        failed = True
        print(f"WRONG FILE TYPE: {len(wrong_type)} provenance field(s) on concept files.")
        print("Concepts carry provenance per-row in their canonical table, not in frontmatter.\n")
        for rel, field in wrong_type:
            print(f"  {rel}    {field}")
        print()

    if as_tag:
        failed = True
        print(f"PROVENANCE AS TAG: {len(as_tag)} provenance value(s) found in a tags: list.")
        print("These belong in their own field — see Provenance fields in CLAUDE.md.\n")
        for rel, tag in as_tag:
            print(f"  {rel}    {tag}")
        print()

    if not failed:
        print(f"Provenance fields are valid across {n_summaries} summaries.")

    n_missing = sum(len(v) for v in missing.values())
    if n_missing:
        print(f"\nMISSING (informational — not a failure): {n_missing} unset field(s).")
        print("Omitted-not-guessed is correct when the source names no site or clinician,")
        print("and a document reporting no test result has no status. Backfill from raw/")
        print("only where the document does name one.\n")
        for field, files in missing.items():
            if not files:
                continue
            print(f"  {field} — {len(files)} summary(ies)")
            for rel in files:
                print(f"      {rel}")
        # Echo the count last. The MISSING header above already carries it, but
        # it sits ABOVE a file list of unbounded length, so a reader who pipes
        # this through `tail` loses exactly the number that would have revealed
        # the truncation. See the note in check-bilingual-terms.py.
        print(f"\nTOTAL: {n_missing} unset field(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
