---
name: ingest-increm
description: Run this repository's personal health wiki incremental ingest workflow. Use when the user asks for incremental ingest, ingest-increm, processing new raw files, or updating the wiki from new files in raw/.
---

# Ingest Incremental

Run the repository workflow defined in `prompts/p2-incremental-ingest.md`.

Before acting:

1. Read `AGENTS.md`.
2. Read `CLAUDE.md`.
3. Read `memory/MEMORY.md` and any relevant memory files it references.
4. Read `prompts/p2-incremental-ingest.md` in full.

Then execute the prompt instructions exactly, preserving the repository rules:

- Never modify `raw/`.
- Check `wiki/processed.log` before processing source files.
- Create or update summaries, concepts, backlinks, MOCs, `wiki/index.md`, and
  `wiki/home.md` as the prompt requires.
- Use only canonical tags from `CLAUDE.md`.
- Report a concise summary of created and modified files.
