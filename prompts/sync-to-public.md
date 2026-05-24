Sync public files from /Users/tony3/Documents/my-wiki to /Users/tony3/Documents/my-wiki-public.

The public repo mirrors only these files/directories:
- prompts/          (all .md files)
- .claude/commands/ (all .md files)
- wiki/slides/_marp-template.md
- CLAUDE.md
- README.md

Follow these steps:

1. For each file/directory above, diff the source (my-wiki) against the
   destination (my-wiki-public). Identify:
   - Modified files (content differs)
   - New files (exist in my-wiki but not in my-wiki-public)
   - Deleted files (exist in my-wiki-public but not in my-wiki) — list
     these but do NOT delete without asking the user first.

2. If there are no differences, report "Already in sync." and stop.

3. Copy all modified and new files from my-wiki to my-wiki-public,
   preserving directory structure.

4. Report a summary of what was changed:
   - List each file as Added, Updated, or Pending deletion

5. Suggest a git commit message for the my-wiki-public repo in this format:

   feat: sync from my-wiki

   - <one line per changed file describing what changed>

   Keep each bullet concise and specific (e.g. "add p3c-session-reopen.md",
   "fix archive naming in p3b", not just "update p3b").
