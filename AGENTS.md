# Codex Instructions

This repository is a personal health wiki. Follow the project conventions in
`CLAUDE.md`; treat that file as the shared source of truth for article formats,
tag rules, backlink style, directory meanings, and memory handling.

At the start of a task, read `memory/MEMORY.md` and then read any referenced
memory files that are relevant to the user's request. When saving persistent
project memory, write it under `memory/`, not under a tool-specific global
memory directory.

Use the prompt files in `prompts/` as reusable workflow instructions. Claude
Code slash commands in `.claude/commands/` are wrappers around those prompts;
Codex should read and execute the corresponding `prompts/*.md` file directly
when the user asks for that workflow by name.

For the incremental ingest workflow, Codex can also use the repo skill
`$ingest-increm`, defined in `.agents/skills/ingest-increm/`.

Never modify files in `raw/`. Keep generated wiki content under `wiki/`, keep
automation under `scripts/`, and preserve Obsidian-style `[[backlinks]]`.
