---
name: commit-push-codex
description: Review the current git diff, propose a commit message, wait for approval, then commit and push Codex-authored changes with a Codex co-author trailer. Use when the user asks for commit-push-codex or wants Codex to commit and push current work.
---

# Commit Push Codex

Mirror the Claude `/commit-push` workflow with Codex-specific attribution.

Steps:

1. Review the current git status and diff.
2. Suggest an imperative-mood commit message that accurately describes what
   changed and why. Show it to the user and wait for approval or edits before
   proceeding.
3. Stage modified and untracked files relevant to the approved change. Do not
   stage `.env` files, secrets, unrelated user changes, or generated files that
   should remain untracked.
4. Commit with the approved message, appending this trailer:

   ```text
   Co-Authored-By: Codex <noreply@openai.com>
   ```

5. Push to `origin main`.

If the working tree contains unrelated changes, leave them unstaged and mention
them to the user. If push fails, report the exact failure and do not retry with
destructive git operations.
