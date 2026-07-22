---
name: ingest-first
description: Run this repository's first-ingest workflow to compile the personal health wiki from all files in raw/. Use when the user asks for ingest-first, first ingest, initial ingest, or building the wiki from scratch.
---

# Ingest First

Run the repository workflow defined in `prompts/p1-first-ingest.md`.

Before acting, read `AGENTS.md`, `CLAUDE.md`, `memory/MEMORY.md`, any relevant
memory files it references, and `prompts/p1-first-ingest.md` in full.

Then execute the prompt instructions exactly. Never modify `raw/`; use only
canonical tags from `CLAUDE.md`; preserve Obsidian-style `[[backlinks]]`; and
report a concise summary of created and modified files.
