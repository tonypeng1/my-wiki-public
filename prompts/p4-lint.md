Perform a full health check on the wiki. Work through these 
checks in order:

0. LOCALE GATE
   Run: python3 scripts/check-locale-consistency.py

   This workflow writes clinical prose — step 2 creates and expands concept
   articles, step 4 fills frontmatter, step 6 rewrites MOCs — so it needs the
   same settled locale ingest does.

   - Exit 0 → proceed.
   - `LOCALE CONFIG INVALID` → report it as a finding and STOP. `wiki-config.yml`
     is missing or malformed; every gloss this run would write is unanchored
     until it is fixed.
   - `MISMATCH` → the configured locale disagrees with the prose already in the
     vault, which usually means `locale` was changed on a populated vault.
     Report it as the health check's top finding and STOP. Whether to revert the
     config or re-gloss the vault is the maintainer's call. Without this check
     the same condition surfaces as step 13 flagging nearly every article at
     once, which reads like a broken checker rather than a changed config.

   Record the outcome in the health check report either way.

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
   Chinese gloss; do NOT change any data. For PARTIALLY TABULAR,
   fold the stray bullets into the existing table. For SINGLE VALUE AS BULLET,
   convert the one value to a one-row table; read that tier as a candidate list
   rather than a finding, and skip an entry whose number turns out not to be a
   reported result. Leave dated *events* (medication start/stop dates,
   diagnosis timelines) as prose — the checker already excludes them. The
   checker only catches *date-led* values; one whose date sits in a header line
   is not auto-flagged — apply the same one-row-table rule from CLAUDE.md when
   you notice one. List each conversion in the health check report.

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
   Run: grep -l '^tags:.*medication' wiki/concepts/*.md | xargs -I{} grep -L '^local-brand-name:' {}
   The first two list concept and MOC files with no aliases / no cn-title;
   the last two list medication concepts missing a brand field.
   Under `locale: none` the Chinese layer does not exist: skip the `cn-title:`
   grep, and drop the Chinese-name requirement from `aliases`. Still run the
   `aliases:` grep — English abbreviations, alternate spellings, and lay terms
   are what make a note findable in any locale. `local-brand-name` is likewise
   not required. See the Chinese Medical Terms section in CLAUDE.md.

   Read only the files returned, then fill what is missing:
   - concept `aliases` — 3-5 common abbreviations, alternate spellings, and lay
     terms, including at least one Chinese name in the vault's locale. On a
     medication the Chinese brand name must be among them, since it is not in
     `cn-title`.
   - MOC `aliases` — the Chinese domain name (e.g. `aliases: [血脂]`).
   - `cn-title` — `English (中文)` on a concept, `MOC — {Domain} ({中文})` on a MOC.
   - `brand` / `local-brand-name` — take them from the article body or the source
     summary; never guess a local product name. If neither records it, report the
     gap instead of inventing a value. This matters because
     check-medication-first-mentions.py silently SKIPS any medication concept
     missing either field: the gap disables first-mention enforcement for that
     drug repo-wide and the checker still reports clean.
   All per CLAUDE.md ("Frontmatter aliases and `cn-title`", "Medication concepts").
   `aliases`/`cn-title` are search/display metadata — do NOT bump `updated` for them.
   List any medication field gaps in the health check report.

5. CLOSED VOCABULARIES — tags and provenance fields
   Two closed vocabularies live in frontmatter and drift the same way, so
   check them together.

   a) Run: python3 scripts/canonicalize-tags.py
   The script does two separate things across wiki/concepts/ and
   wiki/summaries/. It REWRITES tags that have a known synonym mapping
   (printing every file changed with a before→after diff), and handles the
   imaging-modality special rule for summaries. It only REPORTS tags that
   are outside the canonical set with no known mapping — those are never
   auto-changed, and the script exits 1 when any exist.
   Report unknown tags as a finding rather than fixing them inline: each is
   either a real domain in the wrong vocabulary, metadata belonging in a
   frontmatter field, or junk, and that call needs the maintainer.
   No file reads are needed for this sub-step.

   b) Run: python3 scripts/check-provenance-fields.py
   Validates `facility`, `physician`, and `result-status` on summaries
   against the closed vocabularies in `memory/provenance-roster.md`, per the
   rules under "Provenance fields" in CLAUDE.md.
   Three failures, all reported and none auto-fixed, all needing the
   maintainer for the same reason unknown tags do:
   - UNKNOWN VALUE — a new site or clinician never added to the roster, or a
     typo'd slug that will silently never match. Read the summary and the
     raw/ source to tell which before touching anything: a real new
     facility gets a row in `memory/provenance-roster.md`, which is the only
     edit needed (the script reads that roster at run time and holds no copy
     of it); a typo gets corrected in the file.
   - WRONG FILE TYPE — a provenance field on a concept. Concepts span many
     draws and carry provenance per-row in their canonical table instead.
   - PROVENANCE AS TAG — the regression these fields exist to prevent.
     Provenance was tags before — a clinic slug, a physician slug,
     `abnormal-result` — which polluted the clinical vocabulary and, since
     every facility clears the 3-article threshold, would have demanded a
     MOC for a clinic. Move the value to its field; do not just delete the
     tag.
   MISSING is informational, not a failure — the fields are omitted rather
   than guessed. Do NOT backfill one by inferring it from a filename or a
   neighbouring summary; only from the raw/ source naming it. Report the
   count, and name any file whose source clearly does record a site that
   the summary is missing.
   Include both scripts' output verbatim in the health check report.

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
   · list-format records converted · backlinks added · dangling links fixed · compilation summary gaps backfilled · missing frontmatter fields added (aliases, cn-title, medication brand fields) · closed-vocabulary findings (unknown tags, provenance field violations, provenance gaps) · misplaced queries moved · recommended new articles.

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

12. COMPILATION SUMMARY AUDIT
    The `## Compilation Summary` block at the top of wiki/index.md is owned by
    the ingest workflow (p1-ingest.md step 7b): one dated paragraph per ingest,
    appended at the end, never rewritten. It drifts silently — nothing fails
    when an ingest forgets its paragraph — and p3-qa.md reads this block for
    chronology and discovery-sequence questions, so a gap quietly degrades
    those answers. Run:
    `python3 scripts/check-compilation-summary.py`
    It cross-references the block against the ingest history in git (the
    commits that added files to wiki/processed.log) and reports four kinds:
    - MISSING — an ingest with no paragraph near its date. Reconstruct it from
      the commit and the summary articles that commit created, and head it
      `**{date} (backfilled {today}):**` so it does not pose as
      contemporaneous. Take the counts from git (`git ls-tree` at that commit),
      never invent them.
    - ORDER — paragraphs out of ascending order. The section runs oldest-first
      so that "append at the end" stays equivalent to date order; re-sort it,
      and never reverse the section to fix this.
    - FOREIGN — session Q&A content. No other workflow may write here, and a
      query already gets its own wiki/index.md entry. Before removing any,
      confirm its content is recorded elsewhere (query file, archive, or
      concept article) so nothing is lost.
    - UNDATED — a paragraph with no bold date header; give it one.
    INFO lines are not findings: one commit can bundle several ingest runs, and
    a run is often committed the following day.
    Any paragraph written or repaired here is new clinical prose — it must go
    through the translation QA in the next step like everything else.
    Add a one-line result (paragraphs backfilled, or "clean") to the health
    check report from step 9.

13. CONTENT QA
    Every run of this workflow edits MOC files, wiki/home.md, and
    wiki/index.md, and step 2 may create or expand concept articles. That is
    new clinical prose, so it carries the same content risks ingest does.

    Under `locale: none` the first two checkers skip themselves and say so;
    run them anyway rather than special-casing this step, and record the skip
    notice in the report. The medication checker still runs — it enforces
    `generic (Brand)` instead of the three-part form. Run
    these LAST, after every edit above is written — including the link
    repairs in step 11 — so the diff they inspect is complete. The checks take
    `--git-diff` with no path arguments: that covers the main content
    locations (concepts, summaries, MOCs, wiki/index.md, wiki/home.md),
    bounds output to the lines this run changed, and scans any new/untracked
    file — such as an article created in step 2 — in full.

    Read each checker's output in full; never pipe it through `head` or
    `tail`. Findings run two lines each and a `tail` drops them off the TOP,
    where nothing marks the loss, so a truncated read looks exactly like a
    short clean one. Each checker closes with `TOTAL: N flagged line(s)` for
    this reason: if N exceeds the rows you can see, the list is partial and
    the check is not done.

    a) Run: python3 scripts/check-bilingual-terms.py --git-diff
       English clinical terms written without their Chinese translation, per
       the Chinese Medical Terms policy in CLAUDE.md. Under `locale: none`
       the checker skips itself and reports that instead. Treat the output as a heuristic suspect list — some
       suspects are known false positives (see
       memory/reference-bilingual-checker-behavior.md for the recurring
       patterns). Patch real misses in the files this workflow touched,
       editing only those files, then rerun until no unreviewed
       high-confidence suspects remain.

    b) Run: python3 scripts/check-glossary-delta.py --git-diff
       Inline `English (中文)` pairs this pass wrote that are not yet in
       the glossary configured in wiki-config.yml. Review each and follow the "What
       belongs in the glossary" rule in CLAUDE.md: add standalone, reusable
       clinical vocabulary; leave one-off phrases inline only; add a term you
       are unsure of for later review rather than guessing. Rerun until no
       unreviewed reusable candidates remain.

    c) Run: python3 scripts/check-medication-first-mentions.py --git-diff
       The repo-wide `generic (Brand, local name)` format (Medication naming
       in CLAUDE.md) on first mention in each `###` section. Note the checker
       silently SKIPS any medication concept missing `brand` or
       `local-brand-name`, so a clean result here does not prove those
       fields exist — step 4 is what guarantees that. Patch any flagged first
       mention and rerun until no unreviewed suspects remain.

    d) Run: python3 scripts/check-unglossed-chinese.py --git-diff
       Chinese left in prose with no English — the mirror image of (a). The
       vault is English-canonical, so a clinical term written only in Chinese
       breaks its `[[backlinks]]` and cannot merge with an article drawn from
       an English-language facility. Checkers (a) and (b) are both keyed on
       the English half and are structurally blind to this, which is why it
       has its own step. Expect findings mainly where a source document was
       itself Chinese and the article had to be translated INTO English.
       Physician and facility names are suppressed from
       memory/provenance-roster.md, so a flagged institution usually means the
       roster is missing a row — add the row rather than rewording the prose.
       A gloss written with a comma or slash instead of parentheses is
       reported on purpose. Patch real misses and rerun.

    e) Run: python3 scripts/check-moc-key-relationships.py --git-diff
       Validate every MOC Key Relationships section this run created or edited:
       one prose paragraph, 2-3 sentences, no open-question or document-
       acquisition language. Also read the linked articles to verify source
       grounding and preserved qualifications. Patch and rerun until clean.

    f) Run: python3 scripts/check-markdown-layout.py --git-diff
       Rejoin every flagged prose paragraph or list item onto one physical
       source line and rely on Obsidian soft wrapping. Run it after the
       bilingual checks so Chinese glosses cannot leave irregular manual
       wrapping. Patch and rerun until clean.

    Append a one-line result for each of a-f (terms patched, glossary entries
    added, first mentions fixed, unglossed Chinese resolved, MOC relationships,
    Markdown layout — or "clean") to the health check report from step 9.
