#!/usr/bin/env python3
"""Flag wiki articles whose prose changed while their mirror descriptions did not.

An article's one-line description is repeated in two places: its ``## {file}.md``
entry block in ``wiki/index.md`` and its ``- [[stem]] — …`` bullet in the MOC files
for its domains. Nothing in the vault forces those copies to move when the article
does, so a rewrite leaves the mirrors describing the article in wording it no longer
uses. That is what prompts/translation-backfill.md step 6 exists to prevent, and it
is the only step in that workflow with no failure signal behind it.

Usage:
  python3 scripts/check-mirror-drift.py [PATH ...] [--git-diff]
  python3 scripts/check-mirror-drift.py [PATH ...] --range REV..REV
  python3 scripts/check-mirror-drift.py --audit

Default (and ``--git-diff``, accepted as an alias so this reads like its siblings in
translation-backfill step 10) compares the working tree against HEAD. ``--range``
compares two revisions, which is how a past batch is audited after the fact.
``--audit`` sweeps the whole history: for every article it finds the most recent
commit that changed the article's body and the most recent commit that changed each
of its mirror lines, and reports the articles whose body moved more recently. That
is the mode for a periodic /lint pass.

This is a STALENESS check, not a correctness check. It compares an article against
its own past, never an article against its mirror -- no term extraction, no
similarity scoring, and it is indifferent to which language the wording is in. A
Chinese-term comparison would be near-blind here by construction, because
prompts/rewrite.md instructs a rewrite to preserve existing glosses: the 中文 is the
one part guaranteed to survive unchanged on both sides. The cost of the staleness
formulation is that ANY edit to the mirror satisfies the check. It proves the mirror
was touched, not that it was correctly synchronized.

Unlike the three glossary checkers this one never reads wiki-config.yml and never
skips itself: mirror wording drifts in every vault, so it runs under `locale: none`
exactly as it does under zh-TW. That is why prompts/rewrite.md invokes it directly
rather than through the translation-backfill hand-off, which Chinese locales alone
trigger.

Changes confined to YAML frontmatter (aliases, cn-title, updated) are ignored, so
metadata passes do not fire it. Findings name the sections that changed so a
reviewer can judge whether the mirror really needed to move. Advisory; read-only;
exit code is always 0.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).parent.parent
WIKI = ROOT / "wiki"
INDEX_REL = "wiki/index.md"
MOCS_REL = "wiki/mocs"

DEFAULT_PATHS = [WIKI / "concepts", WIKI / "summaries", WIKI / "queries"]

# Superseded answers are deliberately removed from wiki/index.md by /lint step 7.
EXCLUDED_DIRS = {"_superseded"}

WORKTREE = ":worktree:"

# Sections whose wording feeds a mirror's one-line description. An unlisted
# section is treated as description-bearing: a custom heading is more likely to
# be content than bookkeeping, and a false alarm costs a glance.
LINK_SECTIONS = {"Connections", "Backlinks", "Key Concepts", "Source Articles Consulted"}
# Sections that feed neither the description nor `Related:`.
INERT_SECTIONS = {"Sources", "Open Questions", "Follow-up Questions Worth Exploring"}

FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
ENTRY_HEADING_RE = re.compile(r"^## (\S+\.md)\s*$")
SECTION_HEADING_RE = re.compile(r"^## +(.+?)\s*$")
BULLET_RE = re.compile(r"^\s*[-*+] ")
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)")

PREAMBLE = "(title)"


# --------------------------------------------------------------------------- git


def git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return result.stdout if result.returncode == 0 else ""


class Blobs:
    """Read file contents at arbitrary revisions through one `git cat-file --batch`."""

    def __init__(self) -> None:
        self._proc = subprocess.Popen(
            ["git", "cat-file", "--batch"],
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        self._cache: dict[tuple[str, str], str | None] = {}

    def _read_exact(self, size: int) -> bytes:
        chunks: list[bytes] = []
        remaining = size
        while remaining > 0:
            chunk = self._proc.stdout.read(remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def read(self, rev: str, relpath: str) -> str | None:
        key = (rev, relpath)
        if key in self._cache:
            return self._cache[key]

        if rev == WORKTREE:
            path = ROOT / relpath
            text = path.read_text(encoding="utf-8") if path.is_file() else None
            self._cache[key] = text
            return text

        self._proc.stdin.write(f"{rev}:{relpath}\n".encode())
        self._proc.stdin.flush()
        header = self._proc.stdout.readline().decode("utf-8", "replace").strip()
        fields = header.rsplit(" ", 2)
        if len(fields) != 3 or not fields[2].isdigit():
            self._cache[key] = None
            return None
        kind, size = fields[1], int(fields[2])
        payload = self._read_exact(size)
        self._proc.stdout.read(1)  # trailing newline
        text = payload.decode("utf-8", "replace") if kind == "blob" else None
        self._cache[key] = text
        return text

    def close(self) -> None:
        self._proc.stdin.close()
        self._proc.stdout.close()
        self._proc.wait()


@dataclass(frozen=True)
class Commit:
    sha: str
    parent: str
    order: int  # 0 is the newest commit; lower means more recent
    files: frozenset[str]


def commit_records(pathspec: list[str]) -> list[Commit]:
    """Commits touching pathspec, newest first, each with the files it changed."""
    raw = git(["log", "--format=\x01%H %P %ct", "--name-only", "--", *pathspec])
    commits: list[Commit] = []
    sha = parent = ""
    files: set[str] = set()
    order = 0

    def flush() -> None:
        nonlocal sha, parent, files, order
        if sha:
            commits.append(Commit(sha, parent, order, frozenset(files)))
            order += 1
        sha, parent, files = "", "", set()

    for line in raw.splitlines():
        if line.startswith("\x01"):
            flush()
            parts = line[1:].split()
            sha = parts[0]
            parent = parts[1] if len(parts) > 2 else ""
        elif line.strip():
            files.add(line.strip())
    flush()
    return commits


# ------------------------------------------------------------------------ parsing


def body(text: str | None) -> str:
    if not text:
        return ""
    return FRONTMATTER_RE.sub("", text)


def sections(text: str | None) -> dict[str, str]:
    """Split an article body into its `## ` sections, keyed by heading."""
    result: dict[str, list[str]] = {PREAMBLE: []}
    current = PREAMBLE
    fenced = False
    for line in body(text).splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        match = None if fenced else SECTION_HEADING_RE.match(line)
        if match:
            current = match.group(1)
            result.setdefault(current, [])
        else:
            result[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in result.items()}


def changed_sections(old: str | None, new: str | None) -> list[str]:
    before, after = sections(old), sections(new)
    changed = [name for name, text in after.items() if before.get(name, "") != text]
    changed += [f"-{name}" for name in before if name not in after]
    return [name for name in changed if name != PREAMBLE or before.get(PREAMBLE, "")]


def describes(names: list[str]) -> list[str]:
    """Changed sections whose wording feeds a one-line description anywhere."""
    return [n for n in names if n.lstrip("-") not in LINK_SECTIONS | INERT_SECTIONS]


def relates(names: list[str]) -> list[str]:
    """Changed sections feeding either a description or the index `Related:` line."""
    return [n for n in names if n.lstrip("-") not in INERT_SECTIONS]


def index_entries(text: str | None) -> dict[str, str]:
    """Map `## {file}.md` entry names to their block text in wiki/index.md."""
    entries: dict[str, list[str]] = {}
    current: str | None = None
    for line in (text or "").splitlines():
        entry = ENTRY_HEADING_RE.match(line)
        if entry:
            current = entry.group(1)
            entries[current] = []
            continue
        if line.startswith("## "):  # a domain section or Compilation Summary
            current = None
            continue
        if current is not None:
            entries[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in entries.items()}


def moc_bullets(text: str | None) -> dict[str, str]:
    """Map an article stem to the MOC bullet describing it (keyed by its first link)."""
    bullets: dict[str, list[str]] = {}
    for line in (text or "").splitlines():
        if not BULLET_RE.match(line):
            continue
        link = WIKILINK_RE.search(line)
        if link:
            bullets.setdefault(link.group(1).strip(), []).append(line.strip())
    return {stem: "\n".join(lines) for stem, lines in bullets.items()}


def moc_files(blobs: Blobs, rev: str) -> list[str]:
    if rev == WORKTREE:
        moc_dir = WIKI / "mocs"
        return sorted(rel_path(p) for p in moc_dir.glob("*.md")) if moc_dir.is_dir() else []
    listing = git(["ls-tree", "--name-only", f"{rev}:{MOCS_REL}"])
    return sorted(f"{MOCS_REL}/{name}" for name in listing.split() if name.endswith(".md"))


def rel_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


# ----------------------------------------------------------------------- findings


@dataclass
class Finding:
    article: str
    changed: list[str]
    stale: list[tuple[str, str]] = field(default_factory=list)  # (mirror file, excerpt)
    missing: list[str] = field(default_factory=list)


def scoped(relpath: str, scope: list[Path]) -> bool:
    path = ROOT / relpath
    if EXCLUDED_DIRS.intersection(path.parts):
        return False
    return any(path == item or item in path.parents for item in scope)


def article_candidates(old_rev: str, new_rev: str, scope: list[Path]) -> list[str]:
    if new_rev == WORKTREE:
        names = set(git(["diff", "--name-only", "HEAD"]).split())
        for line in git(["status", "--short", "--untracked-files=all"]).splitlines():
            if line[:2].strip() == "??":
                names.add(line[3:].strip())
    else:
        names = set(git(["diff", "--name-only", f"{old_rev}..{new_rev}"]).split())
    return sorted(n for n in names if n.endswith(".md") and scoped(n, scope))


def compare_states(blobs: Blobs, old_rev: str, new_rev: str, scope: list[Path]) -> list[Finding]:
    old_index = index_entries(blobs.read(old_rev, INDEX_REL))
    new_index = index_entries(blobs.read(new_rev, INDEX_REL))
    mocs = sorted(set(moc_files(blobs, old_rev)) | set(moc_files(blobs, new_rev)))
    old_mocs = {m: moc_bullets(blobs.read(old_rev, m)) for m in mocs}
    new_mocs = {m: moc_bullets(blobs.read(new_rev, m)) for m in mocs}

    findings: list[Finding] = []
    for relpath in article_candidates(old_rev, new_rev, scope):
        new_text = blobs.read(new_rev, relpath)
        if new_text is None:
            continue  # deleted
        changed = changed_sections(blobs.read(old_rev, relpath), new_text)
        related = relates(changed)
        if not related:
            continue  # frontmatter-only, or confined to Sources/Open Questions

        described = describes(changed)
        name = Path(relpath).name
        stem = Path(relpath).stem
        finding = Finding(relpath, related)

        if name not in new_index:
            finding.missing.append(INDEX_REL)
        elif old_index.get(name) == new_index[name]:
            finding.stale.append((INDEX_REL, f"## {name}"))

        for moc in mocs if described else []:
            bullet = new_mocs[moc].get(stem)
            if bullet is not None and old_mocs[moc].get(stem) == bullet:
                finding.stale.append((moc, bullet))

        if finding.stale or finding.missing:
            findings.append(finding)
    return findings


def audit(blobs: Blobs, scope: list[Path]) -> list[Finding]:
    """Whole-history sweep: compare each article's last body change to its mirrors'."""
    commits = commit_records(["wiki"])
    if not commits:
        return []

    # Most recent commit in which each index entry / MOC bullet changed.
    entry_order: dict[str, int] = {}
    bullet_order: dict[tuple[str, str], int] = {}
    for commit in commits:
        if INDEX_REL in commit.files:
            after = index_entries(blobs.read(commit.sha, INDEX_REL))
            before = index_entries(blobs.read(commit.parent, INDEX_REL)) if commit.parent else {}
            for name, text in after.items():
                if before.get(name) != text:
                    entry_order.setdefault(name, commit.order)
        for moc in (f for f in commit.files if f.startswith(f"{MOCS_REL}/")):
            after_b = moc_bullets(blobs.read(commit.sha, moc))
            before_b = moc_bullets(blobs.read(commit.parent, moc)) if commit.parent else {}
            for stem, text in after_b.items():
                if before_b.get(stem) != text:
                    bullet_order.setdefault((moc, stem), commit.order)

    current_index = index_entries(blobs.read(WORKTREE, INDEX_REL))
    current_mocs = {m: moc_bullets(blobs.read(WORKTREE, m)) for m in moc_files(blobs, WORKTREE)}
    articles = sorted(
        rel_path(p) for item in scope for p in item.rglob("*.md") if scoped(rel_path(p), scope)
    )

    findings: list[Finding] = []
    for relpath in articles:
        name, stem = Path(relpath).name, Path(relpath).stem
        body_order = body_change_order(blobs, commits, relpath)
        if body_order is None:
            continue
        last = commits[body_order]
        changed = changed_sections(blobs.read(last.parent, relpath), blobs.read(last.sha, relpath))
        related = relates(changed)
        if not related:
            continue

        described = describes(changed)
        finding = Finding(relpath, related)

        if name not in current_index:
            finding.missing.append(INDEX_REL)
        elif body_order < entry_order.get(name, len(commits)):
            finding.stale.append((INDEX_REL, f"## {name}"))

        for moc, bullets in current_mocs.items() if described else []:
            if stem in bullets and body_order < bullet_order.get((moc, stem), len(commits)):
                finding.stale.append((moc, bullets[stem]))

        if finding.stale or finding.missing:
            findings.append(finding)
    return findings


def body_change_order(blobs: Blobs, commits: list[Commit], relpath: str) -> int | None:
    """Log position of the most recent commit that changed this article's body."""
    for commit in commits:
        if relpath not in commit.files:
            continue
        after = blobs.read(commit.sha, relpath)
        before = blobs.read(commit.parent, relpath) if commit.parent else None
        if body(after) != body(before):
            return commit.order
    return None


# --------------------------------------------------------------------------- main


def report(findings: list[Finding], mode: str) -> None:
    stale = [f for f in findings if f.stale]
    missing = [f for f in findings if f.missing]

    if not findings:
        print(f"No mirror drift found ({mode}).")
        return

    if stale:
        print("MIRROR DRIFT")
        print("(Article prose moved; its one-line description elsewhere did not.)")
        print()
        for finding in stale:
            changed = ", ".join(finding.changed) if finding.changed else "body"
            print(f"{finding.article}  changed: {changed}")
            for mirror, excerpt in finding.stale:
                print(f"  stale  {mirror}")
                print(f"         {excerpt[:150]}")
            print()

    if missing:
        print("NO INDEX ENTRY")
        print("(Article changed but has no `## {file}.md` block in wiki/index.md.)")
        print()
        for finding in missing:
            print(f"{finding.article}  ->  missing from {', '.join(finding.missing)}")
        print()

    mirrors = {mirror for finding in stale for mirror, _ in finding.stale}
    print(
        f"TOTAL: {len(stale)} article(s) with stale mirrors across {len(mirrors)} "
        f"mirror file(s); {len(missing)} with no index entry."
    )
    print("Fix by editing the named lines only -- never by rewriting a whole mirror")
    print("file. wiki/index.md's Compilation Summary is append-only and ingest-owned,")
    print("and MOC Key Relationships prose has its own 2-3 sentence contract.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", help="Article files or directories to check.")
    parser.add_argument(
        "--git-diff",
        action="store_true",
        help="Compare the working tree against HEAD (the default).",
    )
    parser.add_argument("--range", dest="rev_range", help="Compare two revisions, as REV..REV.")
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Sweep the whole history for articles whose body outran their mirrors.",
    )
    args = parser.parse_args()

    if args.rev_range and args.audit:
        parser.error("--range and --audit are mutually exclusive")

    scope = [Path(p).resolve() for p in args.paths] if args.paths else DEFAULT_PATHS
    scope = [p for p in scope if p.exists()]
    if not scope:
        print("No article paths found.")
        return
    if any(ROOT not in path.parents and path != ROOT for path in scope):
        parser.error("paths must be inside the repository")

    blobs = Blobs()
    try:
        if args.audit:
            findings = audit(blobs, scope)
            mode = "whole history"
        elif args.rev_range:
            old, _, new = args.rev_range.partition("..")
            if not old or not new:
                parser.error("--range expects REV..REV")
            findings = compare_states(blobs, old, new, scope)
            mode = args.rev_range
        else:
            findings = compare_states(blobs, "HEAD", WORKTREE, scope)
            mode = "working tree vs HEAD"
        report(findings, mode)
    finally:
        blobs.close()


if __name__ == "__main__":
    main()
