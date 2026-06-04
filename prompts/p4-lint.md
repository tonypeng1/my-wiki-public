Perform a full health check on the wiki. Work through these 
checks in order:

1. Read wiki/index.md, all files in wiki/mocs/, and wiki/home.md.
   (Concept and summary files are loaded on-demand in later steps.)

2. MISSING AND THIN CONCEPT PAGES
   Run: python3 scripts/detect-missing-thin.py
   The script scans all concept files and outputs two lists:
   (a) concept names referenced via [[backlink]] with no matching file
       in wiki/concepts/ or wiki/summaries/
   (b) concept files with fewer than 150 words of body content

   For each file identified as THIN: read only that concept file.
   For each MISSING concept: search wiki/summaries/ for files whose
   title or tags are topically relevant, then read only those.

   For each article that is missing or thin:
   - If the summaries or other concept articles contain enough
     relevant information, create or expand the article directly
     using that material.
   - If no material is available, create a stub with an Overview
     section and a note marking it as a stub needing expansion.

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

4. MISSING ALIASES
   Run: grep -rL 'aliases:' wiki/concepts/
   This lists every concept file with no aliases field.
   Read only the files returned by that command, then add an
   `aliases` field with 3-5 common abbreviations, alternate
   spellings, and lay terms appropriate to each concept.

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

   For each flagged file, state which sub-folder it likely belongs in
   (_handoff/ or _superseded/) and why, then ask me to confirm before
   moving anything. After I confirm:
   - Move the file to the appropriate sub-folder
   - Strip the `status:` field from the moved file's frontmatter

8. NEW ARTICLE CANDIDATES
   Based on the connections-index from step 3 and the tag-index from
   step 6, identify 3-5 new concept articles that would meaningfully
   improve the wiki's coverage. For each, explain why it would be
   valuable and which existing articles would link to it.

9. Write a health check report to wiki/maintenance/health-check-{today's date}.md
   with sections: wiki state summary · missing concepts created · thin articles expanded
   · backlinks added · missing aliases added · misplaced queries moved · recommended new articles.

10. Using the in-memory wiki/index.md (already updated with any new MOC
    entries in step 6), append the health check report entry and write
    wiki/index.md once.