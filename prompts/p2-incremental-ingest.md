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
      - If wiki/concepts/{concept}.md does not exist, create it.
        Populate the `aliases` field with 3-5 common abbreviations,
        alternate spellings, and lay terms for the concept.
      - If it exists, read it fully and integrate new 
        information without erasing existing content. If the
        file is missing an `aliases` field, add one now.
   d. Before finalizing tags on any new concept or summary file, consult
      the canonical tag list in CLAUDE.md. Use only canonical tags.
      If no existing canonical tag fits the concept, propose the new tag,
      explain why no existing tag covers it, and add it to the canonical
      list in CLAUDE.md before using it in the file.

   e. Append the filename to wiki/processed.log.
   f. Add or update the relevant entries in wiki/index.md.
      Place each entry under the domain section matching the
      article's primary domain tag (first clinical-domain tag
      in its frontmatter). Cross-cutting-only articles go under
      the most relevant domain section. Follow the index entry
      format in CLAUDE.md.
   g. For each canonical tag on the new concept or summary, check whether
      a MOC exists at wiki/mocs/moc-{tag}.md. Skip tags listed under
      "Cross-cutting tags — no dedicated MOC" in CLAUDE.md. If a MOC
      exists, add the new article to the appropriate section (Concepts or
      Source Summaries). If no MOC exists for that tag (and it is not a
      cross-cutting tag) and 3+ articles now share it, create the MOC
      following the MOC File Format in CLAUDE.md, then add the new MOC
      as a row in the wiki/home.md MOC table.

6. After processing all new files, check if any of the 
   newly added concepts create backlink opportunities in 
   older concept articles. If so, update those articles.

7. Report a summary of everything you created or modified.