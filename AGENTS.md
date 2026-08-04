# Codex Instructions

This repository is a personal health wiki. Follow the project conventions in
`CLAUDE.md`; treat that file as the shared source of truth for article formats,
tag rules, backlink style, directory meanings, and memory handling.

At the start of a task, read `memory/MEMORY.md` and then read any referenced
memory files that are relevant to the user's request. When saving persistent
project memory, write it under `memory/`, not under a tool-specific global
memory directory.

Use the prompt files in `prompts/` as reusable workflow instructions. Claude
Code slash commands in `.claude/commands/` are wrappers around those prompts and
are not Codex's entry point.

Every workflow is packaged as a repo skill under `.agents/skills/`, named to
match its Claude slash command: `$ingest`, `$post-ingest`, `$qa`,
`$session-close`, `$session-reopen`, `$contradiction-check`, `$coverage-check`,
`$triage-queries`, `$translation-backfill`, `$lint`, `$slides`, `$synthesis`,
`$sync-to-public`, `$rewrite`, and `$commit-push-codex`
(Codex's `/commit-push`, with a Codex co-author trailer).

Prefer the skill over the prompt file. A skill can do more than read one
prompt — `$ingest` chains `prompts/p4a-post-ingest.md` after
`prompts/p1-ingest.md` whenever new files were added — so executing a
`prompts/*.md` file directly may silently skip a required pass. Read a prompt
directly only when the user names that file, or when no skill covers it.

Never modify the contents of files in `raw/`; the only change permitted there is
renaming a not-yet-ingested source file to the convention in CLAUDE.md ("Source
filenames in `raw/`"). Keep generated wiki content under `wiki/`, keep
automation under `scripts/`, and preserve Obsidian-style `[[backlinks]]`.
