Your task is to compile the wiki from scratch using all documents 
currently in raw/.

For each file in raw/, do the following in order:

1. Read the full contents of the file.
   For image files (.png, .jpg, .jpeg): read the file visually and extract
   chart titles, axes, time ranges, key data series, notable trends,
   anomalies, and specific values. Treat this extracted information as the
   "contents" for the rest of the pipeline.

2. Read `memory/medical-term-translations.md` before writing any summary or
   concept content. Reuse existing Traditional Chinese translations from this
   glossary whenever a matching English medical term appears.

3. Create wiki/summaries/{filename}.md following the summary
   format in CLAUDE.md. Extract all key concepts and 
   write backlinks to any related concepts you identify.
   Add Traditional Chinese translations following the Traditional Chinese Medical
   Terms policy in CLAUDE.md (single source of truth). Find terms with the
   two-pass procedure (Pass A / Pass B) in `prompts/translation-backfill.md`
   step 5: seed a per-file candidate worklist with
   `python3 scripts/extract-term-candidates.py FILE`, add the lowercase and
   multi-word terms it cannot detect by reading every paragraph, bullet, table
   note, impression line, and open-question line, then disposition each candidate
   so no in-scope term is left English-only on first mention.

4. For each key concept you extracted:
   a. Check if wiki/concepts/{concept-name}.md already exists.
   b. If it does not exist, create it following the concept
      article format in CLAUDE.md. If the concept is a medication,
      it MUST carry the `brand` and `taiwan-brand-name` fields and
      the Chinese brand name in `aliases` (see Medication concepts
      in CLAUDE.md) — `check-medication-first-mentions.py`, the final
      gate below, silently skips any medication concept missing them.
   c. If it already exists, read it and integrate new information
      without erasing existing content. If missing an `aliases`
      or `cn-title` field, add one (see Frontmatter aliases and
      `cn-title` in CLAUDE.md). Keep patient test-data values in a Markdown
      table — one row per measurement, even a single value in a
      one-row table — never a bulleted list (see Key Details in
      CLAUDE.md).
   d. For every created or updated concept, add Traditional Chinese
      translations per the Traditional Chinese Medical Terms policy in CLAUDE.md,
      and add useful Chinese terms to `aliases`. Apply the same two-pass find as
      step 3 (seed with `extract-term-candidates.py`, add the terms it cannot
      detect, disposition each); do not stop after the first term in a paragraph.

5. Use only canonical tags (see CLAUDE.md) on all files created
   in steps 3 and 4. If no existing tag fits, follow the
   "Adding a new canonical tag" procedure in CLAUDE.md before
   using it in any file.

6. Append the filename to wiki/processed.log on a new line.

7. Add an entry for each new or updated wiki file to
   wiki/index.md. Place the entry under the domain section 
   matching the article's primary domain tag (first clinical-
   domain tag in its frontmatter). Cross-cutting-only articles 
   go under the most relevant domain section. Follow the index 
   entry format in CLAUDE.md.

After processing all files, do a final pass:
- Add cross-concept backlinks where missing.
- For each canonical, non-cross-cutting tag that now has 3+
  articles and no MOC file, create a MOC following the MOC File
  Format in CLAUDE.md.
- Write a one-paragraph compilation summary at the top of wiki/index.md
  describing what the wiki now covers.
- Build wiki/home.md from scratch following the Home Page Format in CLAUDE.md.
- Run `python3 scripts/check-bilingual-terms.py --git-diff PATH [PATH ...]`
  on every summary, concept, MOC, `wiki/index.md`, and `wiki/home.md` file
  touched by this ingest. Treat the output as a floor, not a ceiling — the
  checker misses many translatable terms; patch real misses, and rerun until
  no unreviewed high-confidence suspects remain. Then run one whole-file pass
  (no --git-diff) over the same files as the final gate:
  `python3 scripts/check-bilingual-terms.py PATH [PATH ...]` — it catches
  in-glossary terms left untranslated on untouched lines that --git-diff hides;
  confirm the remaining hits are only known intentional exceptions.
- Run `python3 scripts/check-glossary-delta.py --git-diff PATH [PATH ...]`
  on those same touched files. Review each reported inline `English (中文)`
  pair, add reusable standalone clinical terms to
  `memory/medical-term-translations.md`, leave one-off phrases inline only,
  and rerun until no unreviewed reusable glossary candidates remain.
- Run `python3 scripts/check-medication-first-mentions.py --git-diff PATH [PATH ...]`
  on those same touched files to verify the repo-wide medication first-mention
  format `generic (Brand, Taiwan name)` (see the Medication naming rule in
  CLAUDE.md). Patch any flagged first mention and rerun until no unreviewed
  suspects remain.
