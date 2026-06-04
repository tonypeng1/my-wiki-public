# Wiki Conventions

## Directory Structure
- raw/              → source documents (never modify these)
- wiki/summaries/   → one .md per source document
- wiki/concepts/    → one .md per concept/topic
- wiki/home.md         → vault entry point; links to all MOCs
- wiki/mocs/           → one moc-{domain}.md per clinical domain; navigation layer for Obsidian
- wiki/queries/     → saved Q&A outputs
  - _handoff/       → clean versions intended to be given to someone (no wiki metadata sections)
  - _superseded/    → answers replaced by a newer, more complete query
- wiki/slides/      → Marp slide decks
- wiki/maintenance/ → health check reports
- wiki/sessions/    → transient session scratch pad (NOT wiki content; do not index)
  - current.md      → active session conversation (deleted when session closes)
  - archive/        → closed sessions saved as YYYY-MM-DD-HHmm.md for reference
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

## Concept Article Format
Each wiki/concepts/{name}.md:

---
title: {Concept Name}
tags: [tag1, tag2]
aliases: [3–5 abbreviations, alternate spellings, lay terms]
updated: {date}
---

# {Concept Name}

## Overview
2-4 sentence plain explanation.

## Key Details
Main substance of the article.

## Connections
- Related to [[concept-a]] because...
- Contrasts with [[concept-b]] in that...

## Sources
- [[summary-of-source-1]]

## Open Questions
Questions worth exploring further.

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
Each wiki/queries/{slugified-question}.md:

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
- **Type:** concept | summary | query | slide | maintenance
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
