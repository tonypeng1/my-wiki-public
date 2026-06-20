Your task is to compile the wiki from scratch using all documents 
currently in raw/.

For each file in raw/, do the following in order:

1. Read the full contents of the file.
   For image files (.png, .jpg, .jpeg): read the file visually and extract
   chart titles, axes, time ranges, key data series, notable trends,
   anomalies, and specific values. Treat this extracted information as the
   "contents" for the rest of the pipeline.

2. Create wiki/summaries/{filename}.md following the summary 
   format in CLAUDE.md. Extract all key concepts and 
   write backlinks to any related concepts you identify.

3. For each key concept you extracted:
   a. Check if wiki/concepts/{concept-name}.md already exists.
   b. If it does not exist, create it following the concept
      article format in CLAUDE.md.
   c. If it already exists, read it and integrate new information
      without erasing existing content. If missing an `aliases`
      field, add one.

4. Use only canonical tags (see CLAUDE.md) on all files created
   in steps 2 and 3. If no existing tag fits, follow the
   "Adding a new canonical tag" procedure in CLAUDE.md before
   using it in any file.

5. Append the filename to wiki/processed.log on a new line.

6. Add an entry for each new or updated wiki file to 
   wiki/index.md. Place the entry under the domain section 
   matching the article's primary domain tag (first clinical-
   domain tag in its frontmatter). Cross-cutting-only articles 
   go under the most relevant domain section. Follow the index 
   entry format in CLAUDE.md.

After processing all files, do a final pass:
- Add cross-concept backlinks where missing.
- For each canonical, non-cross-cutting tag that now has 3+
  articles and no MOC file, create a MOC following the MOC File
  Format in CLAUDE.md.
- Write a one-paragraph compilation summary at the top of wiki/index.md
  describing what the wiki now covers.
- Build wiki/home.md from scratch following the Home Page Format in CLAUDE.md.