---
name: sync-to-public
description: Sync this private wiki's public files to the sibling my-wiki-public repository. Use when the user asks for sync-to-public, public sync, or updating the public repo mirror.
---

# Sync To Public

Mirror the Claude command behavior in `.claude/commands/sync-to-public.md`.

Run:

```bash
bash scripts/sync-to-public.sh
```

Display the script output. Do not independently diff files unless the user asks.
If the output lists pending deletions, ask the user whether to delete them before
proceeding. If it says "PRIVACY GATE: SYNC BLOCKED", stop and report — never
bypass the gate. If the CLAUDE.md review section reports a change, follow the
review flow in `prompts/sync-to-public.md` (port hunks by hand, genericizing
examples, then `--claude-md-reviewed` after the user confirms). Follow relevant
memory from `memory/MEMORY.md`, especially any sync-to-public feedback.
