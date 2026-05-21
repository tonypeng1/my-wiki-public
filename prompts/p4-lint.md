Perform a full health check on the wiki. Work through these 
checks in order:

1. Read wiki/index.md, all files in wiki/concepts/, and all
   files in wiki/summaries/.

2. MISSING AND THIN CONCEPT PAGES
   a) Identify every [[backlink]] referenced across all concept
      articles that does not have a corresponding file in
      wiki/concepts/. List them all.
   b) Identify concept articles that have fewer than 150 words
      of substantive content (excluding frontmatter). List them.

   For each article that is missing or thin:
   - If the summaries or other concept articles contain enough
     relevant information, create or expand the article directly
     using that material.
   - If no material is available, create a stub with an Overview
     section and a note marking it as a stub needing expansion.

3. MISSING BACKLINKS
   Look for concept articles that clearly relate to each
   other but do not yet link to each other. Only add a
   backlink where the connection is substantive — one concept
   directly informs understanding of the other. Skip
   incidental or tangential relationships.

4. MISSING ALIASES
   Identify concept articles that are missing an `aliases` 
   field in their frontmatter. For each, add an `aliases` 
   field with 3-5 common abbreviations, alternate spellings, 
   and lay terms appropriate to the concept.

5. MISPLACED QUERY FILES
   Read every file in wiki/queries/ root (not sub-folders).
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

6. NEW ARTICLE CANDIDATES
   Based on your reading of the full wiki, identify 3-5 
   new concept articles that would meaningfully improve 
   the wiki's coverage. For each, explain why it would 
   be valuable and which existing articles would link to it.

7. Write a health check report to wiki/maintenance/health-check-{today's date}.md
   with sections: wiki state summary · missing concepts created · thin articles expanded
   · backlinks added · missing aliases added · misplaced queries moved · recommended new articles.

8. Update wiki/index.md with an entry for the health check report.