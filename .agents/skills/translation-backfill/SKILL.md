---
name: translation-backfill
description: Repair missing Traditional Chinese medical-term translations in existing wiki files. Use when the user asks for translation backfill, bilingual cleanup, missing Chinese terms, or paragraph-level medical-term QA on an existing batch of wiki content. If the user does not specify a scope, select the next reasonable backfill domain yourself.
---

# Translation Backfill

Run the repository workflow defined in `prompts/translation-backfill.md`.

Before acting, read `AGENTS.md`, `CLAUDE.md`, `memory/MEMORY.md`, any relevant
memory files it references, and `prompts/translation-backfill.md` in full.

Use the user's requested scope as the prompt's scope argument. If no scope was
provided, choose the next reasonable backfill batch yourself.

Then execute the prompt instructions exactly. Preserve Obsidian-style
`[[backlinks]]`, English filenames and titles, canonical tags, and the
repo's Taiwan Traditional Chinese glossary conventions.
