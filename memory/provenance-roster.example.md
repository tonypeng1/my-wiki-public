---
name: provenance-roster
description: this vault's closed facility and physician vocabularies, read at run time by scripts/_provenance_vocab.py
type: reference
---

# Provenance Roster

**Template.** Copy this file to `memory/provenance-roster.md` and fill in the
tables as source documents name real sites and clinicians — `scripts/new-vault.sh`
does the copy for you. Starting empty is correct: a vault with nothing ingested
has no clinics yet.

The closed vocabularies behind the `facility` and `physician` frontmatter fields
on summary files. **This file is data about one patient's care, not convention** —
the rules for choosing a value live in CLAUDE.md under "Provenance fields"; the
values live here.

**Your filled-in roster never syncs.** `scripts/` ships to the public repo and
`memory/provenance-roster.md` does not, which is what keeps a patient's real
clinics and clinicians private. Only this template ships.

## How it is read

Both tables are **executable**. `scripts/_provenance_vocab.py` parses them at run
time and both provenance checkers read them from there, so adding a row here is
the entire edit — there is no second copy in `scripts/` to keep in step, and a
value used before it is listed fails the check rather than passing silently.

The loader matches each table by its **header row** (`slug | Facility`,
`slug | Physician`), not by a heading, so the prose around them can be rewritten
freely. Keep those two header cells intact, and keep one row per site or
clinician with the slug in backticks in the first cell.

Either table may have **zero rows**, as they do here. The header must still be
present.

Both vocabularies are **closed**, like the canonical tags. Before adding a value,
check whether an existing one covers it — one slug should cover a clinic's
sub-clinics, and a hospital's imaging department is the hospital. A new value is
justified when a source document names a site or clinician not already listed.
Add the row **before** using the slug in any file.

## Facilities

`Also written` lists the forms a concept table's `Lab` cell may use for that
site. It is not decoration: `scripts/extract-provenance-claims.py` reads this
column to recognize a facility in prose, so a site missing from it makes every
row naming it read as an unknown clinic. Fill the `中文` cell only for a site
that genuinely operates under a Chinese name; use `—` otherwise, and never
invent one.

| slug | Facility | 中文 | Also written |
|---|---|---|---|

## Physicians

A physician recorded under a Chinese name gets a romanized slug and keeps the
Chinese name in the table. The slug is an identifier, not a display name — body
prose still writes the name as the source document gives it.

Record each name exactly as its source document gives it. Do not supply a
missing half from inference: a guessed set of characters is a different person's
name.

| slug | Physician |
|---|---|
