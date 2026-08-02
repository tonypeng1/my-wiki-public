---
name: provenance-roster
description: this vault's closed facility and physician vocabularies, read at run time by scripts/_provenance_vocab.py
type: reference
---

# Provenance Roster

The closed vocabularies behind the `facility` and `physician` frontmatter
fields on summary files. **The rows below are fictional examples**, carried over
from the conventions file so this repo's checkers exercise a populated roster;
replace them with your own sites as source documents name them. **This file is data about one patient's care, not
convention** — the rules for choosing a value live in CLAUDE.md under
"Provenance fields"; the values live here.

Splitting them matters for three reasons. A vault's roster is its own: nobody
else's clinics belong in it. Editing the roster no longer dirties CLAUDE.md,
so adding a clinic stops dragging a conventions review through the
`/sync-to-public` flow. And the public repo no longer has to hand-maintain a
cast of invented hospitals just to keep its checkers running.

**This file never syncs.** `scripts/` ships to the public repo and this does
not, which is what keeps the patient's real clinics and clinicians private —
the same constraint that previously kept these tables inside CLAUDE.md. A
fresh clone gets `provenance-roster.example.md` instead and fills it in.

## How it is read

Both tables are **executable**. `scripts/_provenance_vocab.py` parses them at
run time and both provenance checkers read them from there, so adding a row
here is the entire edit — there is no second copy in `scripts/` to keep in
step, and a value used before it is listed fails the check rather than passing
silently.

The loader matches each table by its **header row** (`slug | Facility`,
`slug | Physician`), not by a heading, so the prose around them can be
rewritten freely. Keep those two header cells intact, and keep one row per
site or clinician with the slug in backticks in the first cell.

Either table may have **zero rows** — that is the correct state for a vault
that has not ingested anything yet. The header must still be present.

## Facilities

`Also written` lists the forms a concept table's `Lab` cell may use for that
site. It is not decoration: `scripts/extract-provenance-claims.py` reads this
column to recognize a facility in prose, so a site missing from it makes every
row naming it read as an unknown clinic. The `Physician` table needs no such
column — name forms are derived from the name itself.

| slug | Facility | 中文 | Also written |
|---|---|---|---|
| `riverside` | Riverside Family Medicine | — | Riverside |
| `metro-labs` | Metro Reference Laboratories | — | Metro Labs, Metro Reference |
| `lakeview` | Lakeview Regional Medical Center | — | Lakeview |
| `northgate-imaging` | Northgate Diagnostic Imaging | — | Northgate |
| `harbor-sleep` | Harbor Sleep Center | — | Harbor Sleep |
| `mingde` | Mingde Memorial Hospital, Taipei | 台北明德 | Mingde, 明德 |
| `hean` | He-An General Hospital, Taipei | 和安醫院 | He-An, 和安 |
| `xinyuan` | Xinyuan Clinic | 新苑診所 | Xinyuan, 新苑 |

## Physicians

A physician recorded under a Chinese name gets a romanized slug and keeps the
Chinese name in the table. The slug is an identifier, not a display name — body
prose still writes the name as the source document gives it.

Record each name exactly as its source document gives it. Do not supply a
missing half from inference: a guessed set of characters is a different
person's name.

| slug | Physician |
|---|---|
| `dr-alvarez` | Dr. Maria Alvarez |
| `dr-boone` | Dr. Gregory Boone |
| `dr-okafor` | Dr. Ngozi Okafor |
| `dr-whitfield` | Dr. Susan Whitfield |
| `dr-reyes` | Dr. Daniel Reyes |
| `dr-lu-wei-ting` | Dr. 呂偉庭 (Lu, Wei-Ting) |
| `dr-su-yi-fan` | Dr. 蘇怡帆 |
| `dr-ko-ming-hui` | Dr. 柯明慧 |
| `dr-yeh-cheng-han` | Dr. Yeh Cheng-Han |
