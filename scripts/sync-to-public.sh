#!/usr/bin/env bash
# sync-to-public.sh — mirrors selected files from my-wiki → my-wiki-public
# Replaces the LLM-driven sync prompt to avoid ~200k token agentic loops.
set -eo pipefail

# SRC = repo root (parent of the scripts/ directory this file lives in)
SRC="$(cd "$(dirname "$0")/.." && pwd)"
# DST = sibling directory named <repo-name>-public
REPO_NAME="$(basename "$SRC")"
DST="$(dirname "$SRC")/${REPO_NAME}-public"

# This script ships to the public repo, where running it would look for a
# nonsensical <name>-public-public. Explain that instead of a path error.
if [[ "$REPO_NAME" == *-public ]]; then
  echo "Nothing to do: this is the public repo ($REPO_NAME)."
  echo
  echo "sync-to-public.sh is maintainer-only. It runs in the private source repo"
  echo "and copies files OUT to this one; there is no upstream to sync from here."
  echo "See the /sync-to-public row in README.md."
  exit 0
fi

if [[ ! -d "$DST" ]]; then
  echo "ERROR: destination not found: $DST"
  echo "Expected a sibling directory of $SRC named ${REPO_NAME}-public."
  exit 1
fi

added=()
updated=()
to_delete=()

# ── helpers ────────────────────────────────────────────────────────────────

sync_file() {
  local rel="$1"
  local src_file="$SRC/$rel"
  local dst_file="$DST/$rel"

  [[ -f "$src_file" ]] || return 0

  mkdir -p "$(dirname "$dst_file")"

  if [[ ! -f "$dst_file" ]]; then
    cp "$src_file" "$dst_file"
    added+=("$rel")
  elif ! diff -q "$src_file" "$dst_file" > /dev/null 2>&1; then
    cp "$src_file" "$dst_file"
    updated+=("$rel")
  fi
}

# sync_dir <rel_dir> [pattern ...] — defaults to *.md when no pattern is given
sync_dir() {
  local rel_dir="$1"; shift
  local patterns=("$@")
  [[ ${#patterns[@]} -gt 0 ]] || patterns=("*.md")
  local src_dir="$SRC/$rel_dir"
  local dst_dir="$DST/$rel_dir"

  # Build a find expression: \( -name p1 -o -name p2 ... \)
  local find_expr=(\()
  local i
  for i in "${!patterns[@]}"; do
    [[ $i -eq 0 ]] || find_expr+=(-o)
    find_expr+=(-name "${patterns[$i]}")
  done
  find_expr+=(\))

  # Copy new/modified files from src → dst
  if [[ -d "$src_dir" ]]; then
    mkdir -p "$dst_dir"
    while IFS= read -r -d '' f; do
      sync_file "${f#"$SRC/"}"
    done < <(find "$src_dir" "${find_expr[@]}" -print0)
  fi

  # Detect files in dst that no longer exist in src (pending deletion)
  if [[ -d "$dst_dir" ]]; then
    while IFS= read -r -d '' f; do
      local rel="${f#"$DST/"}"
      [[ -f "$SRC/$rel" ]] || to_delete+=("$rel")
    done < <(find "$dst_dir" "${find_expr[@]}" -print0)
  fi
}

# Commit-message label. Bare basenames collide (every Codex skill is SKILL.md,
# and each command shares its prompt's filename), so qualify those two cases.
label() {
  local rel="$1"
  case "$rel" in
    .agents/skills/*/SKILL.md) echo "$(basename "$(dirname "$rel")") Codex skill" ;;
    .claude/commands/*)        echo "$(basename "$rel" .md) command" ;;
    *)                         basename "$rel" ;;
  esac
}

# Flag tracked top-level docs in dst that no longer exist in src.
# sync_dir only sees directories it mirrors, so stray root files went unnoticed.
check_orphan_root_docs() {
  [[ -d "$DST/.git" ]] || return 0
  local rel
  while IFS= read -r rel; do
    [[ "$rel" == */* ]] && continue          # top-level only
    [[ "$rel" == .* ]] && continue           # dotfiles handled explicitly
    [[ -f "$SRC/$rel" ]] || to_delete+=("$rel")
  done < <(git -C "$DST" ls-files -- '*.md' 2>/dev/null)
}

# ── sync ───────────────────────────────────────────────────────────────────

sync_dir "prompts"
sync_dir ".claude/commands"
# Codex skill wrappers around the same prompts; AGENTS.md points at these.
sync_dir ".agents/skills"
# Python pre-filters are load-bearing for the lint/backfill prompts — sync them
# alongside the shell helpers, or the public workflows reference missing files.
sync_dir "scripts" "*.sh" "*.py"
sync_file "wiki/slides/_marp-template.md"
sync_file "CLAUDE.md"
sync_file "README.md"
sync_file "AGENTS.md"
# Permission allowlist for the synced scripts (settings.local.json stays private).
sync_file ".claude/settings.json"
# Shared glossary: check-bilingual-terms.py, check-glossary-delta.py and
# extract-term-candidates.py all default to this path.
sync_file "memory/medical-term-translations.md"
# Keeps __pycache__/*.pyc out of the public repo now that .py files ship.
sync_file ".gitignore"
# Normalizes line endings (LF) in the public repo too, and keeps the README's
# .gitattributes reference accurate there.
sync_file ".gitattributes"

check_orphan_root_docs

# ── report ─────────────────────────────────────────────────────────────────

if [[ ${#added[@]} -eq 0 && ${#updated[@]} -eq 0 && ${#to_delete[@]} -eq 0 ]]; then
  echo "Already in sync. Nothing to do."
  exit 0
fi

echo "=== Sync Summary ==="
for f in "${added[@]}";    do echo "  Added:            $f"; done
for f in "${updated[@]}";  do echo "  Updated:          $f"; done
for f in "${to_delete[@]}"; do echo "  Pending deletion (NOT deleted): $f"; done

echo ""
echo "=== Suggested git commit message ==="
echo "feat: sync from my-wiki"
echo ""
for f in "${added[@]}";    do echo "- add $(label "$f")"; done
for f in "${updated[@]}";  do echo "- update $(label "$f")"; done
for f in "${to_delete[@]}"; do echo "- (pending) remove $(label "$f")"; done
