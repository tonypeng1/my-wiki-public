Mirror this repo's public files to its companion public repo — the sibling
directory named `<repo-name>-public`. Both paths are derived by the script from
its own location; nothing here is machine-specific.

This workflow is script-driven. Run `bash scripts/sync-to-public.sh` and report its
output — do not diff files yourself. (`--dry-run` reports without copying;
`--claude-md-reviewed` is part of the CLAUDE.md review flow below.) This document
records *what* the script mirrors and why, so the two repos stay functionally
equivalent.

Maintainer-only: it runs in the private source repo and copies files out. Run from
a clone of the public repo, the script says so and exits without doing anything.

## What the public repo mirrors

Workflow definitions:
- prompts/            (all .md files)
- .claude/commands/   (all .md files)
- .agents/skills/     (Codex skill wrappers; AGENTS.md points at these)

Automation the prompts depend on:
- scripts/            (all .sh and .py files)
- wiki-config.example.yml — the locale config TEMPLATE, never this vault's live
  wiki-config.yml. Shipping the real one would hand every clone `locale: zh-TW`
  pre-set and silently defeat the p1-ingest step 0 gate; a clone with no config
  trips that gate instead, which is the point.
- memory/medical-term-translations-*.md — EVERY glossary, not just the one this
  vault is configured for, so a clone can become any supported locale. Shipping
  only the configured one left the public repo with no Simplified glossary at
  all.
- memory/provenance-roster.example.md — the provenance roster TEMPLATE (both
  table headers, zero rows). The filled-in memory/provenance-roster.md is the
  patient's real clinics and clinicians and never ships.

  Those are the only memory/ files that ship.
- .claude/settings.json — permission allowlist for those scripts
  (.claude/settings.local.json is machine-local and never synced)

Conventions and entry points:
- AGENTS.md
- README.md
- .gitignore, .gitattributes
- docs/graph-view.png (README hero image)
- wiki/deliverables/_marp-template.md

## What is never synced

- raw/ — source documents
- wiki/ content: summaries/, concepts/, queries/, mocs/, deliverables/ (except the Marp
  template), sessions/, maintenance/, index.md, processed.log. The public repo keeps
  empty .gitkeep placeholders for these directories; the script must never overwrite
  them with real content.
- memory/ — everything except the glossaries and the roster template above
  (MEMORY.md, memory/provenance-roster.md, and all personal, project, and
  feedback memories stay private). The public repo keeps its own
  hand-written `memory/MEMORY.md` starter index; the script must never overwrite
  it with this repo's private one.
- CLAUDE.md — the private copy documents conventions with the patient's real
  medications and conditions as examples, and drifts back to them even after
  cleanups. The public repo carries a hand-maintained copy instead: identical
  conventions, fictional examples. See the review flow below.

## The privacy gate

Before copying anything, the script derives a denylist from the vault itself —
medication generic names (basenames of medication-tagged concepts), their
`brand`/`local-brand-name` field values, and the patient's Chinese name from
memory/patient-name.md — and scans every file it could ship, plus the two
hand-maintained public files (CLAUDE.md, memory/MEMORY.md). Any hit blocks the
entire sync with the file, line, and matched term.

On a block: genericize the flagged line (or fix the file) and rerun. Never
bypass the gate, and never "fix" a block by removing a term from the
derivation. A brand name that is also a common English word is skipped
automatically (with a notice) and stays covered by its generic name.

## The CLAUDE.md review flow

The script snapshots the private CLAUDE.md at each review
(`.sync-claude-md-reviewed`, private, never synced). On every run it compares:

- unchanged → nothing to do.
- changed → it prints the cumulative diff since the last review. Present each
  hunk to the user with a disposition: port as-is (pure convention change),
  port genericized (a real rule illustrated with a real medication or
  condition — the rule crosses, the example gets a fictional substitute), or
  skip (patient-specific, or touches a section the public copy intentionally
  lacks). Edit the public CLAUDE.md accordingly. Only after the user confirms
  the port, rerun with `--claude-md-reviewed` to record it.

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
