#!/usr/bin/env python3
"""
Check source filenames in raw/ against the convention in CLAUDE.md, and
reconcile raw/ against wiki/processed.log.

The convention is `{descriptive-slug}-{YYYY-MM-DD}.{ext}` — lowercase ASCII,
hyphen-separated, with the document's own printed clinical date, or no date at
all when the document itself prints none.

Two rules shape what this reports:

* A NON-CONFORMING name is only actionable while the file is unprocessed.
  Once a name is in wiki/processed.log it is frozen: the log key and the
  summary basename are both bound to it, so renaming it would orphan the log
  entry and re-ingest the document as new. Legacy stems — capitalized,
  underscored, or predating the convention — are therefore counted, not
  listed: a checker that reported the same permanently unfixable findings on
  every /lint run would train the reader to skip its output.

* raw/ and wiki/processed.log are two halves of one ledger, and /ingest keeps
  them in step by renaming a file BEFORE it logs the new name. A file in one
  and not the other means that pairing broke, which is worth more attention
  than any naming nit.

Usage:
  python3 scripts/check-raw-filenames.py [PATH ...]

With no PATH it checks every file in raw/. Read-only; exit code is always 0.
"""

from __future__ import annotations

import argparse
import datetime
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
RAW = ROOT / "raw"
PROCESSED_LOG = ROOT / "wiki" / "processed.log"

# Documentation about raw/, not a source document.
IGNORED_NAMES = {"README.md"}

# {descriptive-slug}[-YYYY-MM-DD].{ext}, lowercase ASCII throughout.
CONFORMING_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.[a-z0-9]+$")
TRAILING_DATE_RE = re.compile(r"-(\d{4})-(\d{2})-(\d{2})$")
# A date the stem is clearly TRYING to carry but did not spell as -YYYY-MM-DD:
# a bare year, an 8-digit run, or a slash/dot-separated date.
DATE_ATTEMPT_RE = re.compile(r"\d{8}|\d{4}[./]\d{1,2}|\d{1,2}[./]\d{1,2}[./]\d{2,4}|(?<!\d)(19|20)\d{2}(?!\d)")
# `name.txt  (was: original-name.txt)` — the optional rename note /ingest writes.
WAS_RE = re.compile(r"\(was:\s*(.+?)\)\s*$")


def read_log() -> "tuple[dict[str, str | None], list[str]]":
    """-> ({current name: original name or None}, [malformed lines])."""
    entries: dict[str, str | None] = {}
    malformed: list[str] = []
    if not PROCESSED_LOG.exists():
        return entries, malformed
    for line in PROCESSED_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        was_match = WAS_RE.search(line)
        original = was_match.group(1).strip() if was_match else None
        name = (line[: was_match.start()] if was_match else line).strip()
        if not name or " " in name:
            malformed.append(line)
            continue
        entries[name] = original
    return entries, malformed


def date_problem(stem: str) -> "str | None":
    """Describe what is wrong with the stem's date, or None if nothing is."""
    match = TRAILING_DATE_RE.search(stem)
    if not match:
        if DATE_ATTEMPT_RE.search(stem):
            return "carries a date that is not a trailing -YYYY-MM-DD"
        return None  # Legitimately undated — the document printed no date.
    year, month, day = (int(part) for part in match.groups())
    try:
        parsed = datetime.date(year, month, day)
    except ValueError:
        return f"{year:04d}-{month:02d}-{day:02d} is not a real calendar date"
    if parsed > datetime.date.today():
        return f"{parsed.isoformat()} is in the future"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check raw/ filenames against the convention and against wiki/processed.log."
    )
    parser.add_argument("paths", nargs="*", help="Files in raw/ to check (default: all of raw/).")
    args = parser.parse_args()

    if args.paths:
        source_files = [Path(p).resolve() for p in args.paths]
    elif RAW.is_dir():
        source_files = sorted(p for p in RAW.iterdir() if p.is_file())
    else:
        print(f"No raw/ directory at {RAW}.")
        return

    source_files = [p for p in source_files if p.name not in IGNORED_NAMES and not p.name.startswith(".")]
    if not source_files:
        print("No source files found in raw/.")
        return

    logged, malformed_log_lines = read_log()
    originals = {was: name for name, was in logged.items() if was}

    non_conforming: list[tuple[str, str, str]] = []  # unprocessed — actionable
    frozen_non_conforming: list[str] = []            # already ingested — do not rename
    pending: list[str] = []
    readded: list[tuple[str, str]] = []

    for path in source_files:
        name = path.name
        try:
            display = path.relative_to(ROOT).as_posix()
        except ValueError:
            display = path.as_posix()
        is_logged = name in logged
        problems: list[str] = []
        if not CONFORMING_RE.match(name):
            problems.append("not lowercase-hyphenated {slug}[-YYYY-MM-DD].{ext}")
        date_issue = date_problem(path.stem)
        if date_issue:
            problems.append(date_issue)

        if problems:
            (frozen_non_conforming.append(name) if is_logged
             else non_conforming.append((display, name, "; ".join(problems))))
        if not is_logged:
            pending.append(name)
            if name in originals:
                readded.append((name, originals[name]))

    on_disk = {p.name for p in source_files}
    orphans = sorted(name for name in logged if name not in on_disk) if not args.paths else []

    findings = 0

    if non_conforming:
        findings += len(non_conforming)
        print("NON-CONFORMING FILENAMES (not yet ingested — /ingest will rename these)")
        print("(See 'Source filenames in raw/' in CLAUDE.md.)")
        print()
        for display, _name, reason in non_conforming:
            print(display)
            print(f"  {reason}")
        print()

    if readded:
        findings += len(readded)
        print("POSSIBLE RE-ADDED DUPLICATE")
        print("(This filename is recorded in processed.log as a name a file arrived under")
        print("and was renamed away from. The document may already be in the wiki.)")
        print()
        for name, current in readded:
            print(f"raw/{name}  →  already ingested as {current}")
        print()

    if orphans:
        findings += len(orphans)
        print("ORPHANED LOG ENTRIES (in processed.log, no such file in raw/)")
        print("(A file renamed after it was logged, or a source document deleted. The")
        print("summary and the log key still point at the old name.)")
        print()
        for name in orphans:
            print(f"  {name}")
        print()

    if malformed_log_lines:
        findings += len(malformed_log_lines)
        print("MALFORMED processed.log LINES")
        print("(Expected `filename.ext` or `filename.ext  (was: original.ext)`.)")
        print()
        for line in malformed_log_lines:
            print(f"  {line}")
        print()

    if pending:
        print(f"PENDING INGEST: {len(pending)} file(s) in raw/ absent from processed.log")
        for name in pending:
            print(f"  {name}")
        print()

    if frozen_non_conforming:
        print(
            f"Legacy: {len(frozen_non_conforming)} already-ingested file(s) do not match "
            "the convention. Frozen by design — renaming them would orphan their "
            "processed.log entry and summary."
        )
        print()

    # Trailing total — see the note in check-bilingual-terms.py. Keep it last.
    if findings:
        print(f"TOTAL: {findings} finding(s) across {len(source_files)} source file(s).")
    else:
        print(f"No raw/ filename findings across {len(source_files)} source file(s).")


if __name__ == "__main__":
    main()
