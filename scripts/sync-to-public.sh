#!/usr/bin/env bash
# sync-to-public.sh — mirrors selected files from my-wiki → my-wiki-public
# Replaces the LLM-driven sync prompt to avoid ~200k token agentic loops.
set -eo pipefail

# SRC = repo root (parent of the scripts/ directory this file lives in)
SRC="$(cd "$(dirname "$0")/.." && pwd)"
# DST = sibling directory named <repo-name>-public
REPO_NAME="$(basename "$SRC")"
DST="$(dirname "$SRC")/${REPO_NAME}-public"

if [[ ! -d "$DST" ]]; then
  echo "ERROR: destination not found: $DST"
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

sync_dir() {
  local rel_dir="$1"
  local pattern="${2:-*.md}"
  local src_dir="$SRC/$rel_dir"
  local dst_dir="$DST/$rel_dir"

  # Copy new/modified files from src → dst
  if [[ -d "$src_dir" ]]; then
    mkdir -p "$dst_dir"
    while IFS= read -r -d '' f; do
      sync_file "${f#"$SRC/"}"
    done < <(find "$src_dir" -name "$pattern" -print0)
  fi

  # Detect files in dst that no longer exist in src (pending deletion)
  if [[ -d "$dst_dir" ]]; then
    while IFS= read -r -d '' f; do
      local rel="${f#"$DST/"}"
      [[ -f "$SRC/$rel" ]] || to_delete+=("$rel")
    done < <(find "$dst_dir" -name "$pattern" -print0)
  fi
}

# ── sync ───────────────────────────────────────────────────────────────────

sync_dir "prompts"
sync_dir ".claude/commands"
sync_dir "scripts" "*.sh"
sync_file "wiki/slides/_marp-template.md"
sync_file "CLAUDE.md"
sync_file "README.md"

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
for f in "${added[@]}";    do echo "- add $(basename "$f")"; done
for f in "${updated[@]}";  do echo "- update $(basename "$f")"; done
for f in "${to_delete[@]}"; do echo "- (pending) remove $(basename "$f")"; done
