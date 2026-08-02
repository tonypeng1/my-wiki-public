# Memory Index

This file is the memory index. `CLAUDE.md`, `AGENTS.md`, and the Codex skills in
`.agents/skills/` all read it at the start of a task, then read the individual
memory files it points to.

In the maintainer's private repo this index lists personal facts, corrections,
and workflow feedback accumulated over time. Those entries are not published —
this public copy ships only the shared glossaries, which the translation scripts
depend on. Add your own entries as you use the wiki.

Both glossaries ship so a clone can become either locale; `wiki-config.yml`
selects one. Your vault's provenance roster is *not* listed here — it is data
about one patient's care, so `memory/provenance-roster.md` never ships and
`scripts/new-vault.sh` creates yours from `memory/provenance-roster.example.md`.

- [Traditional Chinese medical term glossary](medical-term-translations-zh-tw.md) — Taiwan Traditional Chinese translations for recurring medical terms; select it with `locale: zh-TW`
- [Simplified Chinese medical term glossary](medical-term-translations-zh-cn.md) — Mainland Simplified Chinese translations for the same terms; select it with `locale: zh-CN`. Not yet reviewed by a native Mainland clinical reader — check wording before relying on it

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
