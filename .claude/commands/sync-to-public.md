Run this command and display the output verbatim:

```
bash scripts/sync-to-public.sh
```

Do not read any files. Do not diff files yourself. Just run the script and report its output.

- If the output lists "Pending deletion" items, ask the user whether to delete
  them before proceeding.
- If the output says "PRIVACY GATE: SYNC BLOCKED", stop. Report the flagged
  lines, propose a genericized rewrite of each, and apply only what the user
  approves. Never bypass or weaken the gate.
- If the CLAUDE.md review section reports a change, walk the user through the
  diff hunk by hunk (port as-is / port genericized / skip — see
  prompts/sync-to-public.md), edit the public CLAUDE.md accordingly, and only
  after the user confirms rerun with `--claude-md-reviewed`.

