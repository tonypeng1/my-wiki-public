---
name: post-ingest
description: Run this repository's post-ingest housekeeping workflow after incremental ingest. Use when the user asks for post-ingest, post ingest, canonicalizing tags, canonical record format, frontmatter completeness (aliases, cn-title, medication brand fields), backlink cleanup for newly ingested concepts, MOC freshness, or home/index refresh after ingest.
---

# Post Ingest

Run the repository workflow defined in `prompts/p4a-post-ingest.md`.

Before acting, read `AGENTS.md`, `CLAUDE.md`, `memory/MEMORY.md`, any relevant
memory files it references, and `prompts/p4a-post-ingest.md` in full.

Then execute the prompt instructions exactly. Preserve canonical tags,
Obsidian-style `[[backlinks]]`, MOC structure, `wiki/index.md`, and
`wiki/home.md`.
