#!/usr/bin/env python3
"""
Heuristic checker for Chinese that appears as primary content rather than as a
gloss on an English term.

Usage:
  python3 scripts/check-unglossed-chinese.py PATH [PATH ...]

Each PATH may be a markdown file or a directory. Directories are searched
recursively for .md files. If no path is given, the script scans the main wiki
content locations. Output is a suspect list for human or LLM review. Exit code
is always 0.

Why this exists
---------------
The vault is English-canonical: filenames, `title`, headings and `[[backlinks]]`
are English, and Chinese rides along in parentheses as a gloss. Every other
bilingual checker is keyed on that English half — check-bilingual-terms.py looks
up English terms in the glossary and asks whether a translation follows,
check-glossary-delta.py matches the `English (中文)` shape. Both are therefore
structurally blind to the opposite defect: a Chinese term left in prose with no
English at all. There is nothing English for them to key on.

That defect is rare when source documents are English and the writer is adding
Chinese. It is the *expected* failure when the source document is itself Chinese
and the writer must translate INTO English first — which is the normal case for
a `zh-CN` or `zh-TW` vault ingesting local records. A concept that drifts into
Chinese-only prose reads fine to its owner while quietly breaking the model:
`[[backlinks]]` stop resolving to English concept names, and the article cannot
merge with anything drawn from an English-language facility.

check-locale-consistency.py does not cover this either. It asks *which* Chinese
the prose uses, not whether the Chinese should have been English — Simplified
text in a zh-CN vault is consistent by its measure, defect or not.

What counts as glossed
----------------------
Anything inside parentheses. `pituitary stalk (垂體柄)`, the medication form
`amlodipine (Norvasc, 脈優)`, and the institution form
`Mingde Memorial Hospital (台北明德)` all put their Chinese inside `(...)`, so masking
balanced parentheticals removes the entire legitimate class in one step.
Nesting is common and must be handled — `transaminases (轉胺酶; AST (天冬胺酸轉
胺酶), ALT (丙胺酸轉胺酶))` defeats a flat regex — so the mask tracks depth. It
resets at each newline: a parenthetical never spans lines here, and a stray `(`
should not blank the rest of the file.

A gloss written with a comma or slash instead of parentheses IS reported. That
is deliberate; CLAUDE.md specifies the parenthesized form.

What is suppressed, and why it is data rather than a word list
--------------------------------------------------------------
Personal and institution names are legitimately Chinese in body prose — CLAUDE.md
puts physician names under "What NOT to translate", and an institution that
operates under a Chinese name is *named* in Chinese. Suppressing them from a
hardcoded list would put a roster back into `scripts/`, which is exactly what
memory/provenance-roster.md exists to prevent. So the names come from the same
two places every other consumer reads:

  - _provenance_vocab.identifying_terms() — the roster's facility and physician
    tables, matched by containment so a full form (臺北市立明德醫院) is covered
    by the roster's shorter one (明德).
  - memory/patient-name.md, when present, on the >=3 Han-character convention
    run_privacy_gate() in sync-to-public.sh already uses.

Both are optional. A fresh vault has an empty roster and no patient-name file,
and simply gets a longer suspect list until they are filled in.

Two narrow heuristics cover clinicians who are named in prose but do not belong
in the roster at all — an interpreting radiologist, a technologist, the
physician a handoff document is addressed to. Neither is ever a `physician:`
value, so neither will ever be in the roster:

  - a run ending in a personal honorific (醫師, 醫生, 大夫, 主任, 教授);
  - a run introduced by a clinician-name marker on the same line (`Dr.`,
    `Radiologist:`, `attending physician`, `interpreting cardiologist`, `For`).

Bare Chinese role labels (患者, 就診醫師) are suppressed as themselves.

Locale
------
This runs in every locale, including `none`, and does not call
skip_if_monolingual(). Under a Chinese locale an unglossed term is a defect;
under `none` any Chinese in wiki prose is a defect, since the section that
authorizes glosses is skipped entirely. The suppression list still applies in
both — a name is a name.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _provenance_vocab  # noqa: E402

ROOT = Path(__file__).parent.parent
DEFAULT_PATHS = [
    ROOT / "wiki" / "concepts",
    ROOT / "wiki" / "summaries",
    ROOT / "wiki" / "mocs",
    ROOT / "wiki" / "queries",
    ROOT / "wiki" / "deliverables",
    ROOT / "wiki" / "index.md",
    ROOT / "wiki" / "home.md",
]

PATIENT_NAME_FILE = ROOT / "memory" / "patient-name.md"

# CJK Unified Ideographs, Extension A, the compatibility block, and Extension B.
# Extension B is not optional: rare given-name characters live there (U+2304D 𣁽
# appears in a physician name in this vault), and a range that stops at U+9FFF
# splits such a name into two runs, which then miss both the roster lookup and
# the honorific test.
CJK = "㐀-鿿豈-﫿\U00020000-\U0002a6df"
CJK_RE = re.compile(f"[{CJK}]")
RUN_RE = re.compile(f"[{CJK}]+")

FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")

HONORIFICS = ("醫師", "醫生", "大夫", "主任", "教授")
ROLE_LABELS = frozenset(
    {"醫師", "醫生", "大夫", "患者", "病人", "就診醫師", "主治醫師", "技術員"}
)

# Text immediately preceding a run, when it introduces a person's name. The
# -ologist / -iatrist branch covers the specialty words these reports actually
# use (cardiologist, radiologist, technologist) without enumerating them.
NAME_CONTEXT_RE = re.compile(
    r"(?:Dr\.?|MD|PhD|Prof\.?|attending|interpreting|ordered\s+by|performed\s+by"
    r"|read\s+by|signed\s+by|referred\s+to|physician|surgeon|specialist|dentist"
    r"|[A-Za-z]+(?:ologist|iatrist)|For|with)"
    r"[\s:：,，/、·—–-]*$",
    re.IGNORECASE,
)

MIN_PATIENT_NAME_LEN = 3


def _blank_but_keep_lines(match: re.Match[str]) -> str:
    # Replace a matched region with as many blank lines as it spanned so every
    # following line keeps its original 1-based number in the file.
    return "\n" * match.group(0).count("\n")


def strip_frontmatter(text: str) -> str:
    return FRONTMATTER_RE.sub(_blank_but_keep_lines, text, count=1)


def strip_code_fences(text: str) -> str:
    return CODE_FENCE_RE.sub(_blank_but_keep_lines, text)


def blank_inline_code(text: str) -> str:
    return INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), text)


def mask_parentheticals(text: str) -> str:
    """Blank everything inside balanced (...) or （...）, depth-aware.

    Column positions are preserved so a reported run still points at the right
    place in the original line. Depth resets per line; see the module docstring.
    """
    out: list[str] = []
    for line in text.split("\n"):
        chars = list(line)
        depth = 0
        for i, ch in enumerate(line):
            if ch in "(（":
                depth += 1
                chars[i] = " "
            elif ch in ")）":
                if depth:
                    depth -= 1
                chars[i] = " "
            elif depth:
                chars[i] = " "
        out.append("".join(chars))
    return "\n".join(out)


def load_known_names() -> frozenset[str]:
    """Chinese names that are legitimately Chinese in prose.

    Roster failures are swallowed on purpose: a vault with no roster yet should
    get a noisier suspect list, not a crash, since this checker is advisory.
    """
    names: set[str] = set()
    try:
        _, cjk_terms = _provenance_vocab.identifying_terms()
        names.update(t for t in cjk_terms if t)
    except Exception:  # noqa: BLE001 - advisory checker, never a hard failure
        pass
    if PATIENT_NAME_FILE.exists():
        text = PATIENT_NAME_FILE.read_text(encoding="utf-8")
        names.update(
            run for run in RUN_RE.findall(text) if len(run) >= MIN_PATIENT_NAME_LEN
        )
    return frozenset(names)


def is_person_name(run: str, preceding: str, known: frozenset[str]) -> bool:
    if run in ROLE_LABELS:
        return True
    if any(name in run for name in known):
        return True
    for honorific in HONORIFICS:
        if run.endswith(honorific) and len(run) > len(honorific):
            return True
    return bool(NAME_CONTEXT_RE.search(preceding))


def parse_unified_zero_diff(diff_text: str) -> dict[Path, set[int]]:
    # Same shape as the copies in check-bilingual-terms.py, check-glossary-delta.py,
    # check-dangling-links.py and check-medication-first-mentions.py. Kept local
    # rather than shared so adding this checker does not touch four working ones.
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
    diff = subprocess.run(
        ["git", "diff", "--unified=0", "--", *relative_paths],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    changed = parse_unified_zero_diff(diff.stdout)

    status = subprocess.run(
        ["git", "status", "--short", "--", *relative_paths],
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


def iter_markdown_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.rglob("*.md")))
        elif path.is_file() and path.suffix == ".md":
            files.append(path)
    return files


def scan_file(path: Path, known: frozenset[str]) -> list[tuple[int, str, list[str]]]:
    original = path.read_text(encoding="utf-8").split("\n")
    text = strip_frontmatter(path.read_text(encoding="utf-8"))
    text = strip_code_fences(text)
    text = blank_inline_code(text)
    text = mask_parentheticals(text)

    findings: list[tuple[int, str, list[str]]] = []
    for line_no, line in enumerate(text.split("\n"), 1):
        if not CJK_RE.search(line):
            continue
        suspects = [
            m.group(0)
            for m in RUN_RE.finditer(line)
            if not is_person_name(m.group(0), line[: m.start()], known)
        ]
        if suspects:
            raw = original[line_no - 1].strip() if line_no <= len(original) else ""
            findings.append((line_no, raw, suspects))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report Chinese that is not a gloss on an English term."
    )
    parser.add_argument("paths", nargs="*", help="markdown files or directories")
    parser.add_argument(
        "--git-diff",
        action="store_true",
        help="Only report findings on lines in the current git diff. Untracked files are scanned in full.",
    )
    args = parser.parse_args()

    scan_paths = [Path(p).resolve() for p in args.paths] if args.paths else DEFAULT_PATHS
    files = iter_markdown_files([p for p in scan_paths if p.exists()])
    known = load_known_names()
    changed_lines_by_file = git_changed_lines(files) if args.git_diff else {}

    findings: list[tuple[str, int, str, list[str]]] = []
    for path in files:
        if args.git_diff and path not in changed_lines_by_file:
            continue
        try:
            rel = path.relative_to(ROOT)
        except ValueError:
            rel = path
        for line_no, raw, suspects in scan_file(path, known):
            if args.git_diff and line_no not in changed_lines_by_file[path]:
                continue
            findings.append((str(rel), line_no, raw, suspects))

    if not findings:
        print(
            f"No unglossed Chinese found across {len(files)} file(s)."
            if files
            else "No files to scan."
        )
        return 0

    print("SUSPECT UNGLOSSED CHINESE")
    print("(Heuristic output; review before editing.)")
    print()
    for rel, line_no, raw, suspects in findings:
        snippet = raw[:180] + ("..." if len(raw) > 180 else "")
        print(f"{rel}:{line_no}  {', '.join(dict.fromkeys(suspects))}")
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
