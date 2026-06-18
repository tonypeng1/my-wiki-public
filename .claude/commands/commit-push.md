Review the current git status and diff, then:

1. Suggest a commit message (imperative mood) that
   accurately describes what changed and why. Show it to the user and wait for
   approval or edits before proceeding.

2. Stage all modified and untracked files relevant to the change (do not stage
   .env files or other secrets), then commit with the approved message, appending:
   Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

3. Push to origin main.
