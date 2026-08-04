---
name: rewrite
description: Rewrite one or more existing medical documents in clear, patient-friendly language while preserving every fact, qualification, uncertainty, medical term, Markdown structure, and link. Use when the user asks to paraphrase, simplify, or rewrite files, multiple files, directories, or glob-selected documents without changing their medical meaning.
---

# Rewrite

Run the repository workflow defined in `prompts/rewrite.md`.

Before acting, read `AGENTS.md`, `CLAUDE.md`, `memory/MEMORY.md`, any relevant
memory files it references, and `prompts/rewrite.md` in full.

Use the user's target arguments to select the source documents. Accept one or
more file paths, directories, glob patterns, and `--recursive`/`-r` directory
selection as described in the prompt. Resolve relative paths from the
repository root, preserve argument order, expand matches alphabetically, and
deduplicate them.

Execute the prompt exactly:

- Read every resolved target fully before rewriting.
- Preserve every fact, value, date, unit, finding, limitation, qualification,
  uncertainty, negation, medical term, link target, and intended meaning.
- Rewrite difficult wording directly into familiar language instead of adding
  dictionary-style definitions afterward.
- Do not add outside facts, diagnoses, advice, interpretations, reassurance, or
  stronger conclusions.
- Preserve Markdown frontmatter, headings, tables, lists, links, filenames,
  values, document boundaries, and source paths unless the user explicitly
  asks for a structural change.
- Do not modify source files unless the user explicitly requests saved changes.
- Return only the rewritten document or documents unless the user asks for an
  explanation.

After saving rewritten files, if the saved targets include files under `wiki/`
and `wiki-config.yml` uses `locale: zh-TW` or `locale: zh-CN`, run the
translation-backfill workflow on exactly those saved files as its explicit
scope. Skip that follow-up for output-only rewrites, non-wiki files, and
`locale: none`. Follow `prompts/translation-backfill.md` exactly; it performs
the Chinese translation, glossary, medication-format, mirror-file, and
structural QA passes.
