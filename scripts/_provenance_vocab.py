#!/usr/bin/env python3
"""
Load the closed provenance vocabularies out of CLAUDE.md.

`facility` and `physician` are closed vocabularies whose tables live in
CLAUDE.md ("Provenance fields" under Summary File Format). Both provenance
checkers read those tables at run time instead of keeping a copy.

That is a privacy constraint, not tidiness. `scripts/` ships to the public
repo and CLAUDE.md deliberately does not — the public copy is hand-maintained
with fictional examples — so a roster spelled out here would publish the
patient's clinics and clinicians. run_privacy_gate() in sync-to-public.sh
already derives its denylist for the identical reason: never write the real
values into a file that ships.

It also closes a drift seam. Both checkers used to say "CLAUDE.md is the
source of truth — add a value there first, then here", which is a rule someone
has to remember; now the second half is mechanical, and the public repo's
scripts read the public tables and work unmodified.

Not a CLI — importing scripts run it, and it prints nothing on its own.
"""

import re
from functools import lru_cache
from pathlib import Path

CLAUDE_MD = Path(__file__).parent.parent / "CLAUDE.md"

RESULT_STATUSES: frozenset[str] = frozenset({"normal", "mixed", "abnormal"})

# Pre-migration status tags. Not current field values, but what a regression
# would most likely reintroduce, so they stay denied as tags.
LEGACY_STATUS_TAGS: frozenset[str] = frozenset(
    {"abnormal-result", "within-range", "normal-result", "lab-result"}
)

MIN_NAME_LEN = 3

_TABLE_ROW_RE = re.compile(r"^\s*\|")
_TABLE_SEP_RE = re.compile(r"^\s*\|[\s|:-]+\|\s*$")
_SLUG_CELL_RE = re.compile(r"^`([a-z0-9][a-z0-9-]*)`$")
_HAN_RUN_RE = re.compile(r"[一-鿿]+")
_NULL_CELLS = frozenset({"", "—", "-", "–", "n/a"})
# Titles and honorifics that survive tokenizing but name nobody.
_NOT_A_NAME = frozenset({"dr", "prof", "md", "do", "vs"})


class VocabularyError(RuntimeError):
    """CLAUDE.md is missing, or a provenance table is not where it should be.

    Raised rather than falling back to an empty vocabulary: an empty one does
    not fail safe. It would make every recorded value read as UNKNOWN, and
    would empty the forbidden-tag set so the check that exists to keep
    provenance out of `tags:` would silently pass on everything.
    """


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _tables(text: str):
    """Yield (header cells, body rows) for every pipe table in the document."""
    lines = text.split("\n")
    i, n = 0, len(lines)
    while i < n:
        if not _TABLE_ROW_RE.match(lines[i]):
            i += 1
            continue
        header = _cells(lines[i])
        if i + 1 >= n or not _TABLE_SEP_RE.match(lines[i + 1]):
            i += 1
            continue
        i += 2
        rows = []
        while i < n and _TABLE_ROW_RE.match(lines[i]):
            rows.append(_cells(lines[i]))
            i += 1
        yield header, rows


@lru_cache(maxsize=None)
def _document() -> str:
    try:
        return CLAUDE_MD.read_text(encoding="utf-8")
    except OSError as exc:
        raise VocabularyError(
            f"cannot read the provenance vocabularies: {CLAUDE_MD} ({exc})"
        ) from exc


@lru_cache(maxsize=None)
def _table(kind: str) -> tuple[list[str], tuple[tuple[str, ...], ...]]:
    """The `slug | {kind}` table, matched on its header rather than its heading.

    Keying off the header cells means the section can be retitled or moved
    without breaking the loader, and a table that merely happens to sit nearby
    cannot be mistaken for it.
    """
    for header, rows in _tables(_document()):
        if (len(header) >= 2 and header[0].lower() == "slug"
                and header[1].lower() == kind):
            return header, tuple(tuple(r) for r in rows)
    raise VocabularyError(
        f"no `slug | {kind.title()}` table found in {CLAUDE_MD}. The provenance "
        f"vocabularies live under 'Provenance fields' in Summary File Format; "
        f"restore the table there rather than hardcoding values in scripts/."
    )


def _rows(kind: str) -> list[tuple[str, str]]:
    """(slug, display name) for each row whose first cell is a `slug` literal."""
    _, rows = _table(kind)
    out = []
    for row in rows:
        if not row:
            continue
        m = _SLUG_CELL_RE.match(row[0])
        if m:
            out.append((m.group(1), row[1] if len(row) > 1 else ""))
    if not out:
        raise VocabularyError(
            f"the `slug | {kind.title()}` table in {CLAUDE_MD} has no rows."
        )
    return out


def facilities() -> frozenset[str]:
    return frozenset(slug for slug, _ in _rows("facility"))


def physicians() -> frozenset[str]:
    return frozenset(slug for slug, _ in _rows("physician"))


def facility_forms() -> dict[str, list[str]]:
    """slug -> the display forms a concept table may legitimately use for it.

    Read from the table's `Also written` column. These are data, not a
    derivation. A hospital slugged after its full name is written in prose as
    an acronym, as a shortened English name, and as the Chinese name printed
    on the report — and no rule over the slug and the full name produces that
    set, which is why the column exists.
    """
    header, _ = _table("facility")
    lowered = [h.lower() for h in header]
    if "also written" not in lowered:
        raise VocabularyError(
            f"the facility table in {CLAUDE_MD} has no `Also written` column. "
            f"It carries the display forms concept tables use; without it every "
            f"Lab cell reads as an unknown facility."
        )
    col = lowered.index("also written")
    _, rows = _table("facility")
    out: dict[str, list[str]] = {}
    for row in rows:
        m = _SLUG_CELL_RE.match(row[0]) if row else None
        if not m:
            continue
        cell = row[col] if col < len(row) else ""
        forms = [f.strip() for f in cell.split(",") if f.strip().lower() not in _NULL_CELLS]
        if forms:
            out[m.group(1)] = forms
    return out


def _name_forms(display: str) -> set[str]:
    """Every name form one Physician cell offers.

    The cell holds the name as its source document prints it, and those shapes
    disagree. A Western name puts the surname last; a romanized Taiwan name
    puts it first; a Taiwan report may print characters only, or characters
    plus a parenthesized romanization. Which token is the surname is not
    decidable across that set, so every token is registered and ambiguity is
    resolved by dropping — see physician_forms().
    """
    forms = set(_HAN_RUN_RE.findall(display))
    for token in re.split(r"[^\w.-]+", _HAN_RUN_RE.sub(" ", display)):
        token = token.strip(".-")
        if len(token) < MIN_NAME_LEN or token.lower() in _NOT_A_NAME:
            continue
        forms.add(token)
    return forms


def identifying_terms() -> tuple[list[str], list[str]]:
    """(ascii, cjk) terms that name a real facility or clinician.

    Consumed by run_privacy_gate() in sync-to-public.sh, which refuses to
    publish any file containing one. This is the second half of keeping the
    rosters out of `scripts/`: reading the tables from CLAUDE.md stops them
    being written there, and this stops them being pasted back.

    That pairing is not theoretical. Both provenance checkers carried hardcoded
    rosters — including the Chinese hospital and physician names — through four
    commits, and the gate passed them every time, because the only thing it
    knew how to look for was medications.

    Single Latin name tokens are included. A bare surname is weak evidence
    alone, but the caller already skips any term that is also a common English
    word, and a name surviving that filter has no business in a published
    prompt or script.
    """
    ascii_terms: set[str] = set()
    cjk_terms: set[str] = set()

    def add(value: str) -> None:
        value = value.strip()
        if not value or value.lower() in _NULL_CELLS:
            return
        runs = _HAN_RUN_RE.findall(value)
        cjk_terms.update(runs)
        if not runs:
            ascii_terms.add(value)

    _, facility_rows = _table("facility")
    header = [h.lower() for h in _table("facility")[0]]
    forms_col = header.index("also written") if "also written" in header else None
    for row in facility_rows:
        m = _SLUG_CELL_RE.match(row[0]) if row else None
        if not m:
            continue
        ascii_terms.add(m.group(1))
        for i, cell in enumerate(row[1:], start=1):
            if i == forms_col:
                for form in cell.split(","):
                    add(form)
            else:
                add(cell)

    for slug, display in _rows("physician"):
        ascii_terms.add(slug)
        cjk_terms.update(_HAN_RUN_RE.findall(display))
        tokens = _name_forms(display)
        ascii_terms.update(t for t in tokens if not _HAN_RUN_RE.search(t))
        # The full Latin name too: distinctive even where a single token is not.
        latin = [t for t in tokens if not _HAN_RUN_RE.search(t)]
        if len(latin) > 1:
            stripped = _HAN_RUN_RE.sub(" ", display)
            stripped = re.sub(r"\b(?:Dr|Prof)\.?\s*", "", stripped)
            stripped = " ".join(stripped.replace("(", " ").replace(")", " ").split())
            if " " in stripped:
                ascii_terms.add(stripped)

    return sorted(ascii_terms), sorted(cjk_terms)


def physician_forms() -> dict[str, str]:
    """name form -> physician slug.

    A form claimed by two physicians is dropped rather than guessed: an
    ambiguous name cannot serve as a join key, and picking one would
    manufacture false matches. Same rule build_mention_map() applies to
    concept aliases in _claims_common.py.
    """
    claims: dict[str, set[str]] = {}
    for slug, display in _rows("physician"):
        for form in _name_forms(display):
            claims.setdefault(form, set()).add(slug)
    return {form: next(iter(slugs)) for form, slugs in claims.items()
            if len(slugs) == 1}
