Perform a targeted contradiction check on the wiki.
Run this occasionally — it is not part of the standard health check.

Scope: numeric claims in wiki/concepts/ — specific values, dates,
reference ranges, and test results. Prose/status contradictions
("resolved" vs "active", conflicting causal claims, ranges stated in
words) are NOT covered by this pass; say so when reporting.

1. Run: python3 scripts/extract-claims.py
   The script groups every numeric/date claim in wiki/concepts/ by the
   concept it is about, so claims arrive already paired with their
   counterparts. This replaces reading all 69 concept files (~377 KB).

   There are two kinds of block.

   ANCHORED — the concept has its own longitudinal table, which is the
   authoritative record fed by ingest:

     === vitamin-d ===
     CANONICAL  wiki/concepts/vitamin-d.md
       L27  | 2020-03-11 | LabA | VD-25OH | 28.4 | LOW | ...
     RESTATEMENTS
       bone-density.md:44  all three vitamin D draws came back LOW ...

   PEER — the concept has no table, so no claim referees the others.
   Asserted values are shown in [brackets] and the claims are sorted by
   value, so agreeing claims cluster and outliers stand apart:

     === atenolol ===
     PEER CLAIMS  wiki/concepts/atenolol.md has no longitudinal table
       [25 mg, 2024-03-11]
         cardiology-visit.md:22  ... atenolol 25 mg prescribed on 2024-03-11
       [25 mg, 2024-03-11]
         ecg-findings.md:52      Atenolol 25 mg (started 2024-03-11) ...

   Blocks with no restatement are omitted — a concept nobody else cites
   cannot have a cross-file contradiction. Peer blocks holding only one
   claim are omitted too: a lone claim has nothing to disagree with.

2. CONTRADICTIONS
   In ANCHORED blocks, compare every RESTATEMENT against the CANONICAL
   rows above it. This is where drift lives: the canonical table gets
   updated on ingest and the hand-written restatement does not.

   In PEER blocks, compare the claims against each other. Disagreement
   between two files is the finding; neither side is presumed correct,
   so report both and let me decide which is right.

   Look for:
   - a value, date, or flag that disagrees with the canonical row
   - a count or series that is stale ("all three readings" when the
     table now holds six)
   - a stated range that no longer spans the canonical values

   Do NOT flag these:
   - different values at different dates — this is longitudinal data,
     and change over time is the norm, not a contradiction
   - a statement explicitly scoped to a subset ("the three 2019 draws")
   - lab-dependent differences where the article names the reason
     (e.g. a value left unflagged by one lab's wider reference range but
     flagged by another lab's stricter one)

   Claim text in the script output is condensed to ~200 characters.
   Read the full file ONLY for blocks that look inconsistent, using the
   file:line pointer, and quote both conflicting statements verbatim.

   Group findings by clinical domain where it helps readability, but do
   not use tags as the primary lens: `biomarker` is the first tag on 23
   of 69 concepts and is cross-cutting, so it does not partition the
   corpus. The concept grouping in the script output is the better unit.

   Sort every finding into Tier A or Tier B before changing anything.

   TIER A — fix automatically. ALL of these must hold:
   - the block is ANCHORED (a canonical table exists)
   - the correct value is unambiguous: a specific canonical cell, or a
     count/range derived from the canonical rows by arithmetic
   - the fix is a mechanical substitution — a number, count, date, or
     range swapped for the canonical one
   - nothing else about the sentence changes: no rewording, no clause
     added or removed, no change of scope

   TIER B — do not fix. Flag with options (step 4). ANY of these:
   - the finding is in a PEER block — no claim is authoritative
   - the fix would change the sentence's meaning, structure, or scope
   - more than one plausible correct fix exists
   - the canonical table itself may be wrong or incomplete
   - resolving it needs knowledge the wiki does not hold (e.g. whether a
     test was never drawn, or drawn but never ingested)
   - any clinical interpretation is involved

   When in doubt, it is Tier B. A wrong flag costs me a minute; a wrong
   edit writes a falsehood into a medical record.

3. TIER A — apply the fixes.
   - Edit only the restating file. NEVER edit a canonical table row:
     those are fed by ingest (p2), and correcting them here would
     overwrite the record with a guess.
   - Edit only files in wiki/concepts/.
   - Bump the `updated:` frontmatter date on each file changed.
   - Update that concept's wiki/index.md entry only if the corrected
     value also appears there.
   - Apply all Tier A fixes in one batch, then re-run
     `python3 scripts/extract-claims.py` and confirm each fixed finding
     is gone and no new disagreement appeared.
   - The re-run is not a complete check. Claim text in the output is
     truncated at ~200 characters, so a fix landing past that point shows
     no change even when it applied correctly. For any edit beyond roughly
     the first 200 characters of its line — and these are common, since the
     long restatement lines are exactly the ones that drift — confirm it by
     opening the file at its file:line rather than trusting the re-run.
     Report it as verified only once you have looked.

4. TIER B — flag each finding with a menu I can pick from.
   Do not ask open-ended questions; give me concrete, executable choices.

   Use this shape:

     FINDING {n}: {one-line description}
       A. {file:line}  "{verbatim statement}"
       B. {file:line or CANONICAL}  "{verbatim statement}"
       Why not auto-fixed: {one sentence}
       Options:
         1. {the exact edit, with the replacement text written out}
            — assumes: {what must be true for this to be right}
         2. {alternative edit}
            — assumes: {…}
         3. Leave as is — {the circumstance that makes this correct}

   Rules for the menu:
   - every option must be executable as written, with the actual
     replacement wording spelled out — not "reword to match"
   - state what each option assumes, since that assumption is the thing
     I am actually choosing between
   - always include a "leave as is" option and say when it is right
   - at most 4 options; if there are genuinely more, give the 3 most
     likely and say the list is not exhaustive

   Present ALL Tier B findings together in one numbered list, then STOP.
   Do not apply any Tier B option, and do not pause after each finding to
   ask about it — finish the whole check first, so I can see every finding
   before deciding any of them. Several findings often share one root
   cause and deserve one consistent decision.

   Never pick a Tier B option yourself, however likely one looks. A
   finding is Tier B precisely because the choice is mine.

   I may answer for all findings, or only some ("3 → option 2, skip the
   rest"). Apply exactly what I picked, leave the rest flagged, and say
   which ones are still open.

5. Report. Include:
   - TIER A: what was changed, as before → after with file:line
   - TIER B: the findings and their option menus
   - if nothing was found, say so explicitly so I know the check ran
   - coverage: how many blocks were anchored vs peer, and a reminder
     that prose/status contradictions were not checked by this pass

   A clean-looking report must not hide an incomplete check.
