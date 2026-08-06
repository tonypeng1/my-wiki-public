Use this workflow when repairing missing Chinese medical-term translations in
existing wiki content.

This workflow exists only for Chinese locales. If `locale` in `wiki-config.yml`
is `none`, the vault carries no glosses to repair — report that and stop.

1. Determine the scope.
   Accepted scope forms:
   - a domain or MOC area (for example: hepatic, glycemic, lipid)
   - a concept family
   - specific files
   - the files already touched in the current batch

   If the user supplied a scope, work only on that scope.

   If the user invoked this workflow without a scope, choose the next
   reasonable backfill batch yourself:
   - prefer one coherent domain-sized batch, not a cross-repo scattershot pass
   - inspect `wiki/mocs/` and `wiki/index.md` to identify candidate domains
   - prefer domains where the glossary already has good coverage and where a
     modest batch can be completed cleanly in one pass
   - avoid immediately reusing a domain that was just completed unless the user
     explicitly asks for a re-check
   - use the checker script on candidate files as a ranking aid, then choose
     the domain with the clearest concentration of likely bilingual misses

   Report the chosen scope before editing if you had to select it yourself.

2. Before editing, read:
   - `AGENTS.md`
   - `CLAUDE.md`
   - `memory/MEMORY.md`
   - the glossary named by `glossary:` in `wiki-config.yml`

3. Assemble the candidate file set:
   - source files explicitly in scope
   - concept or summary files already touched in the current batch
   - if the scope is a domain, use the relevant MOC file to gather the
     concept and summary members of that domain batch
   - mirror files that may need synchronized wording:
     - `wiki/index.md`
     - relevant `wiki/mocs/*.md`
     - `wiki/home.md` if MOC rows or summary wording change

4. Seed the candidate worklist by running both scripts on the scoped files:
   - `python3 scripts/check-bilingual-terms.py PATH [PATH ...]` — flags terms
     already in the glossary that lack a translation.
   - `python3 scripts/extract-term-candidates.py PATH [PATH ...]` — surfaces
     acronyms and "Phrase (ACRONYM)" definitions, including ones NOT in the
     glossary (the class the checker is structurally blind to).
   Treat both as a floor, not a ceiling: they only catch dictionary terms and
   pattern-detectable candidates. You are expected to find and translate terms
   neither script flags — that is what Pass A below is for.

5. Edit the source files with a two-pass find that separates *noticing* every
   candidate term from *translating* it, so low-salience terms sitting next to
   already-translated ones are not lost to a single inline read. Apply the
   Chinese Medical Terms policy in CLAUDE.md (single source of truth)
   for what to translate, first-mention handling, abbreviations, exclusions, and
   glossary inclusion. For every summary or concept in scope:

   Pass A — enumerate, do not translate yet. Start from the step-4 worklist, then
   read the file unit by unit (each paragraph, bullet, table cell, impression
   line, open-question line) and add the terms the scripts cannot detect:
   lowercase and multi-word clinical terms such as "sleep pressure" or "arousal
   threshold". Coverage over judgment — if a span might be clinical, add it.

   Pass B — disposition every row of the worklist (walk the list, not the prose).
   Resolve each term PER OCCURRENCE within its counting unit, because the policy
   requires translating the FIRST *and* the SECOND occurrence in each unit — not
   only the first. The counting unit is the innermost heading section (`##`, or
   `###` when used); for `wiki/index.md` it is each Compilation Summary paragraph
   and each `## {file}.md` entry block. Query files keep the more aggressive
   CLAUDE.md exception. Give each occurrence exactly one outcome:
   - translate here — reuse the glossary 中文, or translate and add a glossary
     entry. This covers the first occurrence in the unit AND, whenever the term
     recurs, the second occurrence too (maximum two translations per term per
     unit);
   - third-or-later occurrence in the unit — leave as plain English/abbreviation;
   - intentional English — proper noun or opaque identifier; note why;
   - unsure of the wording for this locale — leave English, add to the glossary
     Review Queue.
   A `[[backlink]]` is English and never counts as an occurrence. An occurrence
   left without an outcome is unfinished work. Batch new glossary entries at the
   end of Pass B so they insert in alphabetical order before the QA steps.

6. Update mirror files after the source-file edits.
   Synchronize any changed wording into:
   - `wiki/index.md` summary lines for touched files
   - the relevant MOC entries and relationship prose
   - `wiki/home.md` only if this batch changes MOC coverage or article counts

7. Run diff-scoped bilingual QA on the edited files:
   - `python3 scripts/check-bilingual-terms.py --git-diff PATH [PATH ...]`
   Review each reported line, patch real misses, and rerun until the remaining
   hits are intentional exceptions or low-confidence false positives. Then run one
   whole-file pass as the final gate (no --git-diff):
   - `python3 scripts/check-bilingual-terms.py PATH [PATH ...]`
   This surfaces in-glossary terms left untranslated on lines your edits did not
   touch, which the diff-scoped run filters out; confirm the remaining hits are
   only known intentional exceptions. A hit suffixed `(2nd)` means the term
   occurs twice or more in one counting unit but carries fewer than two
   translations — patch the missing second occurrence (backlinks do not count).

8. Run diff-scoped medication-format QA on the edited files:
   - `python3 scripts/check-medication-first-mentions.py --git-diff PATH [PATH ...]`
   Review each reported line, patch missing `generic (Brand, local name)`
   first-mention formatting, and rerun until the remaining hits are intentional
   exceptions or medications that do not yet have a reliable brand/local-name
   mapping in the repo.

9. Run a diff-scoped glossary-delta pass on the same edited files:
   - `python3 scripts/check-glossary-delta.py --git-diff PATH [PATH ...]`
   Review each reported inline `English (中文)` pair. Add reusable standalone
   clinical terms to the glossary configured in `wiki-config.yml`, leave one-off
   patient- or sentence-specific phrases inline only, and rerun until no
   unreviewed reusable candidates remain.

10. Run structural QA after all translations and mirror updates are final:
   - `python3 scripts/check-moc-key-relationships.py --git-diff PATH [PATH ...]`
     checks any relationship prose this batch edited for the one-paragraph,
     2-3-sentence contract and misplaced open-question/action language. Patch
     and rerun until clean.
   - `python3 scripts/check-markdown-layout.py --git-diff PATH [PATH ...]`
     flags paragraphs or list items that are manually hard-wrapped. Rejoin each
     onto one physical source line and let Obsidian soft-wrap it. This must run
     after gloss insertion so translations cannot lengthen only selected source
     lines. Patch and rerun until clean.
   - `python3 scripts/check-mirror-drift.py --git-diff PATH [PATH ...]`
     is the failure signal for step 6, which otherwise has none. It flags an
     article whose prose this batch changed while its `## {file}.md` block in
     `wiki/index.md` or its MOC bullet did not. Fix by editing the named lines
     only — never by rewriting a mirror file, whose Compilation Summary is
     append-only and whose Key Relationships prose has its own contract. Rerun
     until clean, or state which flagged mirror legitimately needed no change
     and why. The check is satisfied by any edit to the mirror, so it proves
     the mirror was touched, not that it was synchronized correctly.

11. Report:
   - scope reviewed
   - files changed
   - glossary entries added
   - any deliberately deferred or ambiguous translation choices
   - MOC relationship, Markdown layout, and mirror-drift check results
   - the mirror files updated in step 6, named individually — a step with no
     artifact of its own is the one that goes missing, so report it explicitly
     even when the answer is "none needed"
