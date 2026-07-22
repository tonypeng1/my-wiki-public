Sync public files from /Users/tony3/Projects/my-wiki to /Users/tony3/Projects/my-wiki-public.

This workflow is script-driven. Run `bash scripts/sync-to-public.sh` and report its
output — do not diff files yourself. This document records *what* the script mirrors
and why, so the two repos stay functionally equivalent.

## What the public repo mirrors

Workflow definitions:
- prompts/            (all .md files)
- .claude/commands/   (all .md files)
- .agents/skills/     (Codex skill wrappers; AGENTS.md points at these)

Automation the prompts depend on:
- scripts/            (all .sh and .py files)
- memory/medical-term-translations.md — shared glossary; check-bilingual-terms.py,
  check-glossary-delta.py and extract-term-candidates.py all default to this path
- .claude/settings.json — permission allowlist for those scripts
  (.claude/settings.local.json is machine-local and never synced)

Conventions and entry points:
- CLAUDE.md
- AGENTS.md
- README.md
- .gitignore
- wiki/slides/_marp-template.md

## What is never synced

- raw/ — source documents
- wiki/ content: summaries/, concepts/, queries/, mocs/, slides/ (except the Marp
  template), sessions/, maintenance/, index.md, processed.log. The public repo keeps
  empty .gitkeep placeholders for these directories; the script must never overwrite
  them with real content.
- memory/ — everything except the glossary above (MEMORY.md and all personal,
  project, and feedback memories stay private). The public repo keeps its own
  hand-written `memory/MEMORY.md` starter index; the script must never overwrite
  it with this repo's private one.

## Rules

1. The script copies new and modified files only. It never deletes.
2. Files present in the public repo but gone from my-wiki are reported as
   "Pending deletion". Ask the user before removing any of them.
3. When a prompt starts depending on a new file (a script, a glossary, a template),
   add it to `scripts/sync-to-public.sh` and to the list above in the same change —
   otherwise the public workflow references a file that was never published.
4. Commit in the public repo with:

   feat: sync from my-wiki

   - <one line per changed file describing what changed>

   Keep each bullet concise and specific (e.g. "add p3c-session-reopen.md",
   "fix archive naming in p3b", not just "update p3b").
