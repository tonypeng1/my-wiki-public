---
name: qa
description: Ask a question of this personal health wiki. Every question is a turn in a session — a one-off question is simply a session with one turn, published by $session-close. Use when the user asks for qa, a wiki question, one-off Q&A, a session question, a follow-up in session, or conversational Q&A.
---

# QA

Run the repository workflow defined in `prompts/p3-qa.md`.

Before acting, read `AGENTS.md`, `CLAUDE.md`, `memory/MEMORY.md`, any relevant
memory files it references, and `prompts/p3-qa.md` in full.

Use the user's current question as the prompt's question argument. Execute the
workflow exactly, updating `wiki/sessions/current.md` and
`wiki/sessions/log.md` as instructed.

This workflow never writes to `wiki/queries/` and never updates
`wiki/index.md` — `$session-close` is the only publisher. Close your response
by telling the user the answer is not published until they run
`$session-close`.
