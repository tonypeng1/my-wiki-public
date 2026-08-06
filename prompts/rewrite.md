# Rewrite Existing Medical Documents

Rewrite one or more existing medical documents in natural, patient-friendly language for an adult reader with little medical knowledge.

## Select the targets

Treat the text supplied after this prompt as the target specification. Accept all of the following:

- One file path, such as `wiki/concepts/hemoglobin-a1c.md`.
- Multiple file paths, separated by spaces; paths containing spaces may be quoted.
- One or more directory paths. A directory selects all readable text or Markdown documents directly inside it.
- Glob patterns, such as `wiki/concepts/*.md` or `wiki/queries/2026-*.md`.
- `--recursive` or `-r` together with a directory, which selects eligible files in that directory and all nested directories.
- Recursive glob patterns, such as `wiki/**/*.md`, which include nested directories without needing `--recursive`.

Resolve relative paths from the repository root. Preserve the user's argument order, expand directory and glob matches in stable alphabetical order, and remove duplicates. Do not silently broaden a target: if a path does not exist, a glob matches nothing, or a directory contains no eligible documents, report that target and continue only when other targets were resolved.

Use readable text and Markdown documents, including files with extensions such as `.md`, `.markdown`, `.mdx`, `.txt`, `.text`, `.rst`, `.csv`, and `.tsv`. Do not interpret binary files as text. Report unsupported binary targets, such as PDFs, images, audio, or office files, and ask the user to use an appropriate document workflow if they need those rewritten. Ignore hidden files and hidden directories unless the user names a hidden file explicitly.

If no target is supplied, ask the user to provide one or more file paths, directories, or glob patterns. Before rewriting, report the resolved target list when it contains more than one file or when directory/glob expansion was used.

## Task

Read each resolved document in full and rewrite it while preserving every fact, medical concept, number, date, measurement, unit, comparison, finding, qualification, uncertainty, negation, and intended meaning. Do not add information, medical advice, diagnoses, interpretations, or conclusions that are not supported by the supplied text. Provide any analysis, interpretation, or conclusion that is directly supported by the supplied information and relevant to the task, stating it with the appropriate level of uncertainty. Keep approximately the same level of detail and length.

If multiple documents are selected, rewrite each one separately in the resolved order. Preserve document boundaries and identify each rewritten result by its source path. Do not merge facts from different documents or make one document appear to support another.

For each resolved target, print the rewritten document first, then automatically save that exact rewritten content back to its original path. Treat selecting a target as authorization to replace it in place; do not wait for a separate save request or confirmation. Preserve each original path and apply the final quality check before writing. If a write fails, report the source path and error without silently substituting another path.

## Writing rules

- Rewrite difficult sentences themselves instead of keeping difficult words and explaining them afterward.
- Prefer familiar words over formal or abstract words.
- Use short, natural sentences with one main idea each.
- Prefer active, direct wording and concrete descriptions of what happens in the body.
- Keep medically important names when accuracy requires them, including diagnoses, tests, hormones, anatomy, enzymes, medications, abbreviations, and measured values.
- Make the role and meaning of each necessary medical term clear from the sentence around it rather than adding a dictionary-style definition afterward.
- Keep the original tone appropriately cautious. Do not sound childish, overly casual, or reassuring without evidence.
- Make clear what a result does and does not show.

Use direct replacements where they improve clarity, for example:

- “excess thyroid hormone” → “too much thyroid hormone”
- “suppress” → “reduce the activity of”
- “undetectable, meaning the test could not detect it” → “too low for the test to detect”
- “incidental” → “found by chance and possibly unrelated”
- “low-normal” → “within the normal range but near the lower end”

## Preserve medical meaning

Do not strengthen or weaken any conclusion:

- “may” or “can” must not become “does” or “will.”
- “evidence against” must not become “rules out.”
- “possible” must not become “confirmed.”
- “within the reference range” must not become “healthy” or “normal overall.”
- “not tested” must not become “normal.”
- “not detected” must not become proof that a disease is absent.

Preserve and clearly communicate diagnoses, advice, causes, consequences, and interpretations that are already present in the source. Provide any additional analysis, interpretation, or conclusion that is directly supported by the supplied information and relevant to the task, stating it with the appropriate level of uncertainty. Do not remove a supported conclusion merely because it is medically consequential, but do not invent, extend, or make any conclusion stronger than the supplied information supports.

## Preserve document structure

If a source uses Markdown, preserve its frontmatter, headings, tables, list structure, links, link targets, filenames, values, and overall organization. Preserve existing Chinese translations and follow the Chinese Medical Terms policy in `CLAUDE.md` when rewriting wiki content in a Chinese-locale vault. Do not invent translations or change locale-specific wording. For non-wiki documents, preserve their existing language unless the user explicitly asks for translation. Do not change source quotations.

## Silent quality check

Before responding, silently compare every rewrite with its source:

1. Confirm that every fact, value, date, unit, comparison, negative finding, limitation, and qualification is still present.
2. Confirm that no uncertainty has become certainty and no conclusion has become stronger or weaker.
3. Confirm that no diagnosis, advice, cause, consequence, interpretation, or outside fact was added.
4. Replace any remaining unnecessarily difficult wording with a clear, natural sentence.

Return the rewritten document or documents, with source-path labels when needed to distinguish multiple outputs, and report the path or paths saved. Do not add an explanation unless the user asks for one.

## Translation audit after saved wiki rewrites

After the rewrite is automatically saved, run the translation-backfill workflow on exactly the saved wiki files when all of these conditions are true:

- at least one saved target is under `wiki/`; and
- `locale` in `wiki-config.yml` is `zh-TW` or `zh-CN`.

Read and execute `prompts/translation-backfill.md` with the saved files as its explicit scope. Let that workflow perform its normal glossary, translation, medication-format, mirror-file, and structural QA. Do not run this follow-up for files outside `wiki/` or a vault with `locale: none`.

## Mirror synchronization after saved wiki rewrites

An article's one-line description is repeated in its `## {file}.md` block in `wiki/index.md` and in the MOC bullet for each of its domains. A rewrite changes the article's wording and nothing carries that across on its own, so the mirrors are left describing the article in wording it no longer uses.

Run this for every saved target under `wiki/`, **whatever the locale**. Mirror wording is language-independent, so this must not be conditional on the translation audit above: that audit does not run under `locale: none`, and routing the mirror work through it would leave an English-only vault with no mirror step at all.

Run it after the translation audit when that audit applies. In a Chinese-locale vault the backfill's step 6 has already synchronized the mirrors, so this returns clean and costs one command; under `locale: none` it is the only step that does the work.

- `python3 scripts/check-mirror-drift.py --git-diff PATH [PATH ...]`

For each flagged article, edit the named `wiki/index.md` entry block and the named MOC bullet so they describe the article in its new wording. Edit those lines only — never rewrite a whole mirror file: `wiki/index.md` carries an append-only, ingest-owned `## Compilation Summary` block, and MOC `## Key Relationships` prose has its own one-paragraph contract. Preserve every value, unit, flag, and link target already in the mirror line; plain-English rewording never touches the digits. Rerun until clean, or state which flagged mirror legitimately needed no change and why.

Name the mirror files you updated when reporting the saved paths, even when the answer is "none needed". The check is satisfied by any edit to the mirror, so it proves the mirror was touched, not that it was synchronized correctly.
