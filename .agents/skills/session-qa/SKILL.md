---
name: session-qa
description: Ask a question inside a live personal health wiki Q&A session, creating session files if needed and preserving context across turns. Use when the user asks for session-qa, session question, follow-up in session, or conversational wiki Q&A.
---

# Session QA

Run the repository workflow defined in `prompts/p3a-session-qa.md`.

Before acting, read `AGENTS.md`, `CLAUDE.md`, `memory/MEMORY.md`, any relevant
memory files it references, and `prompts/p3a-session-qa.md` in full.

Use the user's current question as the prompt's question argument. Execute the
workflow exactly, updating `wiki/sessions/current.md` and
`wiki/sessions/log.md` as instructed.
