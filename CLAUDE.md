<!--
Hand-maintained public copy of the private repo's CLAUDE.md. Conventions are
identical; medication and condition examples are fictional substitutes for the
private originals. Maintainers: when scripts/sync-to-public.sh reports that the
private CLAUDE.md changed, port the convention hunks here by hand, keep every
example generic, then rerun with --claude-md-reviewed.
-->

# Wiki Conventions

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
  - archive/        → closed sessions saved as YYYY-MM-DD-{topic-slug}.md (+ -log.md) for reference
- wiki/index.md     → master index of all wiki content
- wiki/processed.log → list of already-processed raw/ files

## Backlink Format
Always use Obsidian-style backlinks: [[article name]]
Article name should match the filename without the .md extension.

## General Rules
1. Never modify anything in raw/
2. Always check wiki/processed.log before processing raw/ files
3. Always update wiki/index.md after creating or modifying any wiki file
4. Always add backlinks using [[name]] syntax
5. Dates should be in YYYY-MM-DD format
6. Filenames should be lowercase-hyphenated, e.g. surface-code-basics.md
   (exception: query files under wiki/queries/ are prefixed with their date,
   e.g. 2026-05-21-slug.md — see the Query File Format section)

## Traditional Chinese Medical Terms

The patient is a native Traditional Chinese reader from Taiwan. Make medical prose
easier to read by adding Traditional Chinese translations for medical terms.

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
- Format: English term, then the Traditional Chinese in parentheses:
  `Carotid intima-media thickness (IMT) (頸動脈內膜中層厚度)`.

### Medication naming
- This is a **repo-wide** rule for medication mentions in body content.
- On the **first mention of a medication in each `###` section**, write it as
  `generic (Brand, Taiwan name)`.
- If a file has no `###` headings in the relevant area, fall back to the first
  mention within the enclosing `##` section.
- Apply the same format on the **first mention inside tables, Key Points,
  follow-up bullets, and other skim-heavy recap blocks**, even if the medication
  already appeared earlier in the file.
- Later mentions within the same `###` section can use the generic name alone
  unless repeating the brand/Taiwan name materially improves clarity.
- Keep `#` titles, frontmatter titles, filenames, and Obsidian backlinks in
  English only; do not add brand/Taiwan-name parentheticals there.
- The Brand and Taiwan name come from the `brand` and `taiwan-brand-name` fields in
  that medication's concept frontmatter (see Concept Article Format) — use them
  verbatim so the same medication reads identically everywhere.
- Examples: `amlodipine (Norvasc, 脈優)`, `atorvastatin (Lipitor, 立普妥)`,
  `alprazolam (Xanax, 贊安諾)`.

### Abbreviations
- A term and its abbreviation are the **same term**. Whether an article uses only
  the abbreviation (e.g. `AST`), only the full name, or both, the first mention
  gets a Traditional Chinese translation.
- Keep the abbreviation in English and put the Chinese after the full term:
  `aspartate aminotransferase (AST) (天門冬胺酸轉胺酶)`. If only the abbreviation
  appears, attach the Chinese to it: `AST (天門冬胺酸轉胺酶)`.

### What NOT to translate
Leave in English:
- filenames, article titles, and Obsidian backlinks
- physician names and institution names
- units, and **opaque lab/order identifiers that carry no medical meaning of
  their own** — numeric or catalog codes, LOINC codes, accession numbers, MRN,
  panel item numbers.

Two clarifications:
- Medication brand names are still not translated as ordinary clinical terms,
  but in body prose they are intentionally included in the medication format
  `generic (Brand, Taiwan name)` per the Medication naming rule above.
- Exception: translate anyway when the source document itself supplies the
  Chinese wording.
- An abbreviation that *denotes a medical concept* (AST, GGT, eGFR) IS translated
  per the Abbreviations rule above. Only identifiers with no standalone medical
  meaning are excluded — that is what "opaque identifier" means here.

### Frontmatter aliases and `cn-title`
Two frontmatter layers make the vault navigable in Chinese **without renaming any
file** — filenames, `title`, and `[[backlinks]]` stay English-canonical per "What
NOT to translate" above.

**`aliases`** — add useful Traditional Chinese terms when they help searchability,
so the note is reachable by its Chinese name in Obsidian's Quick Switcher and
global search. Every concept and MOC should carry at least one Chinese alias.

**`cn-title`** — a display field in `English (中文)` form, read by the Front Matter
Title Obsidian plugin to label the file tree, tabs, and graph. Required on every
**concept** and **MOC** file (summaries and queries do not use it). Rules:
- The English part is the concept's **common abbreviation** when it has one
  (`GGT (γ-谷氨醯轉移酶)`, `COPD (慢性阻塞性肺病)`, `PSA (攝護腺特異抗原)`),
  otherwise the plain name (`Gout (痛風)`, `Peptic Ulcer (消化性潰瘍)`).
- MOCs keep their full title: `MOC — Cardiology (心臟科)`.
- Medications answer **"what kind of drug is this?"**, never the brand — the brand
  is already in `brand`/`taiwan-brand-name` and in `aliases`. In order of
  preference:
  1. the **Chinese generic name**, when one is in common Taiwan use:
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

New concept and MOC files created during ingest or by a maintenance pass must get
both, or they show English-only in the sidebar.

Obsidian rewrites the frontmatter of any note it has open into block-style YAML and
can clobber CLI edits with its cached copy. The repo convention is inline flow style
(`aliases: [x, y]`); when bulk-editing frontmatter, keep the affected notes closed in
Obsidian or commit promptly so a clobber is recoverable.

### The shared glossary
Use `memory/medical-term-translations.md` as the shared glossary during ingest,
article updates, query answers, and slide creation. Reuse existing entries and
prefer Taiwan Traditional Chinese clinical wording. If unsure of the correct
Taiwan wording, add the term to the glossary for later review instead of guessing.

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
aliases: [3–5 abbreviations, alternate spellings, lay terms, + the Traditional Chinese name]
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

The rule covers **measured patient result values** (a lab/imaging number with a
unit). It does *not* pull in reference ranges or interpretation thresholds
(general knowledge), medication doses, qualitative findings with no number, or
dated *events* (a medication's prescribe/discontinue dates, a diagnosis
timeline) — those stay prose; they carry no canonical value to anchor.

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
taiwan-brand-name: {full Taiwan product name, incl. dosage-form suffix}  # e.g. 脈優錠
```

They are the **source for the `generic (Brand, Taiwan name)` format** in body prose
(see Medication naming above) — copy them verbatim rather than rewording, so the
same medication reads identically everywhere: the two fields above give
`amlodipine (Norvasc, 脈優錠)`. `brand` records the name as actually prescribed,
which is not always a tidy originator brand (`amlodipine besylate`, `BZD Xanax`) —
keep it as prescribed rather than "correcting" it. `cn-title` may use a trimmed
form of `taiwan-brand-name`; see Frontmatter aliases and `cn-title` above.

## Summary File Format
Each wiki/summaries/{name}.md:

---
source: {original filename in raw/}
date-added: {date}
tags: [tag1, tag2]
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

## Query File Format
Each query file is named `{YYYY-MM-DD}-{slugified-question}.md`, date-prefixed like
the files in wiki/sessions/archive/. The date is the `date:` value below — the day
the answer was written. The date prefix applies in the `_superseded/` subfolder, and
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

Use only these tags in concept and summary frontmatter. 24 canonical tags total.

### Clinical domains
`biomarker` · `cardiology` · `hematology` · `hepatic` · `metabolic` · `glycemic` · `lipid` · `genitourinary` · `immunology` · `gastrointestinal` · `dermatology` · `musculoskeletal` · `sleep-medicine` · `sexual-health` · `neurology` · `respiratory`

### Cross-cutting
`screening` · `imaging-finding` · `clinical-finding` · `medication` · `procedure`

### Imaging modalities (summaries only, kept alongside `imaging-finding`)
`ultrasound` · `mri` · `ct`

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
| imaging, ultrasound, mri, ct (on concepts) | imaging-finding |

### Adding a new canonical tag
Before creating a new tag, check whether an existing canonical tag covers it.
A new tag is justified only if:
- No existing canonical tag fits the concept
- At least 2 existing or new articles would use it

Add the new tag to this list before using it in any file.

### Cross-cutting tags — no dedicated MOC
These tags are valid on concept and summary files but intentionally have no MOC file.
Do NOT create a MOC for them even if 3+ articles share the tag.

| Tag | Reason |
|---|---|
| `biomarker` | Spans all clinical domains; every domain MOC covers its own biomarkers |

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
2-3 sentences on how these concepts connect to each other.

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
