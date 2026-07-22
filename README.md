# my-wiki

A **personal health wiki** driven by AI prompts. Raw medical source documents (lab results, imaging reports, clinical notes, medication records) are ingested and transformed into structured concept articles, summaries, Q&A records, and slide decks — all cross-linked using Obsidian-style `[[backlinks]]`.

> **Scope: medical data only.** The project's tagging taxonomy, article formats, and MOC structure are purpose-built for clinical domains. Non-medical documents (finance, recipes, general notes) cannot be meaningfully tagged and should not be ingested here. Use a separate wiki for other domains.

## Inspiration

The structure and ideas behind this project are inspired by [Andrej Karpathy's post on LLM Knowledge Bases](https://x.com/karpathy/status/2039805659525644595) (April 2026), in which he describes using LLMs to incrementally compile a personal wiki from raw source documents — with summaries, concept articles, backlinks, Q&A, Marp slides, and health-check linting — all maintained by the LLM and viewed in Obsidian.

## Directory Structure

```
raw/              → source documents (never modify these)
wiki/
  home.md         → vault entry point; links to all MOCs
  index.md        → master index of all wiki content
  processed.log   → list of already-processed raw/ files
  summaries/      → one .md per source document
  concepts/       → one .md per concept/topic
  mocs/           → one moc-{domain}.md per clinical domain
  queries/        → saved Q&A outputs (files named YYYY-MM-DD-{slug}.md)
    _handoff/     → clean versions intended to be given to someone
    _superseded/  → answers replaced by a newer query
  slides/         → Marp slide decks
  maintenance/    → health check and synthesis reports
  sessions/       → transient session scratch pad (not wiki content)
    current.md    → active session full Q&A log (deleted on close)
    log.md        → compact session summary, one entry per turn (deleted on close)
    archive/      → closed sessions saved as YYYY-MM-DD-{topic-slug}.md + YYYY-MM-DD-{topic-slug}-log.md
scripts/          → automation scripts (Python pre-filters for lint prompts, bilingual/glossary/medication checkers, term-candidate extractor, sync helper)
memory/           → persistent facts and corrections used by Claude/Codex
.claude/
  commands/       → slash command definitions that power the workflows
prompts/          → reusable AI prompt files
CLAUDE.md         → project conventions auto-loaded by Claude Code each session
AGENTS.md         → Codex entry point that delegates to CLAUDE.md and prompts/
```

## Workflows

This project runs in **Claude Code**. Workflows are invoked as slash commands — type `/` followed by the command name in the Claude Code chat, e.g. `/ingest-first`.

| Prompt | Slash Command | Purpose |
|--------|---------------|---------|
| `p1-first-ingest.md` | `/ingest-first` | Compile the wiki from scratch using all files in `raw/` |
| `p2-incremental-ingest.md` | `/ingest-increm` | Add only new files in `raw/` that haven't been processed yet |
| `p3-qa.md` | `/qa` | Answer a one-off question and save the result directly to `wiki/queries/` |
| `p3a-session-qa.md` | `/session-qa` | Ask a question inside a live session — auto-starts the session if none is active; full prior conversation is in context for each follow-up |
| `p3b-session-close.md` | `/session-close` | End the session — saves worthy Q&A turns to `wiki/queries/`, archives the session log, and cleans up |
| `p3c-session-reopen.md` | `/session-reopen` | Restore a closed session from archive back to `current.md` to continue it |
| `p4a-post-ingest.md` | `/post-ingest` | Post-ingest housekeeping — canonicalize tags, check backlinks, refresh MOCs; run after every `/ingest-increm` |
| `p4b-contradiction-check.md` | `/contradiction-check` | Scan wiki articles for contradictions |
| `p4c-deep-check.md` | `/deep-check` | Monthly content quality check — thin/missing articles, missing aliases, new article candidates |
| `p4d-triage-queries.md` | `/triage-queries` | Interactive triage of misplaced files in `wiki/queries/` root |
| `translation-backfill.md` | `/translation-backfill` | Repair missing Traditional Chinese medical-term translations in existing wiki content (see [Backfilling best practice](#backfilling-translations-best-practice)) |
| `p4-lint.md` | `/lint` | Full quarterly health check — all tasks above plus a written report to `wiki/maintenance/` |
| `p5-slides.md` | `/slides` | Generate a Marp slide deck on a topic from wiki content |
| `p6-weekly-synthesis.md` | `/synthesis` | Summarize what was added to the wiki this week |
| `sync-to-public.md` | `/sync-to-public` | **Maintainer only.** Copy public files (prompts, commands, templates) to the companion public repo and suggest a commit message. Not needed if you are a user who cloned this repo. |

### Backfilling translations (best practice)

The patient is a native Traditional Chinese reader, so clinical vocabulary is
glossed inline (`atherosclerosis (動脈粥狀硬化)`). The rules for *what* to translate
live in `CLAUDE.md` (single source of truth); this note covers *how to scope* a
backfill pass over already-existing articles.

- **Prefer domain-sized batches, not file-by-file.** Pass a whole domain/MOC as the
  scope (e.g. `/translation-backfill moc-imaging-finding`) rather than one concept
  at a time. A MOC is used as a **manifest**: the workflow expands its `[[links]]`
  into the member concept and summary files, runs the checker over the whole set,
  and edits each. Batching keeps the same term translated consistently across
  sibling files (the glossary is loaded once and reused), and syncs `wiki/index.md`
  and the MOC prose in the same pass.
- **A MOC scope does not recurse outward.** Only the concept/summary members listed
  in that MOC are pulled in. A `[[link]]` pointing to an article in a *different*
  domain is not followed — that article is covered when you run its own domain.
- **Order by glossary coverage.** Do domains where the glossary is already warm
  first (cleaner passes, fewer new guesses), then move to sparser domains.
- **The checkers are a floor, not a ceiling.** `scripts/check-bilingual-terms.py`
  only flags terms already in the glossary dictionary — a missing first-mention
  translation, or a `(2nd)` suffix when a term recurs within one counting unit
  (the innermost heading section; for `wiki/index.md` a Compilation Summary
  paragraph or a `## {file}.md` entry block) but carries fewer than the two
  translations the policy requires (`[[backlinks]]` never count as occurrences;
  query files are exempt from this within-unit rule). Meanwhile
  `scripts/extract-term-candidates.py` surfaces pattern-detectable candidates
  (acronyms and `Phrase (ACRONYM)` definitions) that are *not* yet in the glossary
  — but neither can catch lowercase multi-word terms. The edit itself runs a
  **two-pass find**: Pass A enumerates every candidate (from the extractor worklist
  plus terms only a human/LLM reading the prose would notice), Pass B dispositions
  each one. Finish with a whole-file gate — rerun `check-bilingual-terms.py` plus a
  `--git-diff` QA pass, and `check-medication-first-mentions.py` and
  `check-glossary-delta.py` on the edited files.
- **Every clinical term is translated inline; glossary additions are selective.**
  These are two separate actions when the agent meets a new term. It is always
  glossed inline (`atherosclerosis (動脈粥狀硬化)`). It is added to
  `memory/medical-term-translations.md` only when it is *standalone and reusable*
  (analyte/lab names, anatomy, pathology, procedures, enzymes, abbreviation full
  forms, ratio names) per the "What belongs in the glossary" criterion in
  `CLAUDE.md`; a one-off phrase tied to a single sentence gets its inline Chinese
  and nothing more. If unsure of the correct Taiwan wording, add it for later
  review rather than guessing. This is *why* the checker is only a floor — the
  glossary deliberately does not contain every translatable phrase.
- **Sub-batch large MOCs.** Files are translated one-by-one, and a single pass stays
  reliable only up to ~8–12 files before the context window fills. The big MOCs
  (`moc-cardiology` ~38, `moc-screening` ~29, `moc-metabolic` ~27, `moc-lipid` ~23,
  `moc-imaging-finding` ~20) should be split into 3–4 passes of ~10 files, each with
  its own `--git-diff` QA and commit so it is self-contained and resumable. MOCs with
  ≤ ~10 members are fine to do whole in one pass.
- **Scoping a sub-batch — three ways, no need to hand-list paths.** The scope after
  `/translation-backfill` is free text:
  - explicit paths — `/translation-backfill wiki/concepts/a.md wiki/concepts/b.md …`
  - a description — `/translation-backfill first 10 concept files in moc-cardiology`
  - by suspect count — `/translation-backfill moc-cardiology — do the ~10 files with
    the most bilingual gaps first` (the checker ranks members; worst offenders first)

  However the scope is expressed, the resolved file list is reported for approval
  before any file is edited.

## Getting Started

### Claude Code

1. Open a terminal in this directory and start Claude Code:
   ```
   claude
   ```
2. Drop source documents into `raw/`.
3. Run `/ingest-first` to build the wiki from scratch, or `/ingest-increm` to add only new files.
4. After each `/ingest-increm`, run `/post-ingest` to canonicalize tags, check backlinks, and refresh MOCs.
5. Use `/qa` to ask a one-off question. The result is saved immediately to `wiki/queries/`.
6. For a conversational session with follow-up questions:
   - Run `/session-qa your question` — the session starts automatically on the first question.
   - Keep asking follow-ups with `/session-qa your next question`; each turn appends a compact summary to `wiki/sessions/log.md` (read for context on the next turn) and the full answer to `wiki/sessions/current.md` (used only when the session closes).
   - When done, run `/session-close` — it saves substantive Q&A turns to `wiki/queries/`, archives both session files to `wiki/sessions/archive/` (as `YYYY-MM-DD-{topic-slug}.md` + `YYYY-MM-DD-{topic-slug}-log.md`), and removes both `current.md` and `log.md`.
7. Run `/deep-check` monthly for content quality (thin articles, missing aliases, coverage gaps).
8. Run `/triage-queries` as needed to move misplaced files out of `wiki/queries/` root.
9. Run `/lint` quarterly for a full health check with a written maintenance report.
10. Use `/slides` to generate a Marp presentation on any topic covered in the wiki.

### Codex

Codex can work in the same repository using `AGENTS.md`, which points it to the
shared conventions in `CLAUDE.md`, shared memory in `memory/`, and workflow
prompts in `prompts/`.

Codex does not use the Claude Code slash-command wrappers in `.claude/commands/`
directly. To run the same workflow in Codex, ask it to read and execute the
corresponding prompt file, for example:

```
Read and execute prompts/p2-incremental-ingest.md
```

Reusable workflows are also available as repo-scoped Codex skills with names
matching the Claude slash commands:

| Claude Code | Codex |
|-------------|-------|
| `/ingest-first` | `$ingest-first` |
| `/ingest-increm` | `$ingest-increm` |
| `/post-ingest` | `$post-ingest` |
| `/qa` | `$qa` |
| `/session-qa` | `$session-qa` |
| `/session-close` | `$session-close` |
| `/session-reopen` | `$session-reopen` |
| `/contradiction-check` | `$contradiction-check` |
| `/deep-check` | `$deep-check` |
| `/triage-queries` | `$triage-queries` |
| `/translation-backfill` | `$translation-backfill` |
| `/lint` | `$lint` |
| `/slides` | `$slides` |
| `/synthesis` | `$synthesis` |
| `/sync-to-public` | `$sync-to-public` |
| `/commit-push` | `$commit-push-codex` |

`$commit-push-codex` mirrors `/commit-push` but uses a Codex-specific
`Co-Authored-By: Codex <noreply@openai.com>` trailer.

All durable project changes should stay in the shared repo paths (`wiki/`,
`prompts/`, `scripts/`, `memory/`) so switching between Claude Code and Codex
keeps changes synchronized through git.

## Conventions

- All cross-references use Obsidian-style backlinks: `[[article-name]]` (filename without `.md`).
- Article formats (concept, summary, query, MOC) are defined in `CLAUDE.md` (auto-loaded by Claude Code; also human-readable).
- Never edit files in `raw/` — they are the source of truth.
- `wiki/index.md` is the entry point for browsing all content.

## Tagging System

All concept and summary files use a **closed set of 24 canonical tags**. New tags require explicit justification (no existing tag fits, 2+ articles would use it).

**Clinical domain tags** — each has a corresponding MOC file in `wiki/mocs/`:

| Group | Tags |
|---|---|
| Labs & biomarkers | `biomarker`, `hematology`, `immunology` |
| Metabolic / endocrine | `metabolic`, `glycemic`, `lipid` |
| Cardiovascular | `cardiology` |
| Organ systems | `hepatic`, `genitourinary`, `gastrointestinal`, `respiratory` |
| Musculoskeletal & neuro | `musculoskeletal`, `neurology` |
| Integumentary & sleep | `dermatology`, `sleep-medicine` |
| Sexual health | `sexual-health` |

**Cross-cutting tags** (no dedicated MOC):
`screening` · `imaging-finding` · `clinical-finding` · `medication` · `procedure`

**Imaging modality tags** (summaries only, used alongside `imaging-finding`):
`ultrasound` · `mri` · `ct`

Non-canonical synonyms (e.g. `cardiovascular`, `lab-test`, `renal`) are mapped to their canonical equivalents in `CLAUDE.md` and must never appear in frontmatter.

### What happens if a non-medical document is ingested?

Non-medical documents (financial records, recipes, book notes, etc.) have no applicable canonical tags, so Claude would either silently misfit them into medical tags or invent new ones — both corrupting the taxonomy. The article would also lack the clinical context that makes concept articles and MOCs useful. The correct action is to reject non-medical files at ingest time and direct them to a separate wiki.

## Git Setup

To put this folder under version control:

1. Open a terminal in this folder and initialize a git repository:
   ```
   git init
   ```
2. Create a `.gitignore` to exclude files you don't want tracked (optional but recommended). This repo's `.gitignore` covers OS, Python, and Obsidian cruft:
   ```
   # macOS
   .DS_Store
   .AppleDouble
   .LSOverride

   # Python
   __pycache__/
   *.pyc

   # Obsidian
   .obsidian/
   ```
3. Stage all files and make the initial commit:
   ```
   git add .
   git commit -m "Initial commit"
   ```
4. To back it up to a remote (e.g. GitHub), create a new repository on GitHub, then:
   ```
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git branch -M main
   git push -u origin main
   ```
5. After that, commit changes as usual:
   ```
   git add .
   git commit -m "your message"
   git push
   ```

## License

MIT License
