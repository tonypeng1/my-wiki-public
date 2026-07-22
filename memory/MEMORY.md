# Memory Index

This file is the memory index. `CLAUDE.md`, `AGENTS.md`, and the Codex skills in
`.agents/skills/` all read it at the start of a task, then read the individual
memory files it points to.

In the maintainer's private repo this index lists personal facts, corrections,
and workflow feedback accumulated over time. Those entries are not published —
this public copy ships only the shared glossary, which the translation scripts
depend on. Add your own entries as you use the wiki.

- [Traditional Chinese medical term glossary](medical-term-translations.md) — shared Taiwan Traditional Chinese translations for recurring medical terms

## Conventions

One file per memory, in this directory. Keep this index to one line per memory —
`- [Title](file.md) — short hook` — and never put the memory content here.

Each memory file carries frontmatter:

```markdown
---
name: <short-kebab-case-slug>
description: <one-line summary used to decide relevance during recall>
metadata:
  type: user | feedback | project | reference
---
```

`user` — who the patient/user is. `feedback` — guidance on how the agent should
work, with the reasoning behind it. `project` — ongoing work and constraints not
derivable from the files themselves; write dates as absolute `YYYY-MM-DD`.
`reference` — pointers to external resources. Link related memories with
`[[their-name]]`.
