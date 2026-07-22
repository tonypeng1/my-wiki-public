Review the current git status and diff, then:

1. Suggest a commit message (imperative mood) that
   accurately describes what changed and why. Show it to the user and wait for
   approval or edits before proceeding.

2. Stage all modified and untracked files relevant to the change (do not stage
   .env files or other secrets), then commit with the approved message, appending
   a Co-Authored-By trailer that names the Claude model you are actually running
   as (do not hardcode a model — use your real identity), for example:
   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>

3. Push to origin main.
