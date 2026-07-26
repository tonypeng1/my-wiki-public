#!/usr/bin/env python3
"""
Extract every STATE claim in wiki/concepts/, grouped by the concept it is
about, and emit only the groups whose claims disagree.

This is the status counterpart to extract-claims.py. That script compares
numbers; this one compares the words around them — the class of contradiction
p4b-contradiction-check.md explicitly leaves out ("resolved" vs "active",
"currently taking" vs "discontinued").

  === {medication} ===
  DIMENSION medication  (ACTIVE vs STOPPED)
    ACTIVE   {condition}.md:31   currently on {medication} 10 mg nightly …
    STOPPED  {medication}.md:22  SELF  discontinued YYYY-MM-DD …

The asymmetry that shapes everything here: the numeric checker can COMPUTE a
disagreement (28.4 != 28.7). State words have no such oracle — "elevated" and
"normal" do not compare, and whether two state words genuinely conflict is a
clinical judgement. So this script only ever proposes candidates, tiered by
how likely the conflict is to be real, and the agent decides. Precision is
worth more than recall: a pass that cries wolf gets ignored.

Three design limits, deliberate:

1. Dimensions are restricted to states that are singular and current —
   a medication is either being taken or not; a condition is either active or
   not; a finding is either there or not. Level words (elevated/normal) and
   severity words (mild/severe) are NOT dimensions: those legitimately differ
   between two dated measurements, which is longitudinal data, not a
   contradiction. That is the same exclusion p4b makes for numbers.
2. A claim carrying its own date is demoted, not dropped. "Elevated in 2021"
   next to "normal now" is history; "currently taking" next to "discontinued"
   is drift. Dated claims land in REVIEW, undated pairs in CONFLICT.
3. The concept's own file is labelled SELF but is NOT treated as authority.
   Nothing here is auto-fixable, so there is no anchored/peer split to make —
   every finding goes to a human either way.

Exit code 0 in all cases.
"""

import argparse
import re
import sys
from pathlib import Path

from _claims_common import (
    CLASS_ALIASES,
    CONCEPTS_DIR,
    SOURCES_ENTRY_RE,
    TABLE_ROW_RE,
    PROXIMITY_CHARS,
    build_mention_map,
    condense,
    frontmatter_line_count,
    mask_backlinks,
    mentioned_concepts,
    strip_frontmatter_block,
)

MAX_STATUS_CHARS = 160
MAX_PER_POLARITY = 4  # how many agreeing lines to print before summarizing

# --- what counts as a state claim -------------------------------------------
#
# Each dimension holds two opposing polarities. A phrase is matched
# case-insensitively on word boundaries; spaces mean "one or more spaces".
# Negated forms are spelled out in the bucket they actually mean ("no longer
# taking" is STOPPED) rather than inferred, because inferring negation from
# nearby "not" is where this kind of checker starts fabricating findings.
DIMENSIONS: dict[str, dict[str, tuple[str, ...]]] = {
    "medication": {
        "ACTIVE": (
            "currently taking", "currently on", "current medication",
            "is taking", "still taking", "still on", "remains on",
            "continues to take", "continues on", "ongoing treatment with",
            "maintained on", "takes nightly", "taken nightly", "taking nightly",
            "active prescription", "currently prescribed",
        ),
        "STOPPED": (
            "discontinued", "self-discontinued", "was stopped", "has stopped",
            "stopped taking", "no longer taking", "no longer on",
            "no longer prescribed", "tapered off", "came off", "taken off",
            "withdrawn", "ceased", "last dose", "off all", "d/c",
        ),
    },
    "condition": {
        "ACTIVE": (
            "remains active", "is active", "currently active", "still present",
            "still symptomatic", "currently symptomatic", "unresolved",
            "persists", "persisting", "recurring", "has returned",
            "ongoing symptoms",
        ),
        # "normalized" / "cleared" are deliberately absent: they describe a
        # VALUE returning to range, which is level language (design limit 1),
        # and they fired only on lipid trajectories in testing.
        "RESOLVED": (
            "resolved", "resolution of", "in remission", "remitted",
            "no longer present", "has not returned", "symptom-free",
        ),
    },
    # OFF by default — see LOW_PRECISION_DIMENSIONS below.
    "presence": {
        "PRESENT": (
            "was identified", "were identified", "is present", "are present",
            "was detected", "positive for", "evidence of", "confirmed on",
            "seen on", "visualized", "visualised",
        ),
        "ABSENT": (
            "no evidence of", "not detected", "was not identified",
            "were not identified", "not present", "negative for", "ruled out",
            "denies", "without evidence", "none identified", "unremarkable",
        ),
    },
}

# A dated claim is a snapshot ("discontinued 2026-06-23"); an undated one
# asserts the present ("currently taking"). Comparing the two is the whole
# game — see tier_of().
ISO_DATE_RE = re.compile(r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b")
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
QUESTION_RE = re.compile(r"\?\s*$")
SECTION_RE = re.compile(r"^\s{0,3}#{1,6}\s")
# Two sections are skipped wholesale, per the article format in CLAUDE.md:
# Overview is "2-4 sentence plain explanation" — textbook knowledge by
# convention, not patient state — and Open Questions holds hypotheses being
# asked about rather than claims. Patient status lives in Key Details.
SKIP_SECTION_RE = re.compile(r"^\s{0,3}#{1,6}\s*(overview|open questions)\b",
                             re.IGNORECASE)
# "…in asymptomatic patients" is a statement about a population, i.e. general
# clinical knowledge, not a claim about this patient.
GENERIC_POPULATION_RE = re.compile(
    r"^\W{0,3}(?:patients|individuals|adults|men|women|people|population)\b",
    re.IGNORECASE)


# Presence is off unless asked for. Its cues ("ruled out", "are present",
# "unremarkable") attach to whichever noun sits nearest, and proximity cannot
# tell which noun they belong to: on the real corpus "with HBV/HCV ruled out"
# was filed as a claim that the liver nodule was ruled out. Every presence
# finding in testing was a false positive, and none was a real contradiction.
# Medication and condition cues do not share the problem — "discontinued" and
# "in remission" take the drug or the condition as their subject.
LOW_PRECISION_DIMENSIONS = ("presence",)


def _phrase_pattern(phrases: tuple[str, ...]) -> re.Pattern:
    alts = sorted((re.escape(p).replace(r"\ ", r"\s+") for p in phrases),
                  key=len, reverse=True)
    return re.compile(rf"(?<!\w)(?:{'|'.join(alts)})(?!\w)", re.IGNORECASE)


PATTERNS = {
    dim: {pol: _phrase_pattern(phrases) for pol, phrases in polarities.items()}
    for dim, polarities in DIMENSIONS.items()
}


def state_hits(line: str,
               dimensions: tuple[str, ...]) -> list[tuple[str, str, str, int]]:
    """(dimension, polarity, matched phrase, offset) for every cue on the line.

    Longest-phrase-wins within a dimension: "no longer taking" must not also
    register as ACTIVE via "taking". Overlapping spans are resolved by
    dropping any hit contained in a longer one.
    """
    raw: list[tuple[str, str, str, int, int]] = []
    for dim in dimensions:
        for pol, pattern in PATTERNS[dim].items():
            for m in pattern.finditer(line):
                raw.append((dim, pol, m.group(0), m.start(), m.end()))

    hits = []
    for dim, pol, phrase, start, end in raw:
        covered = any(
            other_start <= start and end <= other_end
            and (other_end - other_start) > (end - start)
            for _, _, _, other_start, other_end in raw
        )
        if covered or GENERIC_POPULATION_RE.match(line[end:end + 24]):
            continue
        hits.append((dim, pol, " ".join(phrase.split()), start))
    return hits


def scan_files(files: list[Path], mention_map: dict[str, str], stems: set[str],
               dimensions: tuple[str, ...]) -> dict[tuple[str, str], list[dict]]:
    """Collect state claims keyed by (concept stem, dimension)."""
    claims: dict[tuple[str, str], list[dict]] = {}

    for md_file in files:
        text = md_file.read_text(encoding="utf-8")
        offset = frontmatter_line_count(text)
        skipping_section = False

        for i, line in enumerate(strip_frontmatter_block(text).split("\n"),
                                 start=offset + 1):
            if SECTION_RE.match(line):
                skipping_section = bool(SKIP_SECTION_RE.match(line))
                continue
            if skipping_section or not line.strip():
                continue
            # A table row is the canonical record: dated measurements whose
            # notes are scoped to that draw, never a current-state assertion.
            if TABLE_ROW_RE.match(line):
                continue
            if QUESTION_RE.search(line) or SOURCES_ENTRY_RE.match(line):
                continue

            masked = mask_backlinks(line)
            hits = state_hits(masked, dimensions)
            if not hits:
                continue

            mentions = mentioned_concepts(line, mention_map, stems)
            if not mentions:
                continue

            for subject, positions in mentions.items():
                for dim, pol, phrase, at in hits:
                    if not any(abs(at - p) <= PROXIMITY_CHARS for p in positions):
                        continue
                    claims.setdefault((subject, dim), []).append({
                        "polarity": pol,
                        "phrase": phrase,
                        "label": f"{md_file.name}:{i}",
                        "self": md_file.stem == subject,
                        "date": claim_date(masked, at),
                        "text": condense(line, MAX_STATUS_CHARS),
                    })
    return claims


def claim_date(masked: str, at: int) -> str:
    """The date this claim carries, as a sortable string ('' if none).

    The date NEAREST the cue phrase, not the newest on the line: a line can
    hold several ("discontinued 2026-06-23 … next visit ~2026-07-14"), and
    only the one next to the cue is the date of the state being asserted.

    A year alone is padded to its year-end so it sorts after that year's
    dated claims: '2021' is less precise than '2021-04-02', not earlier.
    """
    for pattern, pad in ((ISO_DATE_RE, ""), (YEAR_RE, "-12-31")):
        found = list(pattern.finditer(masked))
        if found:
            nearest = min(found, key=lambda m: abs(m.start() - at))
            return nearest.group(0) + pad
    return ""


def tier_of(entries: list[dict]) -> str:
    """CONFLICT or REVIEW for a group holding opposing polarities.

    Two shapes are real conflicts:
      1. two undated claims disagree — both assert the present tense
      2. an undated claim disagrees with the NEWEST dated claim — the stale
         "currently taking" against the "discontinued 2026-06-23" that
         superseded it. This is the common shape of status drift

    Everything else is REVIEW: opposing claims at different dates are a
    state that changed over time, which is history, not a contradiction.

    Opposing cues on ONE line never conflict. "Active until 2026-06, now
    resolved" is a contrast sentence — correct prose that names both states
    on purpose — and flagging it was the single biggest false positive in
    testing.
    """
    by_line: dict[str, set[str]] = {}
    for e in entries:
        by_line.setdefault(e["label"], set()).add(e["polarity"])
    entries = [e for e in entries if len(by_line[e["label"]]) == 1]
    if len({e["polarity"] for e in entries}) < 2:
        return "REVIEW"

    undated = {e["polarity"] for e in entries if not e["date"]}
    if len(undated) >= 2:
        return "CONFLICT"

    dated = [e for e in entries if e["date"]]
    if undated and dated:
        newest = max(e["date"] for e in dated)
        newest_polarities = {e["polarity"] for e in dated if e["date"] == newest}
        if newest_polarities - undated:
            return "CONFLICT"

    return "REVIEW"


def dedupe(entries: list[dict]) -> list[dict]:
    """One entry per (line, polarity) — a line naming two cues of the same
    polarity is one claim, not two."""
    seen: set[tuple[str, str]] = set()
    out = []
    for e in entries:
        key = (e["label"], e["polarity"])
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def render(subject: str, dim: str, entries: list[dict]) -> list[str]:
    """One block per (concept, dimension).

    The minority side prints in full — it is usually the drift — while a
    large agreeing side is truncated. Thirteen ways of saying "discontinued"
    bury the one line that says "currently taking"; the count is kept so the
    weight of the majority is still visible.
    """
    polarities = sorted(DIMENSIONS[dim],
                        key=lambda p: sum(1 for e in entries
                                          if e["polarity"] == p))
    width = max(len(e["label"]) for e in entries)
    out = [f"=== {subject} ===",
           f"DIMENSION {dim}  ({' vs '.join(DIMENSIONS[dim])})"]
    for pol in polarities:
        same = sorted((x for x in entries if x["polarity"] == pol),
                      key=lambda x: (not x["self"], x["label"]))
        for e in same[:MAX_PER_POLARITY]:
            flags = "".join([" SELF" if e["self"] else "",
                             f" [{e['date']}]" if e["date"] else " [undated]"])
            out.append(f"  {pol:<8} {e['label']:<{width}} "
                       f"[{e['phrase']}]{flags}")
            out.append(f"           {e['text']}")
        if len(same) > MAX_PER_POLARITY:
            out.append(f"  {pol:<8} … and {len(same) - MAX_PER_POLARITY} more "
                       f"agreeing {pol} line(s)")
    out.append("")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find status/state contradictions across wiki articles.")
    parser.add_argument(
        "paths", nargs="*", type=Path,
        help="extra files or directories to scan for restatements "
             "(default: wiki/concepts/ only). Subjects always come from "
             "wiki/concepts/. Widening to wiki/queries/ or wiki/deliverables/ "
             "is noisy: those are dated snapshots, correct as of their date.")
    parser.add_argument(
        "--include-presence", action="store_true",
        help="also check the low-precision presence dimension "
             "(present/absent). Off by default — see LOW_PRECISION_DIMENSIONS.")
    args = parser.parse_args()

    dimensions = tuple(d for d in DIMENSIONS
                       if d not in LOW_PRECISION_DIMENSIONS
                       or args.include_presence)

    concept_files = sorted(CONCEPTS_DIR.glob("*.md"))
    stems = {f.stem for f in concept_files}
    mention_map = build_mention_map(concept_files, exclude=CLASS_ALIASES)

    scan = list(concept_files)
    for path in args.paths:
        if path.is_dir():
            scan.extend(sorted(p for p in path.rglob("*.md")
                               if p not in concept_files))
        elif path.is_file() and path not in concept_files:
            scan.append(path)

    claims = scan_files(scan, mention_map, stems, dimensions)

    conflicts: list[list[str]] = []
    review: list[list[str]] = []
    for (subject, dim), entries in sorted(claims.items()):
        entries = dedupe(entries)
        if len({e["polarity"] for e in entries}) < 2:
            continue  # every claim agrees; nothing to judge
        block = render(subject, dim, entries)
        (conflicts if tier_of(entries) == "CONFLICT" else review).append(block)

    out: list[str] = [
        f"Files scanned: {len(scan)}  (subjects: {len(stems)} concepts)",
        f"Dimensions: {', '.join(dimensions)}",
        f"State claims collected: {sum(len(v) for v in claims.values())}",
        f"Disagreeing groups: {len(conflicts)} conflict, {len(review)} review",
        "",
        "CONFLICT — an undated claim (asserting the present) disagrees with",
        "  another undated claim or with the NEWEST dated one, or two claims",
        "  disagree on the same date. This is where status drift lives: one",
        "  file was updated and the other kept its old present tense.",
        "REVIEW  — opposing claims at different dates: most likely a state",
        "  that changed over time, which is history, not a contradiction.",
        "SELF marks the concept's own file. It is the likeliest place for the",
        "  current truth, but it is NOT authoritative — verify before editing.",
        "Nothing here is auto-fixable: no state word can be computed correct.",
        "",
    ]
    if conflicts:
        out.append("################ CONFLICT ################")
        out.append("")
        for block in conflicts:
            out.extend(block)
    else:
        out.append("CONFLICT: none")
        out.append("")
    if review:
        out.append("################ REVIEW ################")
        out.append("")
        for block in review:
            out.extend(block)
    else:
        out.append("REVIEW: none")

    try:
        print("\n".join(out))
    except BrokenPipeError:
        pass  # output was piped into head/grep and the reader closed early


if __name__ == "__main__":
    main()
