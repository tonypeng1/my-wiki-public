---
name: ingest
description: Run this repository's personal health wiki ingest workflow. Use when the user asks for ingest, incremental ingest, first ingest, initial ingest, processing new raw files, building the wiki from raw/, or updating the wiki from new files in raw/.
---

# Ingest

Run the repository workflow defined in `prompts/p1-ingest.md`.

This is the only ingest workflow — it handles both the first run on an empty
vault and every incremental run afterwards. Files already listed in
`wiki/processed.log` are never re-processed; there is no full-rebuild mode.

Before acting:

1. Read `AGENTS.md`.
2. Read `CLAUDE.md`.
3. Read `memory/MEMORY.md` and any relevant memory files it references.
4. Read `prompts/p1-ingest.md` in full.

Then execute the prompt instructions exactly, preserving the repository rules:

- Never modify `raw/`.
- Check `wiki/processed.log` before processing source files.
- Create or update summaries, concepts, backlinks, MOCs, `wiki/index.md`, and
  `wiki/home.md` as the prompt requires.
- Append one new dated paragraph to the `## Compilation Summary` section of
  `wiki/index.md` (step 7b) — never rewrite or extend an existing paragraph.
- Use only canonical tags from `CLAUDE.md`.
- Report a concise summary of created and modified files.

Then, only if that ingest processed one or more new files (i.e. it did not report
the wiki was already up to date), read and execute `prompts/p4a-post-ingest.md`.
