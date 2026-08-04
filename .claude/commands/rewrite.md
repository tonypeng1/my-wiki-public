Read and execute prompts/rewrite.md.

The rewrite targets are:

$ARGUMENTS

After the rewrite, only if the user asked to save changes and one or more saved
targets are under `wiki/` in a `zh-TW` or `zh-CN` vault, read and execute
`prompts/translation-backfill.md` with exactly those saved files as its scope.
Do not run that follow-up for output-only rewrites, non-wiki files, or
`locale: none`.
