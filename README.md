# my-wiki

A personal knowledge wiki driven by AI prompts. Raw source documents (e.g. lab results) are ingested and transformed into structured concept articles, summaries, Q&A records, and slide decks — all cross-linked using Obsidian-style `[[backlinks]]`.

## Inspiration

The structure and ideas behind this project are inspired by [Andrej Karpathy's post on LLM Knowledge Bases](https://x.com/karpathy/status/2039805659525644595) (April 2026), in which he describes using LLMs to incrementally compile a personal wiki from raw source documents — with summaries, concept articles, backlinks, Q&A, Marp slides, and health-check linting — all maintained by the LLM and viewed in Obsidian.

## Directory Structure

```
raw/              → source documents (never modify these)
wiki/
  index.md        → master index of all wiki content
  processed.log   → list of already-processed raw/ files
  summaries/      → one .md per source document
  concepts/       → one .md per concept/topic
  queries/        → saved Q&A outputs
    _handoff/     → clean versions intended to be given to someone
    _superseded/  → answers replaced by a newer query
  slides/         → Marp slide decks
  maintenance/    → health check and synthesis reports
  sessions/       → transient session scratch pad (not wiki content)
    current.md    → active session conversation (deleted on close)
    archive/      → closed sessions saved as YYYY-MM-DD.md
prompts/          → reusable AI prompt files
CLAUDE.md         → project conventions auto-loaded by Claude Code each session
INSTRUCTIONS.md   → human-readable copy of the conventions
```

## Workflows

This project runs in **Claude Code**. Workflows are invoked as slash commands — type `/` followed by the command name in the Claude Code chat, e.g. `/ingest-first`.

| Prompt | Slash Command | Purpose |
|--------|---------------|---------|
| `p1-first-ingest.md` | `/ingest-first` | Compile the wiki from scratch using all files in `raw/` |
| `p2-incremental-ingest.md` | `/ingest-increm` | Add only new files in `raw/` that haven't been processed yet |
| `p3-qa.md` | `/qa` | Answer a one-off question and save the result directly to `wiki/queries/` |
| `p3a-session-qa.md` | `/session-qa` | Ask a question inside a live session — auto-starts the session if none is active; full prior conversation is in context for each follow-up |
| `p3b-session-close.md` | `/session-close` | End the session — saves worthy Q&A turns to `wiki/queries/`, archives the session log, and cleans up |
| `p3c-session-reopen.md` | `/session-reopen` | Restore a closed session from archive back to `current.md` to continue it |
| `p4-lint.md` | `/lint` | Health check — find missing concept pages, thin articles, broken backlinks |
| `p4b-contradiction-check.md` | `/contradiction-check` | Scan wiki articles for contradictions |
| `p5-slides.md` | `/slides` | Generate a Marp slide deck on a topic from wiki content |
| `p6-weekly-synthesis.md` | `/synthesis` | Summarize what was added to the wiki this week |
| `sync-to-public.md` | `/sync-to-public` | Copy public files (prompts, commands, templates) to the companion public repo and suggest a commit message |

## Getting Started

1. Open a terminal in this directory and start Claude Code:
   ```
   claude
   ```
2. Drop source documents into `raw/`.
3. Run `/ingest-first` to build the wiki from scratch, or `/ingest-increm` to add only new files.
4. Use `/qa` to ask a one-off question. The result is saved immediately to `wiki/queries/`.
5. For a conversational session with follow-up questions:
   - Run `/session-qa your question` — the session starts automatically on the first question.
   - Keep asking follow-ups with `/session-qa your next question`; each turn is appended to `wiki/sessions/current.md` and the full history is available as context.
   - When done, run `/session-close` — it saves substantive Q&A turns to `wiki/queries/`, archives the session log to `wiki/sessions/archive/`, and removes `current.md`.
6. Run `/lint` periodically to keep the wiki healthy.
7. Use `/slides` to generate a Marp presentation on any topic covered in the wiki.

## Conventions

- All cross-references use Obsidian-style backlinks: `[[article-name]]` (filename without `.md`).
- Article formats (concept, summary, query) are defined in `CLAUDE.md` (auto-loaded by Claude Code) and mirrored in `INSTRUCTIONS.md` for human reference.
- Never edit files in `raw/` — they are the source of truth.
- `wiki/index.md` is the entry point for browsing all content.

## Git Setup

To put this folder under version control:

1. Open a terminal in this folder and initialize a git repository:
   ```
   git init
   ```
2. Create a `.gitignore` to exclude files you don't want tracked (optional but recommended):
   ```
   echo "wiki/sessions/current.md" > .gitignore
   ```
3. Stage all files and make the initial commit:
   ```
   git add .
   git commit -m "Initial commit"
   ```
4. To back it up to a remote (e.g. GitHub), create a new repository on GitHub, then:
   ```
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git branch -M main
   git push -u origin main
   ```
5. After that, commit changes as usual:
   ```
   git add .
   git commit -m "your message"
   git push
   ```

## License

MIT License
