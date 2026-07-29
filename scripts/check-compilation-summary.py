#!/usr/bin/env python3
"""
Structural checker for the `## Compilation Summary` block in wiki/index.md.

Usage:
  python3 scripts/check-compilation-summary.py [--index PATH]

The Compilation Summary is owned by the ingest workflow (prompts/p1-ingest.md
step 7b): one dated paragraph per ingest, appended at the end, never rewritten.
This checker cross-references that block against the actual ingest history
recorded in git and reports four kinds of drift:

  MISSING   an ingest (a commit that added files to wiki/processed.log) with no
            paragraph anywhere near its date
  ORDER     paragraphs that are not in ascending date order, which breaks the
            "append at the end of the section" rule on the next ingest
  FOREIGN   paragraphs that read as session Q&A rather than ingest records; no
            other workflow may write here
  UNDATED   paragraphs with no bold-date header

Commit dates are a lower bound on ingest runs: one commit can bundle several
runs, and a run is often committed the following day. So a date with *fewer*
paragraphs than commits is reported as INFO, not a finding — only a date with
no coverage at all (within a +/- 2 day window) is treated as MISSING.

Output is a suspect list for human or LLM review. Exit code is always 0.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
DEFAULT_INDEX = ROOT / "wiki" / "index.md"
PROCESSED_LOG = "wiki/processed.log"

HEADING = "## Compilation Summary"
DATE_HEADER_RE = re.compile(r"^\*\*(\d{4}-\d{2}-\d{2})([^:]*):")
SESSION_RE = re.compile(r"Session Q&A|session close", re.IGNORECASE)
NEAR_DAYS = 2


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout


def ingest_commits() -> "list[tuple[str, str, str]]":
    """Commits that ADDED lines to processed.log -> (date, short sha, subject)."""
    out = git("log", "--format=%H\x1f%ad\x1f%s", "--date=short", "--", PROCESSED_LOG)
    commits = []
    for line in out.splitlines():
        if not line.strip():
            continue
        sha, day, subject = line.split("\x1f", 2)
        numstat = git("show", "--numstat", "--format=", sha, "--", PROCESSED_LOG)
        added = 0
        for row in numstat.splitlines():
            parts = row.split("\t")
            if parts and parts[0].isdigit():
                added += int(parts[0])
        if added:
            commits.append((day, sha[:7], subject))
    return sorted(commits)


def read_section(index_path: Path) -> "list[str]":
    text = index_path.read_text(encoding="utf-8")
    if HEADING not in text:
        return []
    start = text.index(HEADING)
    nxt = text.find("\n## ", start + len(HEADING))
    section = text[start + len(HEADING) : nxt if nxt != -1 else len(text)]
    paras = [p.strip() for p in re.split(r"\n\s*\n", section) if p.strip()]
    return [p for p in paras if p != "---"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    args = parser.parse_args()

    paras = read_section(args.index)
    if not paras:
        print("No Compilation Summary section found.")
        return

    dated: "list[tuple[date, str]]" = []
    undated: "list[str]" = []
    foreign: "list[str]" = []
    by_date: "dict[str, int]" = defaultdict(int)

    for para in paras:
        m = DATE_HEADER_RE.match(para)
        if not m:
            undated.append(para)
            continue
        day = m.group(1)
        by_date[day] += 1
        dated.append((date.fromisoformat(day), para))
        if SESSION_RE.search(para):
            foreign.append(para)

    order_breaks = [
        (dated[i - 1][1], dated[i][1])
        for i in range(1, len(dated))
        if dated[i][0] < dated[i - 1][0]
    ]

    commits = ingest_commits()
    commits_by_date: "dict[str, list[tuple[str, str]]]" = defaultdict(list)
    for day, sha, subject in commits:
        commits_by_date[day].append((sha, subject))

    missing, info = [], []
    for day, entries in sorted(commits_by_date.items()):
        covered = sum(
            by_date.get((date.fromisoformat(day) + timedelta(days=d)).isoformat(), 0)
            for d in range(-NEAR_DAYS, NEAR_DAYS + 1)
        )
        if covered == 0:
            missing.extend((day, sha, subject) for sha, subject in entries)
        elif by_date.get(day, 0) < len(entries):
            info.append((day, len(entries), by_date.get(day, 0)))

    findings = bool(missing or order_breaks or foreign or undated)
    if not findings:
        print(
            f"Compilation Summary looks consistent: {len(dated)} dated paragraphs, "
            f"ascending, covering {len(commits)} ingest commits."
        )
    else:
        print("SUSPECT COMPILATION SUMMARY DRIFT")
        print("(Heuristic output; review before editing.)")
        print()

    for day, sha, subject in missing:
        print(f"MISSING  {day}  {sha}  no paragraph for: {subject[:70]}")
    for prev, cur in order_breaks:
        print(f"ORDER    {cur[:60]}  sorts before  {prev[:60]}")
    for para in foreign:
        print(f"FOREIGN  {para[:80]}")
    for para in undated:
        print(f"UNDATED  {para[:80]}")

    if info:
        print()
        print("INFO (not findings — one commit can bundle several ingest runs):")
        for day, ncommits, nparas in info:
            print(f"  {day}: {ncommits} ingest commits, {nparas} paragraphs")


if __name__ == "__main__":
    main()
