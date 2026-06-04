My question is: "{YOUR QUESTION HERE}"

Follow these steps to answer it:

1. Search wiki/index.md for articles relevant to the question.

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

   d. Collect all matching structured article entries as candidates.
      Note any matching Query entries — these are superseded candidates
      for step 4.

2. From the candidates collected in step 1d, select the articles most
   directly relevant to the question. Cap the selection at 5 articles
   for a focused question, or 8 for a broad cross-domain question.

3. Read the selected articles. Apply these read rules:

   - Summary articles (lab results, imaging reports): read in full —
     specific values, dates, and flags are usually needed.
   - Concept articles: read Overview and Key Details sections first.
     Read the rest only if those sections are insufficient.
   - Query articles: read in full — current vs. superseded status matters.

   Do not follow backlinks to additional articles. The index grep in
   step 1 already surfaces all relevant articles by keyword. If a
   specific article name appears in the question and was not returned
   by the grep, fetch it directly — but do not traverse backlink chains.

4. Write a thorough answer and save it to the appropriate location,
   using the query file format from the project conventions. Include
   `status: current` in the frontmatter.

   Save destination rules:
   - If this is a clean handoff document with no Key Points / Source
     Articles / Follow-up sections: save to wiki/queries/_handoff/
     and omit the `status:` field.
   - Otherwise: save to wiki/queries/ root with `status: current`.

   Superseded check (run before saving):
   Using the Query entries identified in step 1d, check whether any
   existing query covers the same topic as this answer. If so, present
   it as a superseded candidate and state why. Wait for my confirmation
   before moving it to wiki/queries/_superseded/ and stripping its
   `status:` field.

5. Add an entry for this query file to wiki/index.md.

6. If the process of answering this question revealed any gaps
   in existing concept articles, note them at the end of your
   response so I can decide whether to address them.