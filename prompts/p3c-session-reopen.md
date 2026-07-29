The user wants to reopen a previously closed session. Follow these steps:

1. Check whether wiki/sessions/current.md already exists.
   - If it EXISTS: stop immediately. Tell the user there is already an
     active session open. They must close it with p3b-session-close.md
     before reopening an archived one.
   - If it does NOT exist: continue to step 2.

2. List all files in wiki/sessions/archive/ that do NOT end in
   -log.md (excluding .gitkeep). For each file, read only its
   frontmatter to extract the session-start date and the `topic:`
   field, and grep the file for "## Turn" to count turns without
   reading it in full.

   For older archives with no `topic:` field, fall back to the topic
   words in the filename (the part after the date), or "—" if none.

   Display a numbered list newest-first showing the topic, date, and
   turn count. Do NOT also print the filename — its date duplicates the
   date column. Keep an internal number → filename mapping for step 4:

     [1] Liver health Q&A         — 2026-07-07  (5 turns)
     [2] QTc & Holter follow-up   — 2026-07-04  (1 turn)
     ...

3. Ask the user which session they want to reopen. Wait for their
   response before continuing. Resolve their choice back to the archive
   filename using the mapping from step 2.

4. Restore both session files:

   - Copy the chosen archive file (e.g. 2026-05-21.md) to
     wiki/sessions/current.md.

   - If a matching log file exists (e.g. 2026-05-21-log.md):
     copy it to wiki/sessions/log.md.

   - If no matching -log.md exists (older archived session):
     reconstruct log.md from current.md as follows:
     a. Read current.md in full.
     b. For each ## Turn block, extract the Q, Sources, and write
        a 2–3 sentence Summary derived from the A field.
     c. Write wiki/sessions/log.md with the same frontmatter as
        current.md, followed by the reconstructed turn entries:

        ## Turn {N}
        **Q:** {extracted question}
        **Summary:** {2–3 sentence summary of the answer}
        **Sources:** {extracted sources}

   In both restored files, insert `status: active` into the
   frontmatter so it reads:

     ---
     session-start: {original value}
     status: active
     ---

   Do not modify any other part of either file.

5. Confirm to the user:
   - Which archive files were restored (current.md + log.md)
   - The session-start date
   - How many prior turns are now in context
   - That they can continue immediately using p3-qa.md

   Remind them that when they close this session with
   p3b-session-close.md, the existing consolidated query file (if any)
   covering the same topic will be flagged as a superseded candidate —
   they should confirm its move to wiki/queries/_superseded/ at that
   point.
