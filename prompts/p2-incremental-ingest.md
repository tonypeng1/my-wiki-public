Your task is to incrementally update the wiki with any new 
source documents added to raw/.

1. Read wiki/processed.log to get the list of already 
   processed files.

2. List all files currently in raw/.

3. Identify which files in raw/ do not appear in 
   wiki/processed.log. These are the new files to process.

4. If there are no new files, report that the wiki is 
   up to date and stop.

5. For each new file, do the following in order:
   a. Read the full contents of the file.
   b. Create wiki/summaries/{filename}.md following the 
      summary format in CLAUDE.md.
   c. For each key concept extracted:
      - If wiki/concepts/{concept}.md does not exist, create it
        following the concept article format in CLAUDE.md.
      - If it exists, read it and integrate new information
        without erasing existing content. If missing an `aliases`
        field, add one.
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

6. Report a summary of everything you created or modified.