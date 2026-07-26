Perform a full health check on the wiki. Work through these 
checks in order:

1. Read wiki/index.md, all files in wiki/mocs/, and wiki/home.md.
   (Concept and summary files are loaded on-demand in later steps.)

2. MISSING AND THIN CONCEPT PAGES
   Two scripts, one list each:
   Run: python3 scripts/detect-thin.py
     → THIN: concept files with fewer than 150 words of body content.
   Run: python3 scripts/check-dangling-links.py
     → every `[[link]]` whose target basename matches no .md anywhere under
       wiki/. These are the MISSING candidates. This run is read-only and is
       for the candidate list; step 11 runs the same checker again as the
       closing gate, after the edits made here and in steps 3 and 6.

   Sort each dangling target before acting on it:
   - names a genuine clinical concept the wiki should hold → create the
     article (below)
   - a typo, or a clinical domain that should point at `[[moc-<domain>]]`
     → fix the link in the referencing file instead; do not create a file
       to satisfy a bad link

   For each file identified as THIN: read only that concept file.
   For each MISSING concept: search wiki/summaries/ for files whose
   title or tags are topically relevant, then read only those.

   For each article that is missing or thin:
   - If the summaries or other concept articles contain enough
     relevant information, create or expand the article directly
     using that material.
   - If no material is available, create a stub with an Overview
     section and a note marking it as a stub needing expansion.

   CANONICAL RECORD FORMAT
   Run: python3 scripts/detect-list-records.py
   This flags concept files whose recurring-measurement record is a bulleted
   list rather than a Markdown table. A series in that shape does not anchor the
   contradiction check (scripts/extract-claims.py): its rows are skipped as
   authority and get misattributed as restatements of neighboring concepts.
   For each file under LIST-FORMAT RECORDS, read it and convert the series to a
   table — one row per draw (date, lab, value, flag, source backlink) — per the
   Key Details rule in CLAUDE.md, preserving every value, flag, backlink, and
   Traditional Chinese gloss; do NOT change any data. For PARTIALLY TABULAR,
   fold the stray bullets into the existing table. Leave dated *events*
   (medication start/stop dates, diagnosis timelines) as prose — the checker
   already excludes them. The checker only catches *date-led* series; a single
   result value or one whose date sits in a header line is not auto-flagged —
   apply the same one-row-table rule from CLAUDE.md when you notice one. List
   each conversion in the health check report.

3. MISSING BACKLINKS
   Run: python3 scripts/connections-index.py
   This outputs each concept's title, tags, overview sentence, and existing
   Connections section — everything needed to spot missing links without
   loading full article bodies (~34 KB vs ~191 KB for full files).

   Look for concept articles that clearly relate to each other but do not
   yet link to each other. Only add a backlink where the connection is
   substantive — one concept directly informs understanding of the other.
   Skip incidental or tangential relationships.
   To add a backlink, read and edit only the specific concept files involved.

4. FRONTMATTER COMPLETENESS — aliases · cn-title · medication fields
   Run: grep -rL 'aliases:' wiki/concepts/ wiki/mocs/
   Run: grep -rL 'cn-title:' wiki/concepts/ wiki/mocs/
   Run: grep -l '^tags:.*medication' wiki/concepts/*.md | xargs -I{} grep -L '^brand:' {}
   Run: grep -l '^tags:.*medication' wiki/concepts/*.md | xargs -I{} grep -L '^taiwan-brand-name:' {}
   The first two list concept and MOC files with no aliases / no cn-title;
   the last two list medication concepts missing a brand field.
   Read only the files returned, then fill what is missing:
   - concept `aliases` — 3-5 common abbreviations, alternate spellings, and lay
     terms, including at least one Traditional Chinese name. On a medication the
     Chinese brand name must be among them, since it is not in `cn-title`.
   - MOC `aliases` — the Chinese domain name (e.g. `aliases: [血脂]`).
   - `cn-title` — `English (中文)` on a concept, `MOC — {Domain} ({中文})` on a MOC.
   - `brand` / `taiwan-brand-name` — take them from the article body or the source
     summary; never guess a Taiwan product name. If neither records it, report the
     gap instead of inventing a value. This matters because
     check-medication-first-mentions.py silently SKIPS any medication concept
     missing either field: the gap disables first-mention enforcement for that
     drug repo-wide and the checker still reports clean.
   All per CLAUDE.md ("Frontmatter aliases and `cn-title`", "Medication concepts").
   `aliases`/`cn-title` are search/display metadata — do NOT bump `updated` for them.
   List any medication field gaps in the health check report.

5. TAG CANONICALIZATION
   Run: python3 scripts/canonicalize-tags.py
   The script replaces all non-canonical tags with their canonical
   equivalents across wiki/concepts/ and wiki/summaries/, handles the
   imaging-modality special rule for summaries, and prints every file
   changed with a before→after diff. Include its output verbatim in
   the health check report. No file reads are needed for this step.

6. MOC FRESHNESS
   Run: python3 scripts/tag-index.py
   This outputs a compact listing of every concept and summary with its
   title/source, date, and tags — without loading 118 full files.

   Using the tag-index output and the MOC files already loaded in step 1:
   a) Verify that every concept and summary whose tags include a MOC domain
      is listed in that MOC. For any that are missing, add an entry with a
      one-line description. (Concept descriptions can draw on the first
      sentence already shown in the tag-index. For summaries, derive the
      description from the source filename and date.)
   b) Check: if a canonical tag now has 3+ articles (visible in the
      tag-index) but no MOC exists, and the tag is NOT listed under
      "Cross-cutting tags — no dedicated MOC" in CLAUDE.md, create the MOC
      following the MOC File Format in CLAUDE.md, then queue an entry for
      wiki/index.md (to be written in step 10).
   c) Using wiki/home.md loaded in step 1, verify it lists every MOC file
      in wiki/mocs/.

   UNCOVERED RECORDS SYNC
   Collect all home.md changes for this step — new/removed MOC table rows
   and the rebuilt Tags Without a MOC table — and apply them in a single
   write at the end of this step.
   For the Tags Without a MOC table: for every canonical tag (excluding
   cross-cutting tags listed under "Cross-cutting tags — no dedicated MOC"
   in CLAUDE.md) that has fewer than 3 articles (count from the tag-index)
   and has no MOC file, collect all articles carrying that tag. Rebuild
   the entire table in one pass, then write wiki/home.md once.
   Report all additions, removals, and new MOCs created.

7. MISPLACED QUERY FILES
   Read every file in wiki/queries/ root (not sub-folders) now.
   Flag any file that matches one or more of these signals:
   - filename contains "printable", "handoff", "draft", or "summary"
   - has no "## Answer" section (i.e. it is a methodology or procedure doc)
   - has a `status:` value other than `current` in its frontmatter
   - its `question:` frontmatter value covers the same topic as a
     newer file (by `date:`) already in wiki/queries/ root
     (flag the older file as a candidate for _superseded/)

   For each flagged file, state where it likely belongs and why, then
   ask me to confirm before moving anything:
   - a clean handoff / presentation document → wiki/deliverables/
   - an answer superseded by a newer file → wiki/queries/_superseded/
   (A file whose name contains "handoff" but is a genuine Q&A stays in
   wiki/queries/ root.)
   After I confirm:
   - Move the file to its destination
   - Strip the `status:` field from the moved file's frontmatter

8. NEW ARTICLE CANDIDATES
   Based on the connections-index from step 3 and the tag-index from
   step 6, identify 3-5 new concept articles that would meaningfully
   improve the wiki's coverage. For each, explain why it would be
   valuable and which existing articles would link to it.

9. Write a health check report to wiki/maintenance/health-check-{today's date}.md
   with sections: wiki state summary · missing concepts created · thin articles expanded
   · list-format records converted · backlinks added · dangling links fixed · missing frontmatter fields added (aliases, cn-title, medication brand fields) · misplaced queries moved · recommended new articles.

10. Using the in-memory wiki/index.md (already updated with any new MOC
    entries in step 6), append the health check report entry and write
    wiki/index.md once.

11. DANGLING BACKLINK CHECK
    Steps 2, 3, and 6 all write `[[links]]` — new articles, added Connections
    entries, new MOC rows — and any of them can point at a target that does
    not exist. Run the same checker step 2 used for its candidate list, now
    as the closing gate over everything this run wrote:
    `python3 scripts/check-dangling-links.py`
    With no path arguments this scans all authored content (concepts,
    summaries, MOCs, queries, wiki/index.md, wiki/home.md) — 3,600+ links
    across six surfaces, not just the concept bodies step 2 reads. A link is
    dangling when its target basename matches no .md file anywhere under
    wiki/ (Obsidian resolves `[[name]]` by basename across the vault, so
    concepts, summaries, MOCs, and query files are all valid targets).
    Fix each one:
    - a reference to a clinical domain → repoint to that domain's MOC,
      `[[moc-<domain>]]` (e.g. `[[hepatic]]` → `[[moc-hepatic]]`);
    - a typo or wrong target → correct the target;
    - a genuine concept that does not exist yet → create it per step 2, or
      say in the report why it was left.
    Rerun until no dangling links remain. Add a one-line result (links
    fixed, or "clean") to the health check report from step 9.

12. BILINGUAL, GLOSSARY, AND MEDICATION QA
    Every run of this workflow edits MOC files, wiki/home.md, and
    wiki/index.md, and step 2 may create or expand concept articles. That is
    new clinical prose, so it carries the same three risks ingest does, and
    p2-incremental-ingest.md step 7 runs the same three checkers on it. Run
    these LAST, after every edit above is written — including the link
    repairs in step 11 — so the diff they inspect is complete. All three take
    `--git-diff` with no path arguments: that covers the main content
    locations (concepts, summaries, MOCs, wiki/index.md, wiki/home.md),
    bounds output to the lines this run changed, and scans any new/untracked
    file — such as an article created in step 2 — in full.

    a) Run: python3 scripts/check-bilingual-terms.py --git-diff
       English clinical terms written without their Traditional Chinese
       translation, per the Traditional Chinese Medical Terms policy in
       CLAUDE.md. Treat the output as a heuristic suspect list — some
       suspects are known false positives (see
       memory/reference-bilingual-checker-behavior.md for the recurring
       patterns). Patch real misses in the files this workflow touched,
       editing only those files, then rerun until no unreviewed
       high-confidence suspects remain.

    b) Run: python3 scripts/check-glossary-delta.py --git-diff
       Inline `English (中文)` pairs this pass wrote that are not yet in
       memory/medical-term-translations.md. Review each and follow the "What
       belongs in the glossary" rule in CLAUDE.md: add standalone, reusable
       clinical vocabulary; leave one-off phrases inline only; add a term you
       are unsure of for later review rather than guessing. Rerun until no
       unreviewed reusable candidates remain.

    c) Run: python3 scripts/check-medication-first-mentions.py --git-diff
       The repo-wide `generic (Brand, Taiwan name)` format (Medication naming
       in CLAUDE.md) on first mention in each `###` section. Note the checker
       silently SKIPS any medication concept missing `brand` or
       `taiwan-brand-name`, so a clean result here does not prove those
       fields exist — step 4 is what guarantees that. Patch any flagged first
       mention and rerun until no unreviewed suspects remain.

    Append a one-line result for each of a, b, and c (terms patched, glossary
    entries added, first mentions fixed — or "clean") to the health check
    report from step 9.