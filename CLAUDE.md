# Wiki Conventions

## Directory Structure
- raw/              → source documents (never modify these)
- wiki/summaries/   → one .md per source document
- wiki/concepts/    → one .md per concept/topic
- wiki/queries/     → saved Q&A outputs
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

## Index Entry Format
Each entry in wiki/index.md:

## {filename}.md
- **Type:** concept | summary | query | slide | maintenance
- **Tags:** tag1, tag2
- **Summary:** One sentence description.
- **Related:** [[article-a]], [[article-b]]
