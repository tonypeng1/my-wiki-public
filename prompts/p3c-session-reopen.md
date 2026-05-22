Read INSTRUCTIONS.md first and follow all conventions defined there.

The user wants to reopen a previously closed session. Follow these steps:

1. Check whether wiki/sessions/current.md already exists.
   - If it EXISTS: stop immediately. Tell the user there is already an
     active session open. They must close it with p3b-session-close.md
     before reopening an archived one.
   - If it does NOT exist: continue to step 2.

2. List all files in wiki/sessions/archive/ (excluding .gitkeep).
   For each file, read its frontmatter to extract the session-start
   date. Display a numbered list to the user in this format:

     [1] 2026-05-21.md    — started 2026-05-21  (N turns)
     [2] 2026-05-21-2.md  — started 2026-05-21  (N turns)
     ...

   Count turns by counting "## Turn" occurrences in each file.
   Sort the list newest-first.

3. Ask the user which session they want to reopen. Wait for their
   response before continuing.

4. Copy the full contents of the chosen archive file into
   wiki/sessions/current.md, then insert `status: active` into the
   frontmatter so it reads:

     ---
     session-start: {original value}
     status: active
     ---

   Do not modify any other part of the file.

5. Confirm to the user:
   - Which archive file was restored
   - The session-start date
   - How many prior turns are now in context
   - That they can continue immediately using p3a-session-qa.md

   Remind them that when they close this session with
   p3b-session-close.md, the existing consolidated query file (if any)
   covering the same topic will be flagged as a superseded candidate —
   they should confirm its move to wiki/queries/_superseded/ at that
   point.
