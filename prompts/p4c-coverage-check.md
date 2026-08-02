Run this monthly to review content quality and coverage.
It complements p4a-post-ingest.md, which handles structural housekeeping
after each ingest, bounded to what that ingest changed.

This pass carries the repo-wide work — the judgment passes whose cost does not
shrink with a small ingest. Steps 2, 3, and 4 all read the same two indexes
(connections-index.py, tag-index.py), so load each once and reuse it: that is
the reason these steps live together rather than firing on every ingest.

1. MISSING AND THIN CONCEPT PAGES
   Two scripts, one list each:
   Run: python3 scripts/detect-thin.py
     → THIN: concept files with fewer than 150 words of body content.
   Run: python3 scripts/check-dangling-links.py
     → every `[[link]]` whose target basename matches no .md anywhere under
       wiki/. These are the MISSING candidates. The same checker runs
       per-ingest in p4a-post-ingest.md step 6, which repairs typos and
       domain references on the lines that ingest changed and deliberately
       leaves a link whose target is a genuine concept nobody has written —
       that leftover is what this step is for.

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

   Give every article you create `aliases` and `cn-title` per CLAUDE.md, so
   it does not come back as a gap in p4a-post-ingest.md step 3.

2. MISSING BACKLINKS
   Run: python3 scripts/connections-index.py
   This outputs each concept's title, tags, overview sentence, and existing
   Connections section — everything needed to spot missing links without
   loading full article bodies (~64 KB vs ~388 KB for full files). Keep the
   output; step 4 reads it again.

   Look for concept articles that clearly relate to each other but do not
   yet link to each other. Only add a backlink where the connection is
   substantive — one concept directly informs understanding of the other.
   Skip incidental or tangential relationships.
   To add a backlink, read and edit only the specific concept files involved.

   This is the repo-wide pass. p4a-post-ingest.md checks only the concepts
   each ingest touched; the full corpus review happens here, monthly, where
   the index it needs is already loaded for step 4. Include the articles
   created or expanded in step 1 — they are new to the corpus and have the
   thinnest Connections sections.
   Report each backlink added.

3. MOC AND HOME RECONCILIATION
   Read all files in wiki/mocs/ and wiki/home.md.
   Run: python3 scripts/tag-index.py
   This outputs a compact listing of every concept and summary with its
   title/source, date, and tags — without loading 150 full files. Keep the
   output; step 4 reads it again.

   This is the full sweep. p4a-post-ingest.md adds only each ingest's new
   files to their MOCs and adjusts home.md counts by net change; anything that
   drifted — a file that never got its entry, a count that went stale, a
   threshold crossed by an ingest that did not carry the tag — is caught here.

   Using the tag-index output and the MOC files:
   a) Verify that every concept and summary whose tags include a MOC domain
      is listed in that MOC. For any that are missing, add an entry with a
      one-line description. (Concept descriptions can draw on the first
      sentence already shown in the tag-index. For summaries, derive the
      description from the source filename and date.)
   b) Check every canonical tag: if a tag has 3+ articles (visible in the
      tag-index) but no MOC exists, and the tag is NOT listed under
      "Cross-cutting tags — no dedicated MOC" in CLAUDE.md, create the MOC
      following the MOC File Format in CLAUDE.md (including `aliases` and
      `cn-title`), then add an entry to wiki/index.md.
   c) Verify wiki/home.md lists every MOC file in wiki/mocs/, and that each
      MOC's article count matches the tag-index count — recount here rather
      than adjusting by net change.

   UNCOVERED RECORDS SYNC
   Collect all home.md changes — new/removed MOC table rows, corrected article
   counts, and the rebuilt Tags Without a MOC table — and apply them in a
   single write.
   For the Tags Without a MOC table: for every canonical tag (excluding
   cross-cutting tags listed under "Cross-cutting tags — no dedicated MOC"
   in CLAUDE.md) that has fewer than 3 articles (count from the tag-index)
   and has no MOC file, collect all articles carrying that tag. Rebuild
   the entire table in one pass, then write wiki/home.md once.

   Then add a wiki/index.md entry for every article created or expanded in
   step 1, per the Index Entry Format in CLAUDE.md, and write wiki/index.md
   once.
   Report all additions, removals, corrected counts, and new MOCs created.

4. NEW ARTICLE CANDIDATES
   Using the connections-index from step 2 and the tag-index from step 3 —
   both already in context, no re-run and no full file reads needed — identify
   3-5 new concept articles that would meaningfully improve the wiki's
   coverage. For each, explain why it would be valuable and which existing
   articles would link to it.

5. BILINGUAL, GLOSSARY, AND MEDICATION QA
   Step 1 creates and expands concept articles, step 2 writes Connections
   prose, and step 3 edits MOC files, wiki/home.md, and wiki/index.md. That is
   new clinical prose, so it carries the same three risks ingest does, and
   p1-ingest.md step 8 runs the same three checkers on it. Run
   these LAST, after every edit above is written, so the diff they inspect is
   complete. All three take `--git-diff` with no path arguments: that covers
   the main content locations (concepts, summaries, MOCs, wiki/index.md,
   wiki/home.md), bounds output to the lines this run changed, and scans any
   new/untracked file — such as an article created in step 1 — in full.

   a) Run: python3 scripts/check-bilingual-terms.py --git-diff
      English clinical terms written without their Chinese translation, per
      the Chinese Medical Terms policy in CLAUDE.md. Under `locale: none`
      the checker skips itself and reports that instead. Treat the output as a heuristic suspect list — some suspects
      are known false positives (see
      memory/reference-bilingual-checker-behavior.md for the recurring
      patterns). Patch real misses in the files this workflow touched, editing
      only those files, then rerun until no unreviewed high-confidence
      suspects remain.

   b) Run: python3 scripts/check-glossary-delta.py --git-diff
      Inline `English (中文)` pairs this pass wrote that are not yet in
      the glossary configured in wiki-config.yml. Review each one and follow the
      "What belongs in the glossary" rule in CLAUDE.md: add standalone,
      reusable clinical vocabulary; leave one-off phrases inline only; add a
      term you are unsure of for later review rather than guessing. Without
      this the glossary falls behind the content and the next ingest invents a
      second wording for a term this pass already translated. Rerun until no
      unreviewed reusable candidates remain.

   c) Run: python3 scripts/check-medication-first-mentions.py --git-diff
      The repo-wide `generic (Brand, local name)` format (Medication naming
      in CLAUDE.md) on first mention in each `###` section. This matters most
      for an article step 1 created from the summaries, whose medication
      mentions have never been checked. Note the checker silently SKIPS any
      medication concept missing `brand` or `local-brand-name` — a clean
      result here does not prove those fields exist; p4a-post-ingest.md step 3
      is what guarantees that. Patch any flagged first mention and rerun until
      no unreviewed suspects remain.

6. REPORT
   Cover, one line each: articles created and expanded (step 1), backlinks
   added (step 2), MOC entries added, counts corrected and MOCs created
   (step 3), and the step 5 results — bilingual, glossary terms added, and
   medication first mentions — one line each. Say "clean" or "none"
   where a step found nothing, so a step that ran and found nothing never
   looks like a step that was skipped. Then list the new article candidates
   from step 4.
