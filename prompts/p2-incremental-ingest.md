Your task is to incrementally update the wiki with any new 
source documents added to raw/.

1. Read wiki/processed.log to get the list of already 
   processed files.

2. List all files currently in raw/.

3. Identify which files in raw/ do not appear in 
   wiki/processed.log. These are the new files to process.

4. If there are no new files, report that the wiki is 
   up to date and stop.

5. Before processing new files, read `memory/medical-term-translations.md`.
   Reuse existing Traditional Chinese translations from this glossary whenever
   a matching English medical term appears in summaries or concepts.

6. For each new file, do the following in order:
   a. Read the full contents of the file.
      For image files (.png, .jpg, .jpeg): read the file visually and extract
      chart titles, axes, time ranges, key data series, notable trends,
      anomalies, and specific values. Treat this extracted information as the
      "contents" for the rest of the pipeline.
   b. Create wiki/summaries/{filename}.md following the 
      summary format in CLAUDE.md.
      Add Traditional Chinese translations following the Traditional Chinese
      Medical Terms policy in CLAUDE.md (single source of truth). Find terms with
      the two-pass procedure (Pass A / Pass B) in
      `prompts/translation-backfill.md` step 5: seed a per-file candidate worklist
      with `python3 scripts/extract-term-candidates.py FILE`, add the lowercase
      and multi-word terms it cannot detect by reading every paragraph, bullet,
      table note, impression line, and open-question line, then disposition each
      candidate so no in-scope term is left English-only on first mention.
   c. For each key concept extracted:
      - If wiki/concepts/{concept}.md does not exist, create it
        following the concept article format in CLAUDE.md.
      - If it exists, read it and integrate new information
        without erasing existing content. If missing an `aliases`
        field, add one.
      - For every created or updated concept, add Traditional Chinese
        translations per the Traditional Chinese Medical Terms policy in
        CLAUDE.md, and add useful Chinese terms to `aliases`.
      - Apply the same two-pass find as step b (seed with
        `extract-term-candidates.py`, add the terms it cannot detect,
        disposition each) before finishing the concept; do not stop after the
        first term in a paragraph.
   d. Use only canonical tags (see CLAUDE.md). If no existing tag fits,
      follow the "Adding a new canonical tag" procedure in CLAUDE.md
      before using it in any file.

   e. Append the filename to wiki/processed.log.
   f. Add or update the relevant entries in wiki/index.md.
      Place each entry under the domain section matching the
      article's primary domain tag (first clinical-domain tag
      in its frontmatter). Cross-cutting-only articles go under
      the most relevant domain section. Follow the index entry
      format in CLAUDE.md.
   g. For each canonical, non-cross-cutting tag on the new article:
      - MOC exists → add article to its Concepts or Source Summaries section.
      - No MOC, 3+ articles share tag → create MOC (MOC File Format in
        CLAUDE.md); add a row to home.md Maps of Content; remove its row
        from home.md Tags Without a MOC.
      - No MOC, <3 articles → add/update the tag's row in home.md
        Tags Without a MOC (following Home Page Format in CLAUDE.md).

7. Report a summary of everything you created or modified.
   Before reporting, run
   `python3 scripts/check-bilingual-terms.py --git-diff PATH [PATH ...]`
   on every summary, concept, MOC, `wiki/index.md`, and `wiki/home.md` file
   touched by this ingest. Treat the output as a floor, not a ceiling — the
   checker misses many translatable terms; patch real misses, and rerun until
   no unreviewed high-confidence suspects remain. Then run one whole-file pass
   (no --git-diff) over the same files as the final gate,
   `python3 scripts/check-bilingual-terms.py PATH [PATH ...]`, to catch
   in-glossary terms left untranslated on untouched lines that --git-diff hides.
   Then run
   `python3 scripts/check-glossary-delta.py --git-diff PATH [PATH ...]` on
   the same touched files, review each reported inline `English (中文)` pair,
   add reusable standalone clinical terms to
   `memory/medical-term-translations.md`, leave one-off phrases inline only,
   and rerun until no unreviewed reusable glossary candidates remain.
   Finally, run
   `python3 scripts/check-medication-first-mentions.py --git-diff PATH [PATH ...]`
   on the same touched files to verify the repo-wide medication first-mention
   format `generic (Brand, Taiwan name)` (see the Medication naming rule in
   CLAUDE.md), patch any flagged first mention, and rerun until no unreviewed
   suspects remain.
