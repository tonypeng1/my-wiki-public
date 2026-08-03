<!--
Hand-maintained public copy of the private repo's CLAUDE.md. Conventions are
identical; every patient-specific example is a fictional substitute for the
private original — medications, conditions, and the facility and physician
rosters in "Provenance fields" alike. The fictional rosters keep each role of
the real ones (ordering clinic, reference lab, hospital, imaging centre, sleep
lab, and Taiwan sites with Chinese names) so the rules still have something to
bite on.

Those two tables are not illustration only: scripts/_provenance_vocab.py parses
them at run time, so THIS file is what the provenance checkers validate against
in this repo. Keep the `slug | Facility` and `slug | Physician` header rows and
the backticked slug in each first cell, or those checks stop working here.

Maintainers: when scripts/sync-to-public.sh reports that the private CLAUDE.md
changed, port the convention hunks here by hand, keep every example generic,
then rerun with --claude-md-reviewed.
-->

# Wiki Conventions

## Response Style
- Be concise.
- Answer first, explain only if requested.
- Do not narrate your reasoning or actions.
- Provide only enough detail to complete the task.

## Memory
All persistent memory lives in `memory/` at the project root. At the start of every conversation,
read `memory/MEMORY.md` to load the index, then read individual files as needed.
When saving a new memory or updating an existing one, write to `memory/` — not to `~/.claude/projects/`.

## Directory Structure
- raw/              → source documents (never modify these)
- wiki/summaries/   → one .md per source document
- wiki/concepts/    → one .md per concept/topic
- wiki/home.md         → vault entry point; links to all MOCs
- wiki/mocs/           → one moc-{domain}.md per clinical domain; navigation layer for Obsidian
- wiki/queries/     → saved Q&A outputs
  - _superseded/    → answers replaced by a newer, more complete query
- wiki/deliverables/ → outbound artifacts to hand to / present to someone: prose
                       handoff docs and Marp slide decks (+ their rendered PDFs).
                       Format is a per-file attribute, not a sub-folder: a file with
                       `marp: true` frontmatter is a slide deck; otherwise it is a
                       prose handoff. Handoff docs are date-prefixed (YYYY-MM-DD-{slug});
                       decks are {topic}-{YYYY-MM-DD}.
- wiki/maintenance/ → health check reports
- wiki/sessions/    → transient session scratch pad (NOT wiki content; do not index)
  - current.md      → active session conversation (deleted when session closes)
  - log.md          → compact session history, one entry per turn; read at the start
                      of each turn to restore context (deleted when session closes)
  - archive/        → closed sessions saved as YYYY-MM-DD-{topic-slug}-session.md
                      (+ -session-log.md) for reference. The `-session` suffix is
                      required: the query file for the same session is built from the
                      same topic string and the same date, so without it the two
                      basenames collide — and Obsidian resolves [[name]] by basename
                      across the whole vault, which makes every link to that name
                      ambiguous.
- wiki/index.md     → master index of all wiki content
- wiki/processed.log → list of already-processed raw/ files, one per line; a
                       renamed file also carries `(was: {arriving name})`

## Backlink Format
Always use Obsidian-style backlinks: [[article name]]
Article name should match the filename without the .md extension.

## General Rules
1. Never modify the contents of anything in raw/ (renaming an unprocessed file
   to the convention below is the one permitted change)
2. Always check wiki/processed.log before processing raw/ files
3. Always update wiki/index.md after creating or modifying any wiki file
4. Always add backlinks using [[name]] syntax
5. Dates should be in YYYY-MM-DD format
6. Filenames should be lowercase-hyphenated, e.g. surface-code-basics.md
   (exception: query files under wiki/queries/ are prefixed with their date,
   e.g. 2026-05-21-slug.md — see the Query File Format section)

### Source filenames in `raw/`

Source documents are named `{descriptive-slug}-{YYYY-MM-DD}.{ext}` —
`carotid-ultrasound-2020-03-14.txt`, `lab-lipid-panel-2020-06-02.txt`.
Lowercase ASCII, hyphen-separated, with no spaces, underscores, or punctuation
such as `&`. The extension is whatever the document is (`.txt`, `.png`,
`.jpg`); the convention governs the stem.

The **slug** names what the document *is* — the study, panel, or visit type —
never what it found: `lab-cbc-with-differential`, not `lab-low-hemoglobin`.
Prefixes are descriptive rather than structural: a `lab-` prefix carries
nothing the rest of the slug does not, and no script reads it. Make the slug
long enough to tell the document apart from its siblings and no longer.

The **date** is the document's own clinical date — specimen collection, study,
or visit — as printed in the document. It is not the day the file was added to
the vault, and not a date lifted from elsewhere in the body. A document that
prints no date of its own **stays undated** (`{slug}.txt`); a hand-written
medication list is the usual case. Manufacturing a date instead is the failure
described under Provenance fields below — one lifted from a prescription date
in the body propagates to every file that cites it.

Two documents of the same type on the same date are told apart by a qualifier
taken from the documents themselves — the performing lab, the body site, the
printed panel name — and only as a last resort by a trailing `-2`. Reach for
that only once the two are confirmed to be different documents: a derived name
that collides with a name already in `raw/` or `wiki/processed.log` usually
means the same export was added twice, and a `-2` would turn one document into
two summaries.

When a file is renamed, `wiki/processed.log` records the name it arrived under
on the same line —
`carotid-ultrasound-2020-03-14.txt  (was: Results_20200314_1152.pdf)`. That
note is the vault's only durable record of the original name: `/ingest` does
not commit, so the arriving name is usually never in git at all and
`git log --follow` cannot recover it. Keeping the note in the log rather than
in the summary puts it in the file that already answers "has this document been
ingested", so one lookup answers both. Consumers read the first
whitespace-delimited field as the filename and ignore the rest of the line;
`scripts/check-raw-filenames.py` reads the note to recognize a re-added export.

The stem matters downstream because it seeds the summary basename
(`wiki/summaries/{name}.md`) and *is* the key recorded in `wiki/processed.log`.
So **never rename a file already listed in `wiki/processed.log`**: both the log
key and the summary basename are bound to the old name, and a rename orphans
the entry and re-ingests the document as new. Files ingested before this
convention keep their names — a vault that predates it may carry capitalized or
underscored legacy stems, and renaming them now would cost more than it fixes.

Renaming an **unprocessed** file is not a breach of General Rule 1, which
protects the contents; those stay untouched. Nor does it make the filename
evidence. Provenance is still read from the document body alone: `/lint` and
the backfill procedure both refuse to infer a `facility`, `physician`, or date
from a filename, and a name the vault generated itself is exactly why.

### Markdown source layout

In authored wiki content, keep each prose paragraph and each list item on one
physical source line. Let Obsidian or the reader soft-wrap it for the available
window width; do not insert manual line breaks at 80 characters or any other
column target. Separate paragraphs with a blank line. This prevents a later
translation pass from lengthening selected lines and leaving a paragraph with
visibly irregular hard wraps.

YAML frontmatter, Markdown tables, fenced code blocks, blockquotes, and nested
list structure are exempt. The rule applies to the prose inside concepts,
summaries, MOCs, queries, `wiki/index.md`, and `wiki/home.md`, including prose
rewritten after Chinese glosses are inserted.

## Chinese Medical Terms

Make medical prose easier to read by adding Chinese translations for medical
terms, so a reader who is not a native English speaker can follow their own
clinical record.

**This whole section applies only when `locale` in `wiki-config.yml` is a Chinese
locale.** The locale decides which Chinese, and whether there is any at all:

| `locale` | Effect |
|---|---|
| `zh-TW` | Gloss in Traditional Chinese, Taiwan clinical wording. |
| `zh-CN` | Gloss in Simplified Chinese, Mainland clinical wording. |
| `none` | English-only vault. **Skip this section entirely** — write no glosses, and treat `cn-title` and Chinese `aliases` as not applicable. |

Under `none` nothing else changes: ingest, concepts, canonical value tables,
provenance, contradiction and coverage checks, and deliverables are all
language-independent, and the three glossary checkers skip themselves rather
than flagging every article (see `scripts/_vault_config.py`).

The examples throughout this section are written in Traditional Chinese. In a
`zh-CN` vault read them as illustrating the *rule*, not the wording — the
configured glossary supplies the wording.

**This section is the single source of truth for translation practice.** The
ingest, backfill, query, and slide workflows all follow it — they must not restate
their own translation rules, only point here.

### What to translate
- Translate **all** clinical vocabulary. Do not restrict to "important" terms and
  do not skip routine ones: anatomy, analytes and lab values, enzymes,
  electrolytes, findings and pathology, procedures, imaging modalities,
  physiological parameters, ratio names, and drug classes.
- "Clinical vocabulary" means terms that carry medical meaning — not ordinary
  English words that merely appear in medical prose (e.g. "history", "elevated",
  "risk" are not translated).
- Default to translating rather than skipping. When finishing an article, cover
  every paragraph, bullet, table cell, impression line, and open-question line —
  do not stop after the first term in a paragraph.

### First mention and repeats
- The counting unit is the **innermost heading section**: each `##` section, or
  each `###` section when the file uses them.
- Translate a term on its **first appearance in a section**. If the **same term
  appears again within that same section**, translate it a **second** time. The
  maximum is **two translations per term per section**; third and later
  appearances in that section use the plain English term or abbreviation.
- The count **resets at each new section** — the same term gets a fresh allowance
  of up to two translations in the next `##`/`###` section. Apply this to **all**
  clinical terms.
- Only inline `English (中文)` translations count toward the two. Obsidian
  `[[backlinks]]` are English and do not count; medication mentions follow the
  Medication naming rule below, not this counter.
- Default rule for concepts, summaries, MOCs, deliverables, and archived sessions
  under `wiki/sessions/archive/`, and for `wiki/index.md`. Query files keep the
  more aggressive exception below.
- `wiki/index.md` counting units: in the `## Compilation Summary` section the
  counting unit is the **paragraph** (the two-per-term allowance resets at each
  new paragraph), because that section packs many long update paragraphs under a
  single `##` heading. In the per-entry blocks, each `## {filename}.md` entry is
  its own section and its `Summary:` line follows the normal per-section count.
- Query-file exception (`wiki/queries/` only): queries are read as standalone
  answers and are often skimmed non-linearly, so repeat translations more
  aggressively for readability.
- In query files, translate clinical terms on the **first mention in each major
  section**, and translate them again in **tables, Key Points, and follow-up
  bullets** even if they already appeared earlier in the file.
- In query files, for **selected recurring clinical terms** — especially common
  abbreviations and skim-critical terms such as `A1C`, `OSA`, `CPAP`, `IFG`,
  `eGFR`, and `OGTT` — repeat the translation on the **first mention in each
  `###` subsection** as well. If there is no `###` heading in the relevant area,
  fall back to the enclosing `##` section.
- In query-file continuous prose, translate the **first mention per paragraph**;
  do not force Chinese onto every repeated use within the same paragraph when
  that would make the sentence heavy.
- In query files, keep abbreviations especially visible in skim-heavy recap
  sections, for example `AHI (呼吸中止低通氣指數)`, `PSG (多項睡眠生理檢查)`,
  `RLS (不寧腿症候群)`.
- Format: English term, then the Chinese in parentheses:
  `Carotid intima-media thickness (IMT) (頸動脈內膜中層厚度)`.

### Medication naming
- This is a **repo-wide** rule for medication mentions in body content.
- On the **first mention of a medication in each `###` section**, write it as
  `generic (Brand, local name)`.
- If a file has no `###` headings in the relevant area, fall back to the first
  mention within the enclosing `##` section.
- Apply the same format on the **first mention inside tables, Key Points,
  follow-up bullets, and other skim-heavy recap blocks**, even if the medication
  already appeared earlier in the file.
- Later mentions within the same `###` section can use the generic name alone
  unless repeating the brand/local name materially improves clarity.
- Keep `#` titles, frontmatter titles, filenames, and Obsidian backlinks in
  English only; do not add brand/local-name parentheticals there.
- The Brand and local name come from the `brand` and `local-brand-name` fields in
  that medication's concept frontmatter (see Concept Article Format) — use them
  verbatim so the same medication reads identically everywhere.
- Examples (a vault whose `region` is Taiwan): `amlodipine (Norvasc, 脈優)`,
  `atorvastatin (Lipitor, 立普妥)`, `alprazolam (Xanax, 贊安諾)`.
- Under `locale: none` there is no local-market Chinese name to carry, so the
  format drops to `generic (Brand)` — `amlodipine (Norvasc)` — and
  `local-brand-name` is not required on the concept.

### Abbreviations
- A term and its abbreviation are the **same term**. Whether an article uses only
  the abbreviation (e.g. `AST`), only the full name, or both, the first mention
  gets a Chinese translation.
- Keep the abbreviation in English and put the Chinese after the full term:
  `aspartate aminotransferase (AST) (天門冬胺酸轉胺酶)`. If only the abbreviation
  appears, attach the Chinese to it: `AST (天門冬胺酸轉胺酶)`.

### What NOT to translate
Leave in English:
- filenames, article titles, and Obsidian backlinks
- physician names
- the **values** of the `facility` and `physician` frontmatter fields — they are
  machine-matched slugs, not prose (see Provenance fields under Summary File
  Format)
- units, and **opaque lab/order identifiers that carry no medical meaning of
  their own** — numeric or catalog codes, LOINC codes, accession numbers, MRN,
  panel item numbers.

**Institution names** are an exception rather than a blanket "leave in English".
A facility that operates under a Chinese name is *named* in Chinese, so writing
it English-only is a mistranslation, not a neutral choice. In body prose give
such a facility on first mention per section as `English (中文)` —
`Mingde Memorial Hospital (台北明德)`, `He-An General Hospital (和安醫院)`,
`Xinyuan Clinic (新苑診所)` — taking both halves verbatim from the facility
vocabulary table so the same site reads identically everywhere. A facility with
no Chinese name stays English-only (`Riverside Family Medicine`); do not invent a
Chinese rendering for one.

This turns on the **facility**, not on the vault's locale: whether a site has a
Chinese name is a fact about the site. Do not restate a Taiwan hospital's name in
Simplified characters in a `zh-CN` vault, or a Mainland hospital's in Traditional
in a `zh-TW` one — the printed name is the name. Under `locale: none` this
exception does not apply at all, and every facility stays English-only.

Two clarifications:
- Medication brand names are still not translated as ordinary clinical terms,
  but in body prose they are intentionally included in the medication format
  `generic (Brand, local name)` per the Medication naming rule above.
- Exception: translate anyway when the source document itself supplies the
  Chinese wording.
- An abbreviation that *denotes a medical concept* (AST, GGT, eGFR) IS translated
  per the Abbreviations rule above. Only identifiers with no standalone medical
  meaning are excluded — that is what "opaque identifier" means here.

### Frontmatter aliases and `cn-title`
Two frontmatter layers make the vault navigable in Chinese **without renaming any
file** — filenames, `title`, and `[[backlinks]]` stay English-canonical per "What
NOT to translate" above.

**`aliases`** — add useful Chinese terms, in the vault's locale, when they help searchability,
so the note is reachable by its Chinese name in Obsidian's Quick Switcher and
global search. Every concept and MOC should carry at least one Chinese alias.

**`cn-title`** — a display field in `English (中文)` form, read by the Front Matter
Title Obsidian plugin to label the file tree, tabs, and graph. Required on every
**concept** and **MOC** file (summaries and queries do not use it) in a Chinese
locale; under `locale: none` the field carries nothing and is omitted. Rules:
- The English part is the concept's **common abbreviation** when it has one
  (`GGT (γ-谷氨醯轉移酶)`, `COPD (慢性阻塞性肺病)`, `PSA (攝護腺特異抗原)`),
  otherwise the plain name (`Gout (痛風)`, `Peptic Ulcer (消化性潰瘍)`).
- MOCs keep their full title: `MOC — Cardiology (心臟科)`.
- Medications answer **"what kind of drug is this?"**, never the brand — the brand
  is already in `brand`/`local-brand-name` and in `aliases`. In order of
  preference:
  1. the **Chinese generic name**, when one is in common use in the vault's
     locale:
     `Aspirin (阿斯匹靈)`;
  2. otherwise the **Chinese drug class**: `Atorvastatin (史他汀類藥物)`,
     `Alprazolam (苯二氮平類)`, `Atenolol (β阻斷劑)`. Prefer the short form of a
     class name over the precise one (`β阻斷劑`, not `心臟選擇性β阻斷劑`) — this is
     a sidebar label, and the article body carries the precise wording;
  3. **except** when the drug is taken for something its class name does not
     suggest, where the label states the **purpose** instead:
     `Amitriptyline (神經痛用藥)` — a TCA, but prescribed for post-herpetic
     neuralgia at sub-antidepressant doses — and `Mirtazapine (助眠劑)`, an
     antidepressant prescribed for sleep. A label that reads "antidepressant" for
     a nerve-pain or sleep medication is worse than no label.
- Because the brand is not in `cn-title`, the Chinese brand name **must** be in
  `aliases` so the file is still findable by what is printed on the box.
- Adding or fixing `aliases`/`cn-title` is search/display metadata, **not** a
  medical-content change — it does not bump `updated`.

In a Chinese locale, new concept and MOC files created during ingest or by a
maintenance pass must get both, or they show English-only in the sidebar.

Obsidian rewrites the frontmatter of any note it has open into block-style YAML and
can clobber CLI edits with its cached copy. The repo convention is inline flow style
(`aliases: [x, y]`); when bulk-editing frontmatter, keep the affected notes closed in
Obsidian or commit promptly so a clobber is recoverable.

### The shared glossary
Use the glossary named by `glossary:` in `wiki-config.yml` as the shared glossary
during ingest, article updates, query answers, and slide creation. Never hardcode
a glossary path: `zh-TW` and `zh-CN` vaults point at different files, and under
`locale: none` there is no glossary at all.

Reuse existing entries and prefer the clinical wording of the vault's locale —
Taiwan wording under `zh-TW`, Mainland wording under `zh-CN`. The two differ in
vocabulary, not just characters (`三酸甘油脂` vs `甘油三酯`, `中風` vs `脑卒中`,
`嗜中性球` vs `中性粒细胞`), so converting characters is not translating. If
unsure of the correct wording for the locale, add the term to that glossary's
Review Queue instead of guessing.

**What belongs in the glossary** — standalone, reusable clinical vocabulary you
would expect in more than one article (analyte and lab names, anatomy, pathology
and findings, procedures, physiological parameters, enzyme and abbreviation full
forms, ratio names). When you translate a term in a paragraph:
- **Add it** to the glossary when it is such a standalone, reusable term.
- **Keep it inline-only** (do not add) when it is a one-off phrase tied to a single
  sentence, report, or patient context you would not expect to look up again.
- **If unsure of the wording**, add it for later review (as above).

## Concept Article Format
Each wiki/concepts/{name}.md:

---
title: {Concept Name}
tags: [tag1, tag2]
aliases: [3–5 abbreviations, alternate spellings, lay terms, + the Chinese name]
cn-title: {English} ({中文})
updated: {date}
---

# {Concept Name}

## Overview
2-4 sentence plain explanation.

## Key Details
Main substance of the article.

**Patient test-data values MUST live in a Markdown table, never a bulleted list
— even a single value goes in a one-row table.** Give each measurement one row
(date, lab, value, flag, source backlink); that table is the concept's
*canonical record*. This holds whether the concept has fourteen draws or one:
the contradiction check (`scripts/extract-claims.py`) recognizes a concept's own
table rows as the authority and compares prose restatements elsewhere against
them — a value written as a bullet does **not** anchor (it is skipped as
authority and its row gets misattributed as a restatement of a neighboring
concept), and a one-row table also appends cleanly when the test is repeated.
Follow the `[[hemoglobin-a1c]]` / `[[lipid-panel]]` table shape.

The rule covers **every lab/imaging result value reported for the patient**. A
unit is **not** a prerequisite: dimensionless results — ratios, indices, scores
— are canonical values too, and a ratio quoted from a report belongs in a
one-row table exactly like a value in mg/dL. What makes a number canonical is
that the source document reports it, not that it carries a unit.

It does *not* pull in reference ranges or interpretation thresholds (general
knowledge), medication doses, qualitative findings with no number, or dated
*events* (a medication's prescribe/discontinue dates, a diagnosis timeline) —
those stay prose; they carry no canonical value to anchor. Nor does it cover
figures **derived in the wiki** rather than reported by the lab: a ratio you
computed yourself from two reported values is not a result, and putting it in
the table would let a wiki-side calculation anchor as authority. Keep derived
figures in prose, labelled as derived.

## Connections
- Related to [[concept-a]] because...
- Contrasts with [[concept-b]] in that...

## Sources
- [[summary-of-source-1]]

## Open Questions
Questions worth exploring further.

### Medication concepts
A concept tagged `medication` carries two extra frontmatter fields, after `updated`:

```
brand: {brand name as prescribed}          # e.g. Norvasc
local-brand-name: {full local product name, incl. dosage-form suffix}  # e.g. 脈優錠
```

They are the **source for the `generic (Brand, local name)` format** in body prose
(see Medication naming above) — copy them verbatim rather than rewording, so the
same medication reads identically everywhere: the two fields above give
`amlodipine (Norvasc, 脈優錠)`. `brand` records the name as actually prescribed,
which is not always a tidy originator brand (`amlodipine besylate`, `BZD Xanax`) —
keep it as prescribed rather than "correcting" it. `cn-title` may use a trimmed
form of `local-brand-name`; see Frontmatter aliases and `cn-title` above.

**`local-brand-name` is relative to `region` in wiki-config.yml, not to
`locale`.** It records the product name as dispensed, *in the market where it was
dispensed* — what is printed on the box the patient actually receives. The two
are different axes: a vault can read one locale while drawing care from
facilities in more than one market. A patient who reads Simplified Chinese but
fills prescriptions in Taipei still gets the Taiwan product name on the box, so
the field follows the pharmacy, not the reader. Under `locale: none` omit the
field entirely; a local-market brand is already what `brand` records.

## Summary File Format
Each wiki/summaries/{name}.md:

---
source: {original filename in raw/}
date-added: {date}
tags: [tag1, tag2]
facility: {slug}        # provenance field — see below
physician: {slug}       # provenance field — see below
result-status: normal | mixed | abnormal   # provenance field — see below
---

# Summary: {Document Title}

## Summary
3-5 sentence summary.

## Key Concepts
- [[concept-1]]

## Notable Details
Specific facts, figures, or arguments worth preserving.

## Backlinks
Other wiki articles this connects to.

### Provenance fields
`facility`, `physician`, and `result-status` record **who produced this document
and how it read** — a different axis from `tags`, which record what the document
is *about*. Keeping the axes apart is the whole point of these fields: provenance
was previously encoded as tags (a slug per clinic, a slug per physician, plus
`abnormal-result`), which polluted the closed clinical vocabulary and, because
every facility clears the 3-article threshold, would have mechanically demanded
a MOC for a clinic. Never reintroduce a provenance value as a tag.

**Summaries only.** A summary describes one document from one site on one date,
so it has a single provenance. A concept spans many draws across years and
therefore has none — provenance lives per-row in the concept's canonical table
(the `Lab` column and the ordering physician in `Notes`), not in its frontmatter.

All three fields are **optional and omitted rather than guessed**. A source
document that does not name its performing site gets no `facility` line; do not
infer one from the ordering clinic. `/lint` reports what is missing.

That rule binds **inference**, not knowledge. Provenance has three sources, and
only the third is forbidden: **the document** (the normal case, and the only one
an agent may act on alone), **the maintainer** (who knows things the paperwork
omits — record what they tell you), and **inference** (never — not from the
ordering clinic, not from a filename, not from a same-day sibling without a
shared printed identifier).

**Never write provenance into `raw/` on your own initiative.** Both the backfill
procedure and `/lint` read `raw/` as evidence of what a document actually said,
so a `Facility:` line added there would later read back as document-supplied.
Rule 1 (never modify `raw/`) exists for this. The one exception is adding a
`NOTE — PROVENANCE` header to a file the patient wrote themselves, at their
explicit request.

**Treat no file in `raw/` as a byte-for-byte export.** Source documents arrive in
many shapes — portal pages, PDFs, paper reports, photos of a printout — and are
converted to one plain-text file per document, so the content is faithful but the
shape is not the original's. Some files have no upstream artifact at all: a record
with no export option, typed out by hand. Keep a note in `raw/` recording which
files came from which process, and read it before treating any field there as
machine-generated.

The failure mode to watch is **promoting a human's informal phrasing into a
structured fact**. A hand-written medication list may open `Exported from …
Portal on <date>` simply because that is how its author chose to head the file;
nothing was exported, and the date means "recorded". Ingest reading such a
heading literally is how a *manufactured* date enters the vault and propagates
to every file that cites it. When a date in `raw/` is load-bearing, check it
against a second field in the same document before building on it.

**`facility` — the site that PRODUCED the document**: for a study, the site that
performed it, not the one that ordered it; for a prescription export, the site
that prescribed. When a clinic draws a specimen and an outside reference lab
runs it, the lab is the facility and the ordering clinician is the `physician`;
that pairing is what makes `facility: metro-labs` + `physician: dr-alvarez`
readable as "Dr. Alvarez ordered it, Metro Labs ran it". An export that names no
institution at all — a patient-portal medication list — still gets no field.
Values:

The values themselves live in `memory/provenance-roster.md` — see "The roster
lives outside this file" below.

Taiwan source documents distinguish **`Requesting Institution`** from
**`Performing Institution`** on the same report, and NHI-uploaded studies often
carry both. Take `facility` from the performing line. Two narrow cases let a
document that does not name its own performing site still get one — both
require printed evidence, not a plausible story:

- **A shared encounter identifier.** A one-day health checkup (一日健診) may
  produce four documents of which only the sonography names the hospital, while
  all four print the same checkup number — in the same date-plus-sequence form,
  spaced on some reports and not on others — and the same MRN. That identifier
  is a join, not an inference, so all four take the hospital's slug. A same-day,
  same-patient coincidence with no shared identifier is **not** sufficient.
- **A modality that can only have been performed at the requesting site.** An
  overnight in-lab study is the clear case: a polysomnography naming only
  `Requesting Institution: 台北和安醫院` still takes `facility: hean`, because a
  night in a sleep lab is not something the ordering hospital sends out. Do not
  stretch this to specimens — a clinic that requests a blood panel very often
  does send it out, which is exactly what the performing-site rule exists to
  capture.

Outside those two, a requesting-only line is the ordering site — omit the field.

**`physician` — the clinician responsible for the document.** Normally one
value. When a document names more than one clinician for the *same* item,
prefer in this order:

1. the **ordering / requesting / attending** clinician — this is the usual case,
   and it is what makes the pair `facility: metro-labs` + `physician: dr-alvarez`
   read as "Dr. Alvarez ordered it, Metro Labs ran it";
2. failing that, the **interpreting** physician or radiologist — the read is the
   document, so on a report that names no orderer the interpreter is the
   responsible clinician;
3. on a Taiwan report listing a resident and a visiting staff
   (`R Chang Yu-Chen / VS Yeh Cheng-Han`), the **VS** is the responsible one.

That precedence settles *one* item with several clinicians attached. A document
covering **several items with a different author each** is a different case, and
the precedence does not apply — there is no single responsible clinician to
pick. Write a flow-style list instead, in the order the document presents them:

```
physician: [dr-su-yi-fan, dr-ko-ming-hui]
```

A prescription export is the typical case: one specialist prescribed the
amlodipine and another the alprazolam, days apart for unrelated problems. Use a
list only when the document really has multiple authors — do not list a resident
alongside their visiting staff, or an interpreter alongside the orderer, since
the precedence above already answers those. Consumers must accept both a bare
slug and a list.

A document that genuinely names nobody gets no field. Establish that by reading
the source, not by reasoning from what the document lacks: a Holter report may
end with its interpretation and signature fields blank yet still name
`Physician: Dr. 蘇怡帆 (cardiologist)` in the demographics block on page 1. A
missing *interpretation* says nothing about whether an *ordering* clinician is
recorded, and the label is often the bare word `Physician:` with no qualifier.

Record each name exactly as its source document gives it — one report prints the
romanization alongside the characters, another gives characters only, and a third
names its visiting staff in romanization only. Do not supply the missing half
from inference: a guessed set of characters is a different person's name.

A Taiwan physician recorded under a Chinese name gets a romanized slug and keeps
the Chinese name in the table. The slug is an identifier, not a display name —
body prose still writes the name as the source document gives it.

**`result-status` — how the document read as a whole**, judged from what it
reports rather than from clinical severity:

| value | Meaning |
|---|---|
| `normal` | every reported value in range, or a qualitative study read as negative / no significant findings |
| `mixed` | a multi-analyte panel with some values flagged and some not |
| `abnormal` | a single abnormal finding, or a dominant one |
| *(omitted)* | the document reports no test result at all — a medication list, a prescription export |

`mixed` is the honest state for most panels and carries the most weight: a CBC
flagging WBC while every red-cell index is normal is a different document from a
lipid panel with all five values elevated. Judge the **document**, not the
number: a screening score of 0 is `abnormal` when the radiologist also reports an
unquantifiable finding alongside it, and `normal` when they do not.

### Adding a new facility or physician
Both vocabularies are closed, like the canonical tags. Before adding a value,
check whether an existing one covers it — a clinic's slug covers its satellite
sites, and a hospital's imaging department is the hospital. A new value is
justified when a source document names a site or clinician not already in the
roster. Add the row to `memory/provenance-roster.md`, with the Chinese name if
the facility has one, **before** using the slug in any file.

### The roster lives outside this file
Both tables are **executable**: `scripts/_provenance_vocab.py` parses
`memory/provenance-roster.md` at run time and both provenance checkers read
them from there, so adding the row to the roster is the entire edit — there is
no second copy in `scripts/` to keep in step, and a value used before it is
listed fails the check rather than passing silently. The loader matches each
table by its header row (`slug | Facility`, `slug | Physician`), so the prose
around them can be rewritten freely; the roster documents that contract.

The roster is separate from this file because it is **data about one patient's
care, not convention**. This file states how to *choose* a `facility` or
`physician` value; the roster records which values a given vault actually has.
Keeping them together meant a shared conventions file had to carry somebody's
clinic list, and made adding one clinic dirty CLAUDE.md.

A filled-in `memory/provenance-roster.md` stays out of any repository the
scripts are published to — `scripts/` is shareable and the roster is not. A
fresh clone starts from `memory/provenance-roster.example.md`, which has both
headers and no rows.

## Query File Format
Each query file is named `{YYYY-MM-DD}-{slugified-question}.md`, date-prefixed like
the files in wiki/sessions/archive/ — which share the date prefix but add a
`-session` suffix, precisely so the two never collide on basename. The date is the
`date:` value below — the day the answer was written. The date prefix applies in the `_superseded/` subfolder, and
to handoff documents in `wiki/deliverables/`, too.

Each wiki/queries/{YYYY-MM-DD}-{slugified-question}.md:

---
question: {the full question as asked}
date: {YYYY-MM-DD}
sources: [list of wiki articles consulted]
status: current
---

# {Question as Title}

## Answer
Full, thorough answer.

## Key Points
- Bullet summary of the most important takeaways.

## Source Articles Consulted
- [[article-1]]

## Follow-up Questions Worth Exploring
- Follow-up question 1

## Canonical Tags

Use only these tags in concept and summary frontmatter. 25 canonical tags total.

### Clinical domains
`biomarker` · `cardiology` · `hematology` · `hepatic` · `metabolic` · `glycemic` · `lipid` · `genitourinary` · `immunology` · `gastrointestinal` · `dermatology` · `musculoskeletal` · `sleep-medicine` · `sexual-health` · `neurology` · `respiratory`

### Cross-cutting
`screening` · `imaging-finding` · `clinical-finding` · `medication` · `procedure`

### Imaging modalities (summaries only, kept alongside `imaging-finding`)
`ultrasound` · `mri` · `ct` · `x-ray`

### Synonym → canonical mapping
| Non-canonical | Use instead |
|---|---|
| infectious-disease | immunology |
| renal, urology | genitourinary |
| lab-test, blood-test | biomarker |
| endocrinology | metabolic |
| cardiovascular, cardiac, atherosclerosis, calcium-scoring | cardiology |
| cbc, hemostasis, anemia | hematology |
| liver-function, nafld, biliary | hepatic |
| atherogenic, lipid-management, ldl-cholesterol | lipid |
| serology, viral-immunity | immunology |
| cancer-screening | screening |
| clinical-category, clinical-diagnosis, risk-state, risk-marker, benign | clinical-finding |
| statin, antihyperglycemic | medication |
| imaging (anywhere); ultrasound, mri, ct, x-ray (on concepts) | imaging-finding |

### Adding a new canonical tag
Before creating a new tag, check whether an existing canonical tag covers it.
A new tag is justified only if:
- No existing canonical tag fits the concept
- At least 2 existing or new articles would use it

Add the new tag to this list before using it in any file.

### Cross-cutting tags — no dedicated MOC
These tags are valid on concept and/or summary files but intentionally have no MOC
file. Do NOT create a MOC for them even if 3+ articles share the tag.

| Tag | Reason |
|---|---|
| `biomarker` | Spans all clinical domains; every domain MOC covers its own biomarkers |
| `ultrasound` | Modality, not a domain — see below |
| `mri` | Modality, not a domain — see below |
| `ct` | Modality, not a domain — see below |
| `x-ray` | Modality, not a domain — see below |

The four imaging modalities are one exemption, not four. They record **how a
study was performed**, which is a different axis from what an article is about —
the same distinction the `facility`/`physician` fields draw against `tags`. A
`moc-ultrasound` would list an abdominal study and a carotid study side by side
because they share a transducer, which is not a reason to read them together.

Their findings are already indexed twice: by subject in the domain MOC
(`moc-hepatic`, `moc-cardiology`, …) and by modality in `moc-imaging-finding`,
which is the imaging cross-index. Note also that these four are **summaries
only** (see Canonical Tags above) — a modality MOC could never list a concept.

Once a vault holds more than a handful of studies all four clear the 3-article
threshold, so without these rows `/lint` step 6b would demand four MOCs on
every run. That is the same mechanical trap the provenance fields were created to
avoid: a value that is not a clinical domain earning a domain's navigation
layer purely by counting.

## MOC File Format
Each wiki/mocs/moc-{domain}.md:

---
title: MOC — {Domain Title}
type: moc
tags: [{domain}]
aliases: [{中文 domain name}]
cn-title: MOC — {Domain Title} ({中文})
updated: {date}
---

# {Domain Title} — Map of Content

## Concepts
- [[concept-filename]] — one-sentence description

## Source Summaries
- [[summary-filename]] — one-sentence description

## Key Relationships
One paragraph of 2-3 sentences explaining how the listed concepts and source
summaries connect to each other.

Keep every relationship source-grounded in the linked articles and preserve
their qualifications: a diagnosis stated on an order is not a confirmed
finding, and two missing forms of evidence are not substitutes merely because
both are absent. This section explains established connections only. Put open
questions in the relevant concept article instead; do not include missing-
document inventories, document-acquisition advice, follow-up recommendations,
or other action items here. If the MOC was triggered by several articles
derived from one source, state only the relationship that source supports and
do not pad the section to make the domain appear broader.

A new MOC is created when 3+ concepts or summaries share a canonical tag with no existing MOC.
MOC files are never indexed in wiki/processed.log.

## Index Entry Format
wiki/index.md is organized into domain sections. Each section heading matches a canonical domain tag (e.g., `## Cardiology`, `## Lipid`). Cross-cutting types (Queries, MOC Files, etc.) have their own sections at the bottom.

When adding a new entry, place it under the section matching the article's **primary domain tag** — the first clinical-domain tag listed in its frontmatter. If the article has only cross-cutting tags (screening, medication, etc.), place it under the most relevant domain section or create a new section if none fits.

Each entry in wiki/index.md:

## {filename}.md
- **Type:** concept | summary | query | slide | handoff | maintenance
  (slide and handoff files live in wiki/deliverables/)
- **Tags:** tag1, tag2
- **Summary:** One sentence description.
- **Related:** [[article-a]], [[article-b]]

### The Compilation Summary block

`wiki/index.md` opens with a `## Compilation Summary` section that is **owned by
the ingest workflow** (`prompts/p1-ingest.md` step 7b) — no other workflow writes
it. It is append-only: the first ingest into an empty vault writes one paragraph,
and each ingest afterwards appends **one new paragraph** opening with its bold
date (`**2026-07-27:**`, disambiguated as `**2026-07-27 (second ingest):**` when
that date is already used). 4–6 sentences: what was ingested, the headline
finding, the concepts and MOCs touched, and the resulting counts.

**Every** paragraph carries a bold date, the first one included — an undated
paragraph cannot be sorted or audited. The section runs **oldest-first**, which
is what makes "append at the end" equivalent to date order; never reverse it.
`scripts/check-compilation-summary.py` audits the block against the ingest
history recorded in git and is part of `/lint`.

Never rewrite, re-scope, or delete an existing paragraph, and never append
sentences onto the end of one. Two consumers depend on one-ingest-one-paragraph:
`p3-qa.md` reads this block a whole paragraph at a time, and the paragraph is
the translation counting unit here (see the `wiki/index.md` counting-units rule
above).

## Home Page Format
wiki/home.md has two sections:

### Maps of Content
Table columns: MOC | Domain | Articles
One row per wiki/mocs/ file; MOC as [[wikilink]]; Articles = count of
concepts + summaries tagged with that domain.

### Tags Without a MOC
Subtitle: "These tags have fewer than 3 articles and no MOC file yet.
Articles may still be covered by other domain MOCs — this table tracks tags,
not orphaned articles."
Table columns: Tag | Articles sharing this tag | Count
One row per non-cross-cutting canonical tag with <3 articles and no MOC.
Articles as [[wikilinks]], comma-separated. Sorted by Count descending.
Omit section if empty.
