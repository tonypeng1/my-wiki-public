---
name: qa
description: Answer a one-off question from this personal health wiki and save the result to wiki/queries/. Use when the user asks for qa, one-off Q&A, a wiki question, or wants an answer saved as a query.
---

# QA

Run the repository workflow defined in `prompts/p3-qa.md`.

Before acting, read `AGENTS.md`, `CLAUDE.md`, `memory/MEMORY.md`, any relevant
memory files it references, and `prompts/p3-qa.md` in full.

Use the user's current question as the prompt's question argument. Execute the
workflow exactly, save the query result as instructed, and report the saved file.
