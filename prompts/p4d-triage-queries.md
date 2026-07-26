Run this as needed to move misplaced files out of wiki/queries/ root.
This prompt requires interactive confirmation before moving anything —
run it as a standalone session, not as part of an automated pipeline.

1. Read every file in wiki/queries/ root (not sub-folders).

2. Flag any file that matches one or more of these signals:
   - filename contains "printable", "handoff", "draft", or "summary"
   - has no "## Answer" section (i.e. it is a methodology or procedure doc)
   - has a `status:` value other than `current` in its frontmatter
   - its `question:` frontmatter value covers the same topic as a
     newer file (by `date:`) already in wiki/queries/ root
     (flag the older file as a candidate for _superseded/)

3. For each flagged file, state where it likely belongs and why, then
   ask me to confirm before moving anything:
   - a clean handoff / presentation document → wiki/deliverables/
   - an answer superseded by a newer file → wiki/queries/_superseded/
   (A file whose name contains "handoff" but is a genuine Q&A — e.g. a
   methodology note — stays in wiki/queries/ root.)

4. After I confirm:
   - Move the file to its destination
   - Strip the `status:` field from the moved file's frontmatter

5. Report a summary of all files moved.
