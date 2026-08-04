Read and execute prompts/rewrite.md.

The rewrite targets are:

$ARGUMENTS

Print each rewritten target and automatically save it back to its original path.
After saving, if one or more saved targets are under `wiki/` in a `zh-TW` or
`zh-CN` vault, read and execute `prompts/translation-backfill.md` with exactly
those saved files as its scope. Do not run that follow-up for non-wiki files or
`locale: none`.
