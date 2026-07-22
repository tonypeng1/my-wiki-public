---
name: triage-queries
description: Run this repository's query triage workflow to move misplaced query files into _handoff or _superseded after user confirmation. Use when the user asks for triage-queries, query triage, misplaced query cleanup, or superseded query review.
---

# Triage Queries

Run the repository workflow defined in `prompts/p4d-triage-queries.md`.

Before acting, read `AGENTS.md`, `CLAUDE.md`, `memory/MEMORY.md`, any relevant
memory files it references, and `prompts/p4d-triage-queries.md` in full.

Then execute the prompt instructions exactly. This workflow requires interactive
confirmation before moving files; present candidates and wait for approval.
