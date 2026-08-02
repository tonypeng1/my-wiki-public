Your task is to ingest any source documents in raw/ that the wiki has not
processed yet.

This is the only ingest workflow. It covers both the first run on an empty vault
and every run afterwards, because the two are the same operation: the selection
rule below is "files in raw/ that are absent from wiki/processed.log", and on a
fresh vault that set is simply every file in raw/. There is no full-rebuild mode
and no flag that re-processes logged files — a file listed in wiki/processed.log
is never processed again.

0. LOCALE GATE — run this before anything else, including reading raw/.
   Run: python3 scripts/check-locale-consistency.py

   The vault's locale decides whether this ingest writes Chinese glosses and
   which Chinese. It has to be settled before the first file is written,
   because ingest writes summaries, concepts, MOCs and wiki/index.md in a
   single pass: a run under the wrong locale is not a setting to flip
   afterwards, it is every file the run touched re-glossed by hand.

   - Exit 0 → proceed to step 1. On a vault that already matches its config
     this is the only outcome, and it costs one command.
   - `LOCALE CONFIG INVALID` → `wiki-config.yml` is missing, malformed, or
     inconsistent. **STOP before writing anything.** Show the error, then ask
     which locale this vault should use:
       - `zh-TW` — Traditional Chinese glosses, Taiwan clinical wording
       - `zh-CN` — Simplified Chinese glosses, Mainland clinical wording
       - `none`  — English only, no glosses
     Do not guess, and do not fall back to a default: a silent default is
     exactly the failure this gate exists to prevent. Write the answer to
     `wiki-config.yml` (a Chinese locale also needs a `glossary:` path),
     rerun the checker, and proceed only once it exits 0.
   - `MISMATCH` → the configured locale and the prose already in the vault
     disagree, which usually means someone changed `locale` on a populated
     vault. **STOP and report it.** Deciding whether to change the config
     back or re-gloss the vault is the maintainer's call, not something to
     work around by ingesting on top of it.

1. Read wiki/processed.log to get the list of already processed files.
   If the file does not exist, treat the list as empty.

2. List all files currently in raw/.

3. Identify which files in raw/ do not appear in
   wiki/processed.log. These are the new files to process.

4. If there are no new files, report that the wiki is
   up to date and stop.

5. Before processing new files, read the glossary named under `glossary:` in
   `wiki-config.yml` — step 0 already established that the locale and glossary
   are valid. Reuse existing translations from that glossary whenever a
   matching English medical term appears in summaries or concepts. Which
   Chinese to write is the locale's decision, not this workflow's — see the
   Chinese Medical Terms section in CLAUDE.md.

   Under `locale: none` there is no glossary and this vault writes no glosses:
   skip this step, and skip every translation instruction below. Everything
   else in this workflow is unchanged.

6. For each new file, do the following in order:
   a. Read the full contents of the file.
      For image files (.png, .jpg, .jpeg): read the file visually and extract
      chart titles, axes, time ranges, key data series, notable trends,
      anomalies, and specific values. Treat this extracted information as the
      "contents" for the rest of the pipeline.
   b. Create wiki/summaries/{filename}.md following the 
      summary format in CLAUDE.md.
      Set the three provenance fields — `facility`, `physician`,
      `result-status` — from the source document, using only the closed
      vocabularies in `memory/provenance-roster.md`, per the rules under
      "Provenance fields" in CLAUDE.md. Three rules decide
      the hard cases:
      - `facility` is the site that PERFORMED the study, not the one that
        ordered it. A clinic that draws a specimen an outside reference lab
        runs is the `physician` side of the pair, not the facility.
      - `result-status` judges the document, not the number: a panel with
        some values flagged and some not is `mixed`, not `abnormal`.
      - Omit a field rather than guess it. A source that never names its
        performing site gets no `facility` line; do not infer one from the
        letterhead of the ordering clinic. A document reporting no test
        result (a medication list) gets no `result-status`.
      If the document names a site or clinician not in the vocabulary, add
      the row to `memory/provenance-roster.md` before using the slug — that
      is the whole edit, since both checkers parse the roster at run time and
      hold no copy of it. A slug used before it is listed is
      indistinguishable from a typo and fails /lint.
      Add Chinese translations following the Chinese Medical Terms policy in
      CLAUDE.md (single source of truth; skipped under `locale: none`). Find terms with
      the two-pass procedure (Pass A / Pass B) in
      `prompts/translation-backfill.md` step 5: seed a per-file candidate worklist
      with `python3 scripts/extract-term-candidates.py FILE`, add the lowercase
      and multi-word terms it cannot detect by reading every paragraph, bullet,
      table note, impression line, and open-question line, then disposition each
      candidate so no in-scope term is left English-only on first mention.
   c. For each key concept extracted:
      - If wiki/concepts/{concept}.md does not exist, create it
        following the concept article format in CLAUDE.md. If the concept
        is a medication, it MUST carry the `brand` and `local-brand-name`
        fields and the Chinese brand name in `aliases` (see Medication
        concepts in CLAUDE.md) — `check-medication-first-mentions.py`, the
        final gate in step 8, silently skips any medication concept
        missing them.
      - If it exists, read it and integrate new information
        without erasing existing content. If missing an `aliases`
        or `cn-title` field, add one (see Frontmatter aliases and
        `cn-title` in CLAUDE.md). Keep patient test-data values in a Markdown
        table — one row per measurement, even a single value in a
        one-row table — never a bulleted list (see Key Details in
        CLAUDE.md).
      - For every created or updated concept, add Chinese translations per
        the Chinese Medical Terms policy in CLAUDE.md, and add useful Chinese
        terms to `aliases`.
      - Apply the same two-pass find as step b (seed with
        `extract-term-candidates.py`, add the terms it cannot detect,
        disposition each) before finishing the concept; do not stop after the
        first term in a paragraph.
      - Backlink targets must resolve to a real file. When you reference a
        clinical **domain** (a canonical domain tag such as `hepatic`,
        `musculoskeletal`, `cardiology`), link to that domain's MOC —
        `[[moc-<domain>]]`, never the bare `[[<domain>]]`, which matches no
        file and leaves a dangling link. Every `[[name]]` you write — in
        concept prose, the Connections section, and the summary Backlinks
        section — must match an existing file basename (a concept, summary,
        MOC, or query file); never link a bare domain or tag name.
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

7. After the per-file loop, do these two finalization steps once. Each is
   conditional on whether the artifact already exists — not on whether this
   was a "first" ingest — so a vault missing one of them self-heals on the
   next run.

   a. wiki/home.md
      - Does not exist → build it from scratch following the Home Page Format
        in CLAUDE.md.
      - Exists → step 6g already updated its rows in place; leave the rest to
        the /post-ingest pass that follows this workflow.

   b. The `## Compilation Summary` section at the top of wiki/index.md.
      This workflow owns that section — no other prompt writes it.
      - Section missing or empty → write one paragraph describing what the
        wiki now covers, opening with the bold ingest date exactly as below.
        EVERY paragraph in this section carries one, the first included — an
        undated opening paragraph cannot be sorted or audited.
      - Otherwise → append exactly ONE new paragraph at the end of the
        section, opening with the bold ingest date: `**2026-07-27:**`. If an
        earlier paragraph in the section already carries today's date,
        disambiguate this one (`**2026-07-27 (second ingest):**`).

      The section runs oldest-first, so appending at the end is what keeps it
      in date order — do not insert a paragraph anywhere else, and do not
      reverse the section. `scripts/check-compilation-summary.py` audits this:
      it cross-references the section against the ingest history in git and
      reports ingests with no paragraph, paragraphs out of ascending order,
      undated paragraphs, and session Q&A content that does not belong here.

      Never rewrite, re-scope, or delete an existing paragraph, and never
      append sentences onto the end of one — every ingest gets its own
      paragraph. Two consumers depend on that: prompts/p3-qa.md reads this
      section one whole paragraph at a time, and CLAUDE.md makes the paragraph
      the translation counting unit for wiki/index.md.

      Keep the paragraph to 4–6 sentences: what was ingested, the headline
      finding, which concepts and MOCs were created or updated, and the
      resulting summary / concept / query counts. If a single ingest genuinely
      needs more, split it by topic into separate dated paragraphs rather than
      growing one long one.

8. Report a summary of everything you created or modified.
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
   add reusable standalone clinical terms to the glossary configured in `wiki-config.yml`,
   leave one-off phrases inline only,
   and rerun until no unreviewed reusable glossary candidates remain.
   Finally, run
   `python3 scripts/check-medication-first-mentions.py --git-diff PATH [PATH ...]`
   on the same touched files to verify the repo-wide medication first-mention
   format `generic (Brand, local name)` (see the Medication naming rule in
   CLAUDE.md), patch any flagged first mention, and rerun until no unreviewed
   suspects remain.
   Last, run
   `python3 scripts/check-unglossed-chinese.py --git-diff PATH [PATH ...]`
   on the same touched files. This is the mirror of the first check: Chinese
   left in prose with no English at all. It matters most when the source
   document in `raw/` was itself Chinese, because then the article had to be
   translated INTO English and any term that did not make the crossing is
   invisible to every other checker — they all key on the English half.
   Rewrite each real finding as `English (中文)`; if the finding is an
   institution, add its row to `memory/provenance-roster.md` instead, since
   roster names are suppressed by design.
