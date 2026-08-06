#!/usr/bin/env python3
"""Flag prose that describes a stopped medication without saying it stopped.

The failure this catches is an OMISSION, not a contradiction. When a medication is
discontinued, wiki/index.md and the MOC bullets rarely claim the patient is still
taking it — they simply never say the patient has stopped, and silence reads as
current. No existing check sees this: scripts/check-mirror-drift.py is satisfied once
the mirror is edited for any reason at all, and scripts/extract-status-claims.py
compares state words against state words, so an absent word cannot disagree with
anything. Pointed at mirrors that still carry the pre-stop wording,
scripts/extract-status-claims.py returns zero hits.

So this script does not compare claims. It takes the medication concept's own
frontmatter `status:` as authority, and reports every block that mentions a stopped
medication while carrying no stop marker.

Usage:
  python3 scripts/check-medication-status.py [PATH ...] [--git-diff]

Findings come in three kinds:

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
  STATUS MISMATCH frontmatter `status:` disagrees with the concept's own body status
                  line, or uses a value outside the closed vocabulary. This is the
                  cost of putting status in frontmatter — two sources of truth
                  inside one file — so it is guarded rather than assumed.

Scanned: wiki/index.md entries whose Type is `concept`, MOC bullets under
`## Concepts`, and wiki/concepts/ bodies. NOT scanned, deliberately — summary
entries and `## Source Summaries` bullets describe what a source document says on
its own date, and a prescription record legitimately records no stop; and
wiki/queries/, which are dated snapshots correct as of their date. Getting those
exemptions wrong is what turns this into a pass that gets ignored.

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

# Closed vocabulary. `occasional` behaves as active here but exists so the field can
# state the truth -- alprazolam is genuinely "active but used only occasionally", and
# a field that cannot say so gets written wrong.
STATUSES = {"active", "occasional", "stopped"}
CHECKED_STATUSES = {"stopped"}

STOP_MARKER_RE = re.compile(
    r"\b(?:discontinu\w*|stopped|stopping|ceased|no longer)\b", re.IGNORECASE
)
BODY_STATUS_RE = re.compile(
    r"\*\*(?:Current status|Discontinued)\b[^*]*\*\*(?::)?\s*(.{0,80})", re.IGNORECASE
)

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
FIELD_RE = re.compile(r"^([\w-]+):\s*(.*)$", re.MULTILINE)
ENTRY_HEADING_RE = re.compile(r"^## (\S+\.md)\s*$")
BULLET_RE = re.compile(r"^\s*[-*+] ")


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
            says_stop = bool(STOP_MARKER_RE.search(claim))
            if says_stop != (status == "stopped"):
                problems.append(Finding(
                    "STATUS MISMATCH", display(path),
                    text[:body_status.start()].count("\n") + 1, path.stem,
                    f"frontmatter says {status!r} but the body reads: {claim.strip()[:110]}"))

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
    watched = [m for m in meds if m.status in CHECKED_STATUSES]

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
        if STOP_MARKER_RE.search(block):
            continue
        text = prose_only(block)
        for med in watched:
            hit = mentions(text, med.names)
            kind = "MISSING STOP"
            if not hit:
                hit = mentions(text, med.aliases)
                kind = "CLASS MENTION"
            if hit:
                excerpt = " ".join(text.split())
                findings.append(Finding(kind, display(path), line_no, med.stem,
                                        f"[{hit}] {excerpt[:150]}"))

    if not findings:
        print(f"No medication-status gaps found "
              f"({len(watched)} stopped medication(s) watched).")
        return

    for kind in ("STATUS MISMATCH", "MISSING STOP", "CLASS MENTION"):
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
        print()
        for f in rows:
            print(f"{f.path}:{f.line}  {f.med}")
            print(f"  {f.excerpt}")
        print()

    counts = ", ".join(f"{len([f for f in findings if f.kind == k])} {k.lower()}"
                       for k in ("STATUS MISMATCH", "MISSING STOP", "CLASS MENTION"))
    print(f"TOTAL: {len(findings)} finding(s) -- {counts}.")


if __name__ == "__main__":
    main()
