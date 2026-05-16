Read INSTRUCTIONS.md first and follow all conventions defined there.

Your task is to compile the wiki from scratch using all documents 
currently in raw/.

For each file in raw/, do the following in order:

1. Read the full contents of the file.

2. Create wiki/summaries/{filename}.md following the summary 
   format in INSTRUCTIONS.md. Extract all key concepts and 
   write backlinks to any related concepts you identify.

3. For each key concept you extracted:
   a. Check if wiki/concepts/{concept-name}.md already exists.
   b. If it does not exist, create it following the concept 
      article format in INSTRUCTIONS.md.
   c. If it already exists, read it and update it with any 
      new information from the current document. Do not 
      erase existing content — only add and integrate.

4. Append the filename to wiki/processed.log on a new line.

5. Add an entry for each new or updated wiki file to 
   wiki/index.md following the index format in INSTRUCTIONS.md.

After processing all files, do a final pass:
- Read all concept articles you created or updated today
- Look for concepts that reference each other and add 
  backlinks where they are missing
- Write a one-paragraph compilation summary at the top 
  of wiki/index.md describing what the wiki now covers