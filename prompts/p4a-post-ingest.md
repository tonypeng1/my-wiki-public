Run this immediately after p2-incremental-ingest.md to keep tags,
backlinks, and MOCs consistent with newly added content.

1. TAG CANONICALIZATION
   Run: python3 scripts/canonicalize-tags.py
   The script replaces all non-canonical tags with their canonical
   equivalents across wiki/concepts/ and wiki/summaries/, handles the
   imaging-modality special rule for summaries, and prints every file
   changed with a before→after diff. Report its output.

2. MISSING BACKLINKS
   Run: python3 scripts/connections-index.py
   This outputs each concept's title, tags, overview sentence, and existing
   Connections section — everything needed to spot missing links without
   loading full article bodies (~34 KB vs ~191 KB for full files).

   Look for concept articles that clearly relate to each other but do not
   yet link to each other. Only add a backlink where the connection is
   substantive — one concept directly informs understanding of the other.
   Skip incidental or tangential relationships.
   To add a backlink, read and edit only the specific concept files involved.

3. MOC FRESHNESS
   Read all files in wiki/mocs/ and wiki/home.md.
   Run: python3 scripts/tag-index.py
   This outputs a compact listing of every concept and summary with its
   title/source, date, and tags — without loading 118 full files.

   Using the tag-index output and the MOC files:
   a) Verify that every concept and summary whose tags include a MOC domain
      is listed in that MOC. For any that are missing, add an entry with a
      one-line description. (Concept descriptions can draw on the first
      sentence already shown in the tag-index. For summaries, derive the
      description from the source filename and date.)
   b) Check: if a canonical tag now has 3+ articles (visible in the
      tag-index) but no MOC exists, and the tag is NOT listed under
      "Cross-cutting tags — no dedicated MOC" in CLAUDE.md, create the MOC
      following the MOC File Format in CLAUDE.md, then add an entry to
      wiki/index.md.
   c) Verify wiki/home.md lists every MOC file in wiki/mocs/.

   UNCOVERED RECORDS SYNC
   Collect all home.md changes — new/removed MOC table rows and the rebuilt
   Tags Without a MOC table — and apply them in a single write.
   For the Tags Without a MOC table: for every canonical tag (excluding
   cross-cutting tags listed under "Cross-cutting tags — no dedicated MOC"
   in CLAUDE.md) that has fewer than 3 articles (count from the tag-index)
   and has no MOC file, collect all articles carrying that tag. Rebuild
   the entire table in one pass, then write wiki/home.md once.
   Report all additions, removals, and new MOCs created.

4. Report a brief summary of everything changed.
