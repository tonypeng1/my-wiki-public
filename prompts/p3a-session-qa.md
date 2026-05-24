My question is: "{YOUR QUESTION HERE}"

Follow these steps to answer it:

1. Check whether wiki/sessions/current.md exists.

   - If it EXISTS: read it in full. This is your live conversation
     history for the current session. Every prior Q&A turn is there.
     Use it as full context — you can reference anything discussed
     earlier without the user repeating themselves.

   - If it does NOT exist: create it now with this exact structure
     and nothing else:

     ---
     session-start: {today's date as YYYY-MM-DD}
     status: active
     ---

2. Read wiki/index.md in full to understand what the wiki contains.

3. Identify which wiki articles (concepts, summaries, or past queries)
   are most relevant to the current question, taking into account the
   session history. List them before proceeding.

4. Read each of those identified articles in full.

5. If any of those articles reference other articles via backlinks
   that also seem relevant, read those too.

6. Answer the question thoroughly, drawing on both the session history
   and the wiki articles. You may refer to earlier turns naturally
   (e.g. "as we discussed…") since you have the full session in context.

7. Append the following block to wiki/sessions/current.md:

   ## Turn {N}
   **Q:** {the exact question as asked}
   **A:** {your full answer}
   **Sources consulted:** {comma-separated list of wiki articles used}

   Where {N} is the next sequential turn number (count existing turns
   in the file to determine it).

Do NOT write anything to wiki/queries/ or update wiki/index.md.
All persistence is deferred until the session is closed with
p3b-session-close.md.
