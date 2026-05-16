Read INSTRUCTIONS.md first and follow all conventions defined there.

The user has asked to end the current session. Follow these steps:

1. Check whether wiki/sessions/current.md exists.
   - If it does NOT exist: stop immediately and tell the user there is
     no active session to close.
   - If it EXISTS: read it in full. This contains all Q&A turns
     from the session.

2. Read wiki/index.md in full.

3. For each turn in the session, decide whether it is worth saving as
   a standalone query file. Save a turn if it:
   - Contains a substantive, self-contained question and answer
   - Would be useful to refer back to in future sessions or queries
   Skip turns that are trivial, redundant, or too context-dependent
   to stand alone.

4. For each turn selected in step 3, save it to:
   wiki/queries/{slugified-question}.md

   Use this structure:

   ---
   question: {the full question}
   date: {session-start date from current.md frontmatter}
   sources: [{comma-separated list of sources from that turn}]
   ---

   # {Question as Title}

   ## Answer
   {The full answer from that turn}

   ## Key Points
   - Bullet summary of the most important takeaways

   ## Source Articles Consulted
   - [[article-1]]
   - [[article-2]]

   ## Follow-up Questions Worth Exploring
   - Question 1
   - Question 2
   - Question 3

5. For each query file saved in step 4, add an entry to wiki/index.md
   using the standard index format.

6. Archive the session by copying the full contents of
   wiki/sessions/current.md to:
   wiki/sessions/archive/{session-start datetime slug}.md
   where the datetime slug is derived from the session-start field
   in the frontmatter (e.g. 2026-05-15T1430 → 2026-05-15-1430.md).

7. Delete wiki/sessions/current.md.

8. Report back to the user:
   - How many turns were in the session
   - Which turns were saved as query files (with filenames)
   - Which turns were skipped and why
   - The archive filename
