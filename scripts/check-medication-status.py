#!/usr/bin/env python3
"""Flag missing stopped-medication context and occasional-use drift.

The failure this catches is an OMISSION, not a contradiction. When a medication is
discontinued, wiki/index.md and the MOC bullets rarely claim the patient is still
taking it — they simply never say the patient has stopped, and silence reads as
current. No existing check sees this: scripts/check-mirror-drift.py is satisfied once
the mirror is edited for any reason at all, and scripts/extract-status-claims.py
compares state words against state words, so an absent word cannot disagree with
anything. Pointed at mirrors that still carry the pre-stop wording,
scripts/extract-status-claims.py returns zero hits.

So this script takes the medication concept's own frontmatter `status:` as authority
and runs two deliberately asymmetric checks:

* ``stopped`` -- report every checked block that names the medication without a stop
  marker, because silence makes a discontinued medicine read as current;
* ``occasional`` -- verify the concept's explicit status line says the use is
  occasional, and report only index/MOC wording that positively implies regular use.
  A neutral mention makes no frequency claim and is left alone.

Usage:
  python3 scripts/check-medication-status.py [PATH ...] [--git-diff]

Findings come in four kinds:

  MISSING STOP    a block names the medication (generic, brand, or local brand) and
                  carries none of the stop markers. Read each one: a statement of
                  the drug's pharmacology ("amlodipine is QTc-neutral") or one
                  explicitly scoped to the past ("may have worsened PLMS during that
                  period") is timeless or already dated, and needs no marker. This
                  is a review list, not a defect list.
  CLASS MENTION   a block matches only a class alias ("the new β-blocker") with no
                  direct name. Review tier: worth reading, but a class alias goes
                  ambiguous the moment two drugs share a class, so it is never
                  reported as a definite miss.
  FREQUENCY MISMATCH
                  an index entry or MOC bullet for an occasional medication says it
                  is used daily, nightly, every/most day or night, regularly, or
                  routinely. Neutral mentions and clearly historical schedules are
                  not findings.
  STATUS MISMATCH frontmatter `status:` disagrees with the concept's own body status
                  line, an occasional medication has no explicit status line, or the
                  field uses a value outside the closed vocabulary. This is the cost
                  of putting status in frontmatter — two sources of truth inside one
                  file — so it is guarded rather than assumed.

Scanned for stopped medications: wiki/index.md entries whose Type is `concept`, MOC
bullets under `## Concepts`, and wiki/concepts/ bodies. Occasional-use frequency is
checked only in the medication's explicit concept status line and in index/MOC
mirrors. NOT scanned, deliberately — summary entries and `## Source Summaries`
bullets describe what a source document says on its own date, and a prescription
record legitimately records no stop; and wiki/queries/, which are dated snapshots
correct as of their date. Getting those exemptions wrong is what turns this into a
pass that gets ignored.

A medication with no `status:` is not checked. The field is omitted rather than
guessed when a concept states no status, following the same rule as the provenance
fields. Read-only; exit code is always 0.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).parent.parent
WIKI = ROOT / "wiki"
CONCEPTS = WIKI / "concepts"
MOCS = WIKI / "mocs"
INDEX = WIKI / "index.md"

# Closed vocabulary. `occasional` is active but not regular use; it needs a narrower
# check than `stopped`, because a neutral mention does not imply any frequency.
STATUSES = {"active", "occasional", "stopped"}

STOP_MARKER_RE = re.compile(
    r"\b(?:discontinu\w*|stopped|stopping|ceased|no longer)\b", re.IGNORECASE
)
OCCASIONAL_MARKER_RE = re.compile(
    r"\b(?:(?:take(?:s|n|ing)?|use(?:s|d|ing)?|dose(?:s|d|ing)?|"
    r"administer(?:s|ed|ing)?)\s+(?:only\s+)?(?:occasional(?:ly)?|"
    r"intermittent(?:ly)?|infrequent(?:ly)?|sporadic(?:ally)?|PRN|"
    r"as[- ]needed|when needed|some\s+"
    r"(?:days?|nights?|mornings?|evenings?))|"
    r"(?:occasional|intermittent|infrequent|sporadic)\s+"
    r"(?:use|dosing|dose|regimen)|PRN|as[- ]needed|when needed|some\s+"
    r"(?:days?|nights?|mornings?|evenings?)|not\s+(?:daily|nightly)|"
    r"not\s+(?:taken|used)\s+(?:daily|nightly)|"
    r"not\s+(?:every|each)\s+(?:day|night|morning|evening))\b",
    re.IGNORECASE,
)
REGULAR_FREQUENCY_RE = re.compile(
    r"\b(?:daily|nightly|regularly|routinely|"
    r"(?:every|each|most)\s+(?:day|night|morning|evening)s?)\b",
    re.IGNORECASE,
)
HISTORICAL_SCOPE_RE = re.compile(
    r"\b(?:previously|formerly|historically|used to|at the time|"
    r"during (?:that|the) period|prior to|until|"
    r"(?:on|in)\s+(?:19|20)\d{2}(?:-\d{2}-\d{2})?)\b",
    re.IGNORECASE,
)
BODY_STATUS_RE = re.compile(
    r"\*\*(?:Current status|Discontinued)\b[^*]*\*\*(?::)?\s*(.{0,80})", re.IGNORECASE
)

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
FIELD_RE = re.compile(r"^([\w-]+):\s*(.*)$", re.MULTILINE)
ENTRY_HEADING_RE = re.compile(r"^## (\S+\.md)\s*$")
BULLET_RE = re.compile(r"^\s*[-*+] ")
MOC_SUBJECT_RE = re.compile(r"^\s*[-*+]\s+\[\[([^\]|#]+)")


WIKILINK_RE = re.compile(r"\[\[[^\]]*\]\]")
ENTRY_LINE_RE = re.compile(r"^## \S+\.md\s*$", re.MULTILINE)
ASCII_RE = re.compile(r"\A[\x00-\x7f]+\Z")


def term_pattern(term: str, case_sensitive: bool) -> re.Pattern[str]:
    """Word-boundary match for ASCII terms; plain containment for CJK.

    Brand names are matched case-sensitively because a short brand can collide with
    an ordinary word -- a brand spelled `Rest` would make a case-blind word match hit
    "heart rate at rest". Generic names are distinctive enough to match
    case-insensitively.
    """
    if ASCII_RE.match(term):
        pattern = r"\b" + re.escape(term).replace(r"\ ", r"\s+") + r"\b"
    else:
        pattern = re.escape(term)
    return re.compile(pattern, 0 if case_sensitive else re.IGNORECASE)


@dataclass(frozen=True)
class Med:
    stem: str
    status: str
    names: tuple[tuple[str, re.Pattern[str]], ...]    # definite: generic/brand/local
    aliases: tuple[tuple[str, re.Pattern[str]], ...]  # class names -- review tier


@dataclass
class Finding:
    kind: str
    path: str
    line: int
    med: str
    excerpt: str


def frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    return {k: v.strip() for k, v in FIELD_RE.findall(match.group(1))}


def split_list(raw: str) -> list[str]:
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    return [item.strip().strip("\"'") for item in raw.split(",") if item.strip()]


def display(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_medications() -> tuple[list[Med], list[Finding]]:
    meds: list[Med] = []
    problems: list[Finding] = []
    for path in sorted(CONCEPTS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta = frontmatter(text)
        if "medication" not in split_list(meta.get("tags", "")):
            continue

        status = meta.get("status", "").strip().lower()
        body_status = BODY_STATUS_RE.search(text)
        if not status:
            continue  # omitted rather than guessed; nothing to check

        if status not in STATUSES:
            problems.append(Finding("STATUS MISMATCH", display(path), 1, path.stem,
                                    f"status: {status!r} is not one of {sorted(STATUSES)}"))
            continue

        # Guard the second source of truth: frontmatter vs the concept's own prose.
        if body_status:
            claim = body_status.group(0)
            body_status_value = body_claim_status(claim)
            if body_status_value != status:
                problems.append(Finding(
                    "STATUS MISMATCH", display(path),
                    text[:body_status.start()].count("\n") + 1, path.stem,
                    f"frontmatter says {status!r}, body status reads "
                    f"{body_status_value!r}: {claim.strip()[:110]}"))
        elif status == "occasional":
            problems.append(Finding(
                "STATUS MISMATCH", display(path), 1, path.stem,
                "frontmatter says 'occasional' but no explicit Current status line "
                "was found"))

        generic = {path.stem.replace("-", " "), meta.get("title", "")}
        branded = {meta[f] for f in ("brand", "local-brand-name") if meta.get(f)}
        generic = {n.strip() for n in generic if n.strip()}
        branded = {n.strip() for n in branded if n.strip()}

        names = [(n, term_pattern(n, case_sensitive=False)) for n in sorted(generic)]
        names += [(n, term_pattern(n, case_sensitive=True)) for n in sorted(branded)]
        seen = {n.lower() for n in generic | branded}
        aliases = [(a, term_pattern(a, case_sensitive=True))
                   for a in sorted(split_list(meta.get("aliases", "")))
                   if a.lower() not in seen]

        meds.append(Med(path.stem, status, tuple(names), tuple(aliases)))
    return meds, problems


def prose_only(block: str) -> str:
    """Strip what is not prose: link targets, entry headings, YAML frontmatter.

    A `[[amlodipine]]` in a Related: line or a `## amlodipine.md` heading is a
    pointer, not a statement about the patient's current regimen, and neither can
    carry a stop marker. Counting them makes every neighbouring entry a finding.
    """
    block = FRONTMATTER_RE.sub("", block)
    block = WIKILINK_RE.sub(" ", block)
    return ENTRY_LINE_RE.sub(" ", block)


def mentions(block: str, terms: tuple[tuple[str, re.Pattern[str]], ...]) -> str | None:
    for term, pattern in terms:
        if pattern.search(block):
            # "~3 weeks off amlodipine" states the stop as plainly as "discontinued".
            # Matched against the drug name rather than as a bare marker, because a
            # standalone `off` would also swallow "off-label" and suppress real gaps.
            if re.search(r"\boff\s+(?:the\s+)?" + re.escape(term), block, re.IGNORECASE):
                continue
            return term
    return None


def first_term(block: str, terms: tuple[tuple[str, re.Pattern[str]], ...]) -> str | None:
    """Return the first matching medication term without stopped-use exceptions."""
    for term, pattern in terms:
        if pattern.search(block):
            return term
    return None


def body_claim_status(claim: str) -> str:
    """Reduce an explicit concept status line to the frontmatter vocabulary."""
    if STOP_MARKER_RE.search(claim):
        return "stopped"
    if OCCASIONAL_MARKER_RE.search(claim):
        return "occasional"
    return "active"


def block_subject(block: str) -> str | None:
    """Return the article named by an index heading or a MOC bullet's first link."""
    heading = ENTRY_HEADING_RE.search(block)
    if heading:
        return Path(heading.group(1)).stem
    bullet = MOC_SUBJECT_RE.search(block)
    if bullet:
        return Path(bullet.group(1)).name
    return None


def regular_use_excerpt(
    text: str,
    required_terms: tuple[tuple[str, re.Pattern[str]], ...] = (),
) -> str | None:
    """Return a present regular-use claim, excluding occasional and past schedules."""
    for segment in re.split(r"(?<=[.!?])\s+|\n+", text):
        if not REGULAR_FREQUENCY_RE.search(segment):
            continue
        if OCCASIONAL_MARKER_RE.search(segment) or HISTORICAL_SCOPE_RE.search(segment):
            continue
        if required_terms and not first_term(segment, required_terms):
            continue
        return " ".join(segment.split())
    return None


def occasional_frequency_hit(block: str, med: Med) -> tuple[str, str] | None:
    """Return the matched identity and regular-use excerpt for one mirror block."""
    text = prose_only(block)
    is_subject = block_subject(block) == med.stem
    excerpt = regular_use_excerpt(text, () if is_subject else med.names)
    if excerpt:
        hit = first_term(excerpt, med.names)
        return hit or med.stem, excerpt
    return None


def index_blocks(text: str) -> list[tuple[int, str]]:
    """Entry blocks in wiki/index.md whose Type is `concept`."""
    blocks, start, lines = [], None, text.splitlines()
    for i, line in enumerate(lines):
        if ENTRY_HEADING_RE.match(line):
            start = i
        elif line.startswith("## ") and start is not None:
            start = None
        if start is not None and i + 1 < len(lines) and lines[i + 1].startswith("## "):
            block = "\n".join(lines[start:i + 1])
            if re.search(r"^- \*\*Type:\*\*\s*concept\b", block, re.MULTILINE):
                blocks.append((start + 1, block))
            start = None
    if start is not None:
        block = "\n".join(lines[start:])
        if re.search(r"^- \*\*Type:\*\*\s*concept\b", block, re.MULTILINE):
            blocks.append((start + 1, block))
    return blocks


def moc_blocks(text: str) -> list[tuple[int, str]]:
    """Bullets under `## Concepts` only -- `## Source Summaries` is exempt."""
    blocks, in_concepts = [], False
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            in_concepts = line.strip().lower() == "## concepts"
            continue
        if in_concepts and BULLET_RE.match(line):
            blocks.append((i, line))
    return blocks


def collect_blocks(paths: list[Path]) -> list[tuple[Path, int, str]]:
    out: list[tuple[Path, int, str]] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if path.resolve() == INDEX.resolve():
            out += [(path, n, b) for n, b in index_blocks(text)]
        elif path.resolve().parent == MOCS.resolve():
            out += [(path, n, b) for n, b in moc_blocks(text)]
        else:
            out.append((path, 1, text))
    return out


def git_changed_lines(paths: list[Path]) -> dict[Path, set[int]]:
    rel = [display(p) for p in paths]
    changed: dict[Path, set[int]] = {}
    diff = subprocess.run(["git", "diff", "--unified=0", "HEAD", "--", *rel],
                          cwd=ROOT, capture_output=True, text=True).stdout
    current: Path | None = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = (ROOT / line[6:]).resolve()
            changed.setdefault(current, set())
        elif line.startswith("@@") and current is not None:
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if m:
                start, count = int(m.group(1)), int(m.group(2) or 1)
                changed[current].update(range(start, start + count))
    return changed


def default_paths() -> list[Path]:
    return [INDEX] + sorted(MOCS.glob("*.md")) + sorted(CONCEPTS.glob("*.md"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", help="Files or directories to scan.")
    parser.add_argument("--git-diff", action="store_true",
                        help="Report only blocks intersecting lines changed vs HEAD.")
    args = parser.parse_args()

    meds, findings = load_medications()
    stopped = [m for m in meds if m.status == "stopped"]
    occasional = [m for m in meds if m.status == "occasional"]

    if args.paths:
        paths: list[Path] = []
        for raw in args.paths:
            p = Path(raw).resolve()
            paths += sorted(p.glob("*.md")) if p.is_dir() else [p]
    else:
        paths = default_paths()
    paths = [p for p in paths if p.is_file() and p.suffix == ".md"]

    changed = git_changed_lines(paths) if args.git_diff else {}

    for path, line_no, block in collect_blocks(paths):
        if args.git_diff:
            span = set(range(line_no, line_no + block.count("\n") + 1))
            if not span & changed.get(path.resolve(), set()):
                continue
        text = prose_only(block)
        if not STOP_MARKER_RE.search(block):
            for med in stopped:
                hit = mentions(text, med.names)
                kind = "MISSING STOP"
                if not hit:
                    hit = mentions(text, med.aliases)
                    kind = "CLASS MENTION"
                if hit:
                    excerpt = " ".join(text.split())
                    findings.append(Finding(kind, display(path), line_no, med.stem,
                                            f"[{hit}] {excerpt[:150]}"))

        is_mirror = (path.resolve() == INDEX.resolve()
                     or path.resolve().parent == MOCS.resolve())
        if is_mirror:
            for med in occasional:
                frequency_hit = occasional_frequency_hit(block, med)
                if frequency_hit:
                    hit, excerpt = frequency_hit
                    findings.append(Finding(
                        "FREQUENCY MISMATCH", display(path), line_no, med.stem,
                        f"[{hit}] {excerpt[:150]}"))

    if not findings:
        print(f"No medication-status gaps found "
              f"({len(stopped)} stopped and {len(occasional)} occasional "
              f"medication(s) watched).")
        return

    kinds = ("STATUS MISMATCH", "FREQUENCY MISMATCH", "MISSING STOP", "CLASS MENTION")
    for kind in kinds:
        rows = [f for f in findings if f.kind == kind]
        if not rows:
            continue
        print(kind)
        if kind == "MISSING STOP":
            print("(Mentions a stopped medication without noting the stop. Review each:")
            print(" a pharmacological property or an explicitly past-tense statement")
            print(" needs no marker.)")
        elif kind == "CLASS MENTION":
            print("(Class alias only, no direct name -- review, may be another drug.)")
        elif kind == "FREQUENCY MISMATCH":
            print("(An occasional medication is described as regular use in an index")
            print(" entry or MOC bullet. Neutral and historical mentions are exempt.)")
        print()
        for f in rows:
            print(f"{f.path}:{f.line}  {f.med}")
            print(f"  {f.excerpt}")
        print()

    counts = ", ".join(f"{len([f for f in findings if f.kind == k])} {k.lower()}"
                       for k in kinds)
    print(f"TOTAL: {len(findings)} finding(s) -- {counts}.")


if __name__ == "__main__":
    main()
