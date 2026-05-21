My question is: "{YOUR QUESTION HERE}"

Follow these steps to answer it:

1. Read wiki/index.md in full to understand what the wiki contains.

2. Identify which wiki articles (concepts, summaries, or past 
   queries) are most relevant to the question. List them before 
   proceeding.

3. Read each of those identified articles in full.

4. If any of those articles reference other articles via backlinks 
   that also seem relevant, read those too.

5. Write a thorough answer and save it to the appropriate location,
   using the query file format from the project conventions. Include
   `status: current` in the frontmatter.

   Save destination rules:
   - If this is a clean handoff document with no Key Points / Source
     Articles / Follow-up sections: save to wiki/queries/_handoff/
     and omit the `status:` field.
   - Otherwise: save to wiki/queries/ root with `status: current`.

   Superseded check (run before saving):
   Read the `question:` frontmatter value of every file currently in
   wiki/queries/ root. If any existing file covers the same topic as
   this answer, present it to me as a superseded candidate and state
   why. Wait for my confirmation before moving it to
   wiki/queries/_superseded/ and stripping its `status:` field.

6. Add an entry for this query file to wiki/index.md.

7. If the process of answering this question revealed any gaps 
   in existing concept articles, note them at the end of your 
   response so I can decide whether to address them.