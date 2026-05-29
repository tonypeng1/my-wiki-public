Your task is to compile the wiki from scratch using all documents 
currently in raw/.

For each file in raw/, do the following in order:

1. Read the full contents of the file.

2. Create wiki/summaries/{filename}.md following the summary 
   format in CLAUDE.md. Extract all key concepts and 
   write backlinks to any related concepts you identify.

3. For each key concept you extracted:
   a. Check if wiki/concepts/{concept-name}.md already exists.
   b. If it does not exist, create it following the concept 
      article format in CLAUDE.md. Populate the `aliases`
      field with 3-5 common abbreviations, alternate spellings,
      and lay terms for the concept.
   c. If it already exists, read it and update it with any 
      new information from the current document. If the file 
      is missing an `aliases` field, add one now. Do not 
      erase existing content — only add and integrate.

4. Append the filename to wiki/processed.log on a new line.

5. Add an entry for each new or updated wiki file to 
   wiki/index.md. Place the entry under the domain section 
   matching the article's primary domain tag (first clinical-
   domain tag in its frontmatter). Cross-cutting-only articles 
   go under the most relevant domain section. Follow the index 
   entry format in CLAUDE.md.

After processing all files, do a final pass:
- Read all concept articles you created or updated today
- Look for concepts that reference each other and add 
  backlinks where they are missing
- Write a one-paragraph compilation summary at the top 
  of wiki/index.md describing what the wiki now covers
- Rebuild wiki/home.md from scratch with two sections:

  ## Maps of Content
  A table with columns: MOC | Domain | Articles
  One row per MOC file in wiki/mocs/, linking to it with
  [[wikilink]] syntax. Articles = total count of concepts
  and summaries tagged with that MOC's domain tag.

  ## Tags Without a MOC
  Subtitle: "These tags have fewer than 3 articles and no
  MOC file yet. Articles may still be covered by other
  domain MOCs — this table tracks tags, not orphaned articles."
  A table with columns: Tag | Articles sharing this tag | Count
  One row per canonical tag (excluding cross-cutting tags
  listed under "Cross-cutting tags — no dedicated MOC" in
  CLAUDE.md) that has fewer than 3 articles and no MOC file.
  Articles listed as [[wikilinks]], comma-separated.
  Rows sorted by Count descending.
  If no such tags exist, omit this section entirely.