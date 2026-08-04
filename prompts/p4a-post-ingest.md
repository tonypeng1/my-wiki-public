Run this immediately after p1-ingest.md to keep tags,
backlinks, and MOCs consistent with newly added content.

Every step here is either script-driven or bounded to what this ingest
changed. The repo-wide judgment passes — reviewing all concepts for missing
connections, reconciling every file against every MOC — belong to the monthly
p4c-coverage-check.md, which loads the indexes those passes need and amortizes
them across several steps. Do not do that work here: its cost does not shrink
when the ingest is small, so running it per-ingest pays full price for a
one-document addition.

Apply the Patient-Friendly Medical Writing policy in CLAUDE.md to all patient-facing prose created or revised by this workflow.

1. CLOSED VOCABULARIES — tags and provenance fields
   a) Run: python3 scripts/canonicalize-tags.py
   The script does two separate things across wiki/concepts/ and
   wiki/summaries/. It REWRITES tags that have a known synonym mapping
   (printing every file changed with a before→after diff), and handles the
   imaging-modality special rule for summaries. It only REPORTS tags that
   are outside the canonical set with no known mapping — those are never
   auto-changed, and the script exits 1 when any exist.
   Report its output. If it lists unknown tags, do not silently strip them:
   each one is either a real domain in the wrong vocabulary (map it), or
   metadata that belongs in a frontmatter field, or junk. Surface the list
   and ask before editing.

   b) Run: python3 scripts/check-provenance-fields.py
   Validates `facility`, `physician`, and `result-status` on summaries against
   the closed vocabularies in `memory/provenance-roster.md`, per the rules
   under "Provenance fields" in CLAUDE.md. Ingest is what
   writes these fields, so a bad value is caught here the same day, for the
   same reason as step 2 — and an UNKNOWN VALUE is most often this ingest
   inventing a slug for a site that needed a CLAUDE.md row first.
   Surface every failure and ask before editing; the fix differs by kind (add
   the vocabulary row in both CLAUDE.md and the script, versus correct a typo
   in the file), and only the maintainer can tell which applies.
   MISSING is informational. Do not backfill a field by inferring it — only
   from the raw/ source naming it.

2. CANONICAL RECORD FORMAT
   Run: python3 scripts/detect-list-records.py
   This flags concept files whose recurring-measurement record is a bulleted
   list rather than a Markdown table. A series in that shape does not anchor
   the contradiction check (scripts/extract-claims.py): its rows are skipped
   as authority and get misattributed as restatements of neighboring concepts.
   Ingest is what writes measurement records, so catching the shape here — the
   same day it is written — keeps a bad record from silently mis-anchoring
   /contradiction-check for a whole quarter until /lint converts it.
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
   you notice one.
   The scan is repo-wide, not limited to this ingest. If it flags a file this
   ingest did not touch, convert it anyway — it is the same fix /lint would
   make — and say in the report which conversions were pre-existing.
   List each conversion in the report.

3. FRONTMATTER COMPLETENESS — aliases · cn-title · medication fields
   Run: grep -rL 'aliases:' wiki/concepts/ wiki/mocs/
   Run: grep -rL 'cn-title:' wiki/concepts/ wiki/mocs/
   Run: grep -l '^tags:.*medication' wiki/concepts/*.md | xargs -I{} grep -L '^brand:' {}
   Run: grep -l '^tags:.*medication' wiki/concepts/*.md | xargs -I{} grep -L '^local-brand-name:' {}
   The first two list concept and MOC files with no aliases / no cn-title;
   the last two list medication concepts missing a brand field.

   Ingest is what creates concept and MOC files, and CLAUDE.md requires both
   fields on every new one — so this belongs here, the same day the file is
   written, for the same reason as step 2. The medication fields are the
   urgent half: check-medication-first-mentions.py silently SKIPS any
   medication concept missing either field, so the gap disables first-mention
   enforcement for that drug repo-wide and the checker still reports clean.
   A gap that switches off a checker must not wait for the monthly pass.

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
     gap instead of inventing a value.
   All per CLAUDE.md ("Frontmatter aliases and `cn-title`", "Medication concepts").
   `aliases`/`cn-title` are search/display metadata — do NOT bump `updated` for them.
   The greps are repo-wide and nearly free. If one flags a file this ingest did
   not touch, fill it anyway and say in the report which fills were pre-existing.
   List any medication field gaps you could not fill from the wiki.

4. CONNECTIONS FOR NEW AND EDITED CONCEPTS
   Bounded to this ingest. Run `git diff --name-only` (plus `git status` for
   untracked files) to list the concept files this ingest created or modified.
   For each, check that its Connections section links the concepts it directly
   relates to, and that those concepts link back to it. Read and edit only the
   files involved.
   Only add a backlink where the connection is substantive — one concept
   directly informs understanding of the other. Skip incidental or tangential
   relationships.
   Do NOT sweep the whole corpus here. The repo-wide pass over all concepts
   runs monthly in p4c-coverage-check.md, where connections-index.py is already
   loaded for the new-article candidates and the same 64 KB pays for two steps
   instead of one.
   Report each backlink added.

5. MOC FRESHNESS — new content only
   For each concept and summary this ingest created, add an entry with a
   one-line description to every MOC whose domain is among its tags. (The
   description can draw on the article's own first sentence; for summaries,
   derive it from the source filename and date.) The new files' own tags are
   all you need here — no repo-wide index required.

   Then update wiki/home.md:
   - bump the article count for each MOC whose membership changed, by the net
     change from this ingest rather than a recount
   - add a row for any MOC newly created below
   - add or update a Tags Without a MOC row only for a tag this ingest
     introduced
   - update the `updated:` field
   Collect all home.md changes and apply them in a single write.

   New MOC threshold: check whether any tag carried by this ingest's new files
   has no MOC file. Only if one does — the common case is that every tag
   already has its MOC, which costs nothing to confirm — run
   `python3 scripts/tag-index.py` to count that tag's articles. If the count is
   now 3+ and the tag is NOT listed under "Cross-cutting tags — no dedicated
   MOC" in CLAUDE.md, create the MOC following the MOC File Format in
   CLAUDE.md (including `aliases` and `cn-title`) and add an entry to
   wiki/index.md.

   Full reconciliation — verifying every existing concept and summary against
   every MOC, re-checking the threshold for every canonical tag, and rebuilding
   the entire Tags Without a MOC table — is monthly work in p4c-coverage-check.md.
   Do not do it here.
   Report the entries added, any MOC created, and the home.md counts changed.

6. DANGLING BACKLINK CHECK
   Newly ingested content, and any backlinks added in steps 4-5, can introduce
   `[[links]]` whose target has no file. Run:
   `python3 scripts/check-dangling-links.py --git-diff`
   With no path arguments this scans all authored content (concepts, summaries,
   MOCs, queries, wiki/index.md, wiki/home.md); --git-diff bounds it to the
   lines this ingest changed and scans any new/untracked file in full. A link
   is dangling when its target basename matches no .md file anywhere under
   wiki/ (Obsidian resolves `[[name]]` by basename across the vault, so
   concepts, summaries, MOCs, and query files are all valid targets). This is
   the repo's only wikilink resolver — p4-lint.md and p4c-coverage-check.md run
   the same checker, so all three passes agree on what "dangling" means.
   Fix each dangling link in the file this workflow touched:
   - a reference to a clinical domain → repoint to that domain's MOC,
     `[[moc-<domain>]]` (e.g. `[[hepatic]]` → `[[moc-hepatic]]`);
   - a typo or wrong target → correct the target;
   - a genuine concept that does not exist yet → leave it, and let the monthly
     `/coverage-check` create it (do NOT create a stub here).
   Rerun until no dangling links remain on changed lines.

7. CONTENT QA
   Step 4 writes Connections prose into concepts, step 5 writes MOC entries and
   can create a whole MOC, and step 6 repoints links. All of that is new prose
   written *after* p1-ingest.md step 8 ran its content checks
   on what the ingest itself wrote — so it is the one slice of authored content
   no checker has seen. It is a small slice, which is the point: bounded to a
   diff it costs almost nothing, and left unchecked it waits up to a month for
   p4c-coverage-check.md.

   Run these LAST, after every edit above is written — including the step 6 link
   repairs — so the diff they inspect is complete. All checks take `--git-diff`
   with no path arguments: that covers the main content locations (concepts,
   summaries, MOCs, wiki/index.md, wiki/home.md, and for the medication checker
   also queries and deliverables), bounds output to the lines this run changed,
   and scans any new/untracked file — such as a MOC created in step 5 — in full.
   Do not pass explicit paths; the defaults are wider than any list worth
   maintaining here. Run all checks unconditionally rather than gating on whether
   a given file changed: on a typical ingest they read a handful of lines, and a
   gate would make a skipped run and a clean run indistinguishable in step 8.

   a) Run: python3 scripts/check-bilingual-terms.py --git-diff
      English clinical terms written without their Chinese translation, per
      the Chinese Medical Terms policy in CLAUDE.md. Under `locale: none`
      the checker skips itself and reports that instead. Treat the output as a heuristic suspect list — some suspects
      are known false positives (see
      memory/reference-bilingual-checker-behavior.md for the recurring
      patterns). Patch real misses in the files this workflow touched, editing
      only those files, then rerun until no unreviewed high-confidence suspects
      remain.

   b) Run: python3 scripts/check-glossary-delta.py --git-diff
      Inline `English (中文)` pairs this pass wrote that are not yet in
      the glossary configured in wiki-config.yml. Review each and follow the "What
      belongs in the glossary" rule in CLAUDE.md: add standalone, reusable
      clinical vocabulary; leave one-off phrases inline only; add a term you are
      unsure of for later review rather than guessing. A Connections sentence or
      a MOC description is exactly where a fresh translation gets coined, and if
      it never reaches the glossary the next ingest invents a second
      wording for it. Rerun until no unreviewed reusable candidates remain.

   c) Run: python3 scripts/check-medication-first-mentions.py --git-diff
      The repo-wide `generic (Brand, local name)` format (Medication naming in
      CLAUDE.md) on first mention in each `###` section. A Connections bullet
      naming a drug is a first mention like any other. Note the checker silently
      SKIPS any medication concept missing `brand` or `local-brand-name`, so a
      clean result here does not prove those fields exist — step 3 above is what
      guarantees that, which is why it runs first. Patch any flagged first
      mention and rerun until no unreviewed suspects remain.

   d) Run: python3 scripts/check-unglossed-chinese.py --git-diff
      Chinese left in prose with no English — the mirror image of (a). The
      vault is English-canonical, so a clinical term written only in Chinese
      breaks its `[[backlinks]]` and cannot merge with an article drawn from an
      English-language facility. Checkers (a) and (b) are both keyed on the
      English half and are structurally blind to this. Expect findings mainly
      where the ingested document was itself Chinese. Physician and facility
      names are suppressed from memory/provenance-roster.md, so a flagged
      institution usually means the roster is missing a row — add the row
      rather than rewording the prose. A gloss written with a comma or slash
      instead of parentheses is reported on purpose. Patch and rerun.

   e) Run: python3 scripts/check-moc-key-relationships.py --git-diff
      Checks a new MOC, or an existing MOC whose Key Relationships section this
      run edited, against the CLAUDE.md contract: exactly one prose paragraph of
      2-3 sentences, with no open-question or document-acquisition language.
      The checker enforces structure and conservative action-language patterns;
      you must still verify source grounding and qualifications by reading the
      linked articles. Patch and rerun until clean.

   f) Run: python3 scripts/check-markdown-layout.py --git-diff
      Flags prose paragraphs or list items this run manually hard-wrapped.
      Rejoin each block onto one physical source line and let Obsidian soft-wrap
      it. Run this after every translation is final so inserted Chinese glosses
      cannot leave an irregular source-line staircase. Patch and rerun until
      clean.

8. REPORT
   Give one line per step 1-6 with its result, then one line each for 7a-7f —
   including "clean" or "none" when a check found nothing. A step that
   ran and found nothing and a step that was skipped must never look alike:
   most of these checks come back clean on a typical run, and a report that
   mentions only what changed is silent about them. Then list the files changed,
   since nothing here is committed and this report is what I review before
   committing.
   When this runs as the tail of /ingest, fold it into that run's
   report as its own section rather than writing a second report.
