My question is: "{YOUR QUESTION HERE}"

This is the only Q&A workflow. It covers both a one-off question and a
multi-turn conversation, because the two are the same operation: every question
is a turn in a session, and a one-off question is simply a session with one
turn. There is no separate one-shot command and no path that writes to
wiki/queries/ from here — p3b-session-close.md is the only publisher, and
closing a one-turn session produces exactly the file a standalone one-off
answer would, plus the translation checker gate that path never had.

Apply the Patient-Friendly Medical Writing policy in CLAUDE.md to all patient-facing prose created or revised by this workflow.

Follow these steps to answer it:

1. Check whether wiki/sessions/log.md exists.

   - If it EXISTS: read it in full. This is the compact session
     history — one summary entry per prior turn. Use it to restore
     context for the current session.

   - If it does NOT exist: this is a new session. Create both files
     now with this exact frontmatter and nothing else:

     wiki/sessions/current.md:
     ---
     session-start: {today's date as YYYY-MM-DD}
     status: active
     ---

     wiki/sessions/log.md:
     ---
     session-start: {today's date as YYYY-MM-DD}
     status: active
     ---

2. Search wiki/index.md for articles relevant to the question.

   a. Extract 3–5 key terms from the question.

   b. Grep wiki/index.md for each term. Apply these read rules to each hit:

      - Hit inside a structured article entry (a line starting with ## and
        ending in .md, followed by Type / Tags / Summary / Related lines):
        Read the full 5-line block. This is the atomic unit — always read
        it in full.

      - Hit inside a dated narrative paragraph in the Compilation Summary
        (line starting with bold date e.g. **2026-05-23**):
        Read the entire paragraph (blank line to blank line). Do not try
        to extract individual clauses.

      - Hit on a domain section header (## Cardiology, ## Lipid, etc.):
        Use as a routing signal only. Do not read further.

   c. Skip the Compilation Summary block by default. Read a Compilation
      Summary paragraph only if:
      - No structured article entries matched the search terms, OR
      - The question is explicitly about chronology, discovery sequence,
        or cross-article update history.

   d. Collect all matching structured article entries as candidates for
      the next step.

3. From the candidates collected in step 2d, select the articles most
   directly relevant to the question. Cap the selection at 5 articles
   for a focused question, or 8 for a broad cross-domain question.

4. Read the selected articles. Apply these read rules:

   - Summary articles (lab results, imaging reports): read in full —
     specific values, dates, and flags are usually needed.
   - Concept articles: read Overview and Key Details sections first.
     Read the rest only if those sections are insufficient.
   - Query articles: read in full — current vs. superseded status matters.

   Do not follow backlinks to additional articles. The index grep in
   step 2 already surfaces all relevant articles by keyword. If a
   specific article name appears in the question or session history
   and was not returned by the grep, fetch it directly — but do not
   traverse backlink chains.

5. Answer the question thoroughly, drawing on both the session history
   and the wiki articles. You may refer to earlier turns naturally
   (e.g. "as we discussed…") since you have the full session in context.

   As you write, apply the Chinese Medical Terms policy in
   CLAUDE.md (single source of truth) to the answer prose — reuse the wording
   in the glossary configured in `wiki-config.yml`, follow the
   query-file exception for the aggressive repeat rules, and use the
   `generic (Brand, local name)` medication first-mention format. This
   keeps the transient session text mostly translated so the checker pass
   at session-close (p3b) is a verification-and-patch step, not a rewrite.
   Do not run the checker scripts here — current.md is transient and all
   verification is deferred to session-close.

6. Append to both session files.

   To wiki/sessions/current.md (full record):

   ## Turn {N}
   **Q:** {the exact question as asked}
   **A:** {your full answer}
   **Sources consulted:** {comma-separated list of wiki articles used}

   To wiki/sessions/log.md (compact summary):

   ## Turn {N}
   **Q:** {the exact question as asked}
   **Summary:** {2–3 sentences capturing the key conclusions}
   **Sources:** {comma-separated list of wiki articles used}

   Where {N} is the next sequential turn number (count existing
   ## Turn entries in log.md to determine it).

7. Close your response with the session state and any gaps found.

   a. State the current turn count and remind me that this answer is not
      published yet — it reaches wiki/queries/ only when I run
      p3b-session-close.md. Keep this to one line; it appears every turn.

   b. If answering this question revealed any gaps in existing concept
      articles, note them so I can decide whether to address them. Report
      these per turn, while the gap is fresh, rather than saving them for
      the close.

Do NOT write anything to wiki/queries/ or update wiki/index.md.
All persistence is deferred until the session is closed with
p3b-session-close.md.
