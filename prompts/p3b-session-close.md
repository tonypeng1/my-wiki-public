The user has asked to end the current session. Follow these steps:

1. Check whether wiki/sessions/current.md exists.
   - If it does NOT exist: stop immediately and tell the user there is
     no active session to close.
   - If it EXISTS: read it in full. This contains all Q&A turns
     from the session.

2. Read only the Queries section of wiki/index.md (from the "## Queries"
   heading to end of file). This is sufficient to check for superseded
   candidates — the full index is not needed.

3. Compile all turns into a single consolidated query file.

   Derive a session topic/title that best captures the overall theme
   of the session (e.g. "Liver health Q&A — May 2026").

   Save destination rules:
   - If the consolidated content is a clean handoff document with no
     Key Points / Source Articles / Follow-up sections: save to
     wiki/deliverables/ and omit the `status:` field.
   - Otherwise: save to wiki/queries/ root with `status: current`.

   Superseded check (run before saving):
   Read the `question:` frontmatter value of every file currently in
   wiki/queries/ root. Check whether any existing file covers the same
   overall topic as this session. Collect all candidates, present them
   to me as a group with a reason for each, and wait for my
   confirmation. After I confirm, move each approved file to
   wiki/queries/_superseded/ and strip its `status:` field.

   Name the file `{date}-{slug}.md`, where `{date}` is the `date:` value
   below (the session-start date) — same date-prefix convention as
   wiki/sessions/archive/.

   File structure:

   ---
   question: {the session topic/title}
   date: {session-start date from current.md frontmatter}
   sources: [{all unique sources consulted across all turns}]
   status: current
   ---

   # {Session Topic as Title}

   ## Answer
   Synthesized narrative combining the answers from all turns into one
   coherent, readable response. Blend the content — do not just
   concatenate turns verbatim.

   ## Key Points
   - Bullet summary of the most important takeaways across all turns

   ## Source Articles Consulted
   - [[article-1]]
   - [[article-2]]

   ## Follow-up Questions Worth Exploring
   - Collected follow-up questions from all turns

4. Add one entry to wiki/index.md for the consolidated query file,
   using the standard index format.

5. Archive both session files.

   Build {slug} = {session-start date}-{topic-slug}, where topic-slug is
   the session topic derived in step 3, lowercased and hyphenated and
   trimmed to ~5 words (e.g. 2026-05-21-liver-health-qa).

   wiki/sessions/current.md → wiki/sessions/archive/{slug}.md
   wiki/sessions/log.md     → wiki/sessions/archive/{slug}-log.md

   If {slug}.md already exists, append a counter suffix to both:
   {slug}-2.md and {slug}-2-log.md, etc.

   Before saving each, edit the frontmatter:
   - remove the `status:` line — presence in the archive folder is
     sufficient to indicate closure.
   - add a `topic:` line holding the human-readable session topic from
     step 3 (e.g. `topic: Liver health Q&A`). This drives the display in
     p3c-session-reopen.md.

6. Run the Traditional Chinese translation pass over the files this
   close produced, before deleting the session files.

   Read `memory/medical-term-translations.md` (the shared glossary), then
   apply the Traditional Chinese Medical Terms policy in CLAUDE.md (single
   source of truth) to all three output files:
   - the consolidated query file from step 3 — apply the query-file
     exception (re-translate in Key Points, tables, and follow-up bullets;
     repeat skim-critical abbreviations per `###` subsection);
   - both archived session files from step 5 (`{slug}.md` and
     `{slug}-log.md`) — apply the default per-section two-per-term rule.
   Reuse glossary wording, and use the `generic (Brand, Taiwan name)`
   medication first-mention format. Because p3a already translated the
   answer prose as it was written, this is mostly verification and
   patching gaps, not a full rewrite.

   Then run the checker scripts over the same three files, mirroring the
   ingest QA gate:
   - `python3 scripts/check-bilingual-terms.py --git-diff PATH [PATH ...]`
     — patch real misses, rerun until no unreviewed high-confidence
     suspects remain. Treat the output as a floor, not a ceiling.
   - `python3 scripts/check-bilingual-terms.py PATH [PATH ...]` (no
     --git-diff) as the final gate — catches in-glossary terms left
     untranslated on lines the edits did not touch. A `(2nd)` suffix means
     a term recurs in one counting unit with fewer than two translations;
     patch the missing occurrence.
   - `python3 scripts/check-medication-first-mentions.py --git-diff PATH [PATH ...]`
     — patch any flagged first mention missing the
     `generic (Brand, Taiwan name)` format, rerun until clean.
   - `python3 scripts/check-glossary-delta.py --git-diff PATH [PATH ...]`
     — review each inline `English (中文)` pair, add reusable standalone
     clinical terms to `memory/medical-term-translations.md` in
     alphabetical order, leave one-off phrases inline only, rerun until no
     unreviewed reusable candidates remain.

7. Delete wiki/sessions/current.md and wiki/sessions/log.md.

8. Report back to the user:
   - How many turns were in the session
   - The filename of the consolidated query file saved
   - The archive filename
   - Glossary entries added, if any, and any deliberately deferred or
     ambiguous translation choices
