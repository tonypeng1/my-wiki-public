Read INSTRUCTIONS.md first and follow all conventions defined there.

The user has asked to end the current session. Follow these steps:

1. Check whether wiki/sessions/current.md exists.
   - If it does NOT exist: stop immediately and tell the user there is
     no active session to close.
   - If it EXISTS: read it in full. This contains all Q&A turns
     from the session.

2. Read wiki/index.md in full.

3. Compile all turns into a single consolidated query file.

   Derive a session topic/title that best captures the overall theme
   of the session (e.g. "Liver health Q&A — May 2026").

   Save destination rules:
   - If the consolidated content is a clean handoff document with no
     Key Points / Source Articles / Follow-up sections: save to
     wiki/queries/_handoff/ and omit the `status:` field.
   - Otherwise: save to wiki/queries/ root with `status: current`.

   Superseded check (run before saving):
   Read the `question:` frontmatter value of every file currently in
   wiki/queries/ root. Check whether any existing file covers the same
   overall topic as this session. Collect all candidates, present them
   to me as a group with a reason for each, and wait for my
   confirmation. After I confirm, move each approved file to
   wiki/queries/_superseded/ and strip its `status:` field.

   File structure:

   ---
   question: {the session topic/title}
   date: {session-start date from current.md frontmatter}
   sources: [{all unique sources consulted across all turns}]
   status: current
   ---

   # {Session Topic as Title}

   ## Answer
   Synthesized narrative combining the answers from all turns into one
   coherent, readable response. Blend the content — do not just
   concatenate turns verbatim.

   ## Key Points
   - Bullet summary of the most important takeaways across all turns

   ## Source Articles Consulted
   - [[article-1]]
   - [[article-2]]

   ## Follow-up Questions Worth Exploring
   - Collected follow-up questions from all turns

4. Add one entry to wiki/index.md for the consolidated query file,
   using the standard index format.

5. Archive the session by copying the full contents of
   wiki/sessions/current.md to:
   wiki/sessions/archive/{slug}.md
   where {slug} is the session-start date (e.g. 2026-05-21).
   If that filename already exists, append a counter suffix:
   2026-05-21-2.md, 2026-05-21-3.md, etc.
   Before saving, remove the `status:` line from the frontmatter —
   presence in the archive folder is sufficient to indicate closure.

6. Delete wiki/sessions/current.md.

7. Report back to the user:
   - How many turns were in the session
   - The filename of the consolidated query file saved
   - The archive filename
