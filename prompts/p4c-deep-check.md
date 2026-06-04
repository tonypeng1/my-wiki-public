Run this monthly to review content quality and coverage.
It complements p4a-post-ingest.md, which handles structural
housekeeping after each ingest.

1. MISSING AND THIN CONCEPT PAGES
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

2. MISSING ALIASES
   Run: grep -rL 'aliases:' wiki/concepts/
   This lists every concept file with no aliases field.
   Read only the files returned by that command, then add an
   `aliases` field with 3-5 common abbreviations, alternate
   spellings, and lay terms appropriate to each concept.

3. NEW ARTICLE CANDIDATES
   Run: python3 scripts/connections-index.py
   Run: python3 scripts/tag-index.py
   Using the connections-index and tag-index (no full file reads needed),
   identify 3-5 new concept articles that would meaningfully improve
   the wiki's coverage. For each, explain why it would be valuable
   and which existing articles would link to it.

4. Report a brief summary of everything changed and the new article
   candidates identified.
