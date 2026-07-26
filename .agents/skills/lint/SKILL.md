---
name: lint
description: Run this repository's full quarterly wiki health-check workflow. Use when the user asks for lint, full health check, quarterly check, tag canonicalization, backlink checks, dangling wikilink validation, MOC freshness, or maintenance report generation.
---

# Lint

Run the repository workflow defined in `prompts/p4-lint.md`.

Before acting, read `AGENTS.md`, `CLAUDE.md`, `memory/MEMORY.md`, any relevant
memory files it references, and `prompts/p4-lint.md` in full.

Then execute the prompt instructions exactly and report a concise summary of
checks, changes, and generated maintenance output.
