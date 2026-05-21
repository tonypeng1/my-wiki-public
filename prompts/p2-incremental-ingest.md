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
      summary format in INSTRUCTIONS.md.
   c. For each key concept extracted:
      - If wiki/concepts/{concept}.md does not exist, create it.
        Populate the `aliases` field with 3-5 common abbreviations,
        alternate spellings, and lay terms for the concept.
      - If it exists, read it fully and integrate new 
        information without erasing existing content. If the
        file is missing an `aliases` field, add one now.
   d. Append the filename to wiki/processed.log.
   e. Add or update the relevant entries in wiki/index.md.

6. After processing all new files, check if any of the 
   newly added concepts create backlink opportunities in 
   older concept articles. If so, update those articles.

7. Report a summary of everything you created or modified.