#!/usr/bin/env bash
# sync-to-public.sh — mirrors selected files from my-wiki → my-wiki-public
# Replaces the LLM-driven sync prompt to avoid ~200k token agentic loops.
#
# Usage:
#   bash scripts/sync-to-public.sh                       # gate, then sync
#   bash scripts/sync-to-public.sh --dry-run             # gate + report, copy nothing
#   bash scripts/sync-to-public.sh --claude-md-reviewed  # record the private
#       CLAUDE.md as reviewed after hand-porting convention changes into the
#       public copy (see the CLAUDE.md review section; works with --dry-run too)
set -eo pipefail

DRY_RUN=0
ACK_CLAUDE=0
for arg in "$@"; do
  case "$arg" in
    --dry-run)            DRY_RUN=1 ;;
    --claude-md-reviewed) ACK_CLAUDE=1 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

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

# ── allowlist ──────────────────────────────────────────────────────────────
# Everything that ships, in one place. The privacy gate scans exactly this
# set before anything is copied, so a new entry is automatically gated.
# Keep the list in prompts/sync-to-public.md in step with this one.
# Directory specs are "<dir>|<pattern>[|<pattern>…]".

SYNC_DIR_SPECS=(
  "prompts|*.md"
  ".claude/commands|*.md"
  # Codex skill wrappers around the same prompts; AGENTS.md points at these.
  ".agents/skills|*.md"
  # Python pre-filters are load-bearing for the lint/backfill prompts — sync
  # them alongside the shell helpers, or the public workflows reference
  # missing files.
  "scripts|*.sh|*.py"
)

SYNC_FILES=(
  "wiki/deliverables/_marp-template.md"
  "README.md"
  "AGENTS.md"
  # Permission allowlist for the synced scripts (settings.local.json stays private).
  ".claude/settings.json"
  # Locale config TEMPLATE, not this vault's live wiki-config.yml. Shipping the
  # real one would hand every new clone locale: zh-TW pre-set, which silently
  # defeats the p1-ingest step 0 gate: a maintainer who wants Simplified and
  # skips the README would get a Traditional vault with nothing asking them.
  # A clone with no wiki-config.yml trips the gate instead, which is the point.
  "wiki-config.example.yml"
  # Provenance roster TEMPLATE — both table headers, zero rows. The filled-in
  # memory/provenance-roster.md is this patient's real clinics and clinicians
  # and never ships; see scripts/_provenance_vocab.py.
  "memory/provenance-roster.example.md"
  # Keeps __pycache__/*.pyc out of the public repo now that .py files ship.
  ".gitignore"
  # Normalizes line endings (LF) in the public repo too, and keeps the
  # README's .gitattributes reference accurate there.
  ".gitattributes"
  # README hero image (safe to publish: only the benign 'lipid-panel' node
  # is legible).
  "docs/graph-view.png"
  # README concept-article example (safe to publish: entirely fabricated —
  # no real patient data, see §10.2 in README.md).
  "docs/concept-example.png"
)

# EVERY glossary ships, not just the one this vault is configured for. A public
# clone has to be able to become any locale the system supports, and shipping
# only the configured one made that impossible: this vault is zh-TW, so the
# public repo carried no Simplified glossary at all and a zh-CN user's
# `glossary:` path resolved to a file that was never published.
#
# Glossaries are the ONLY memory/ files that ship. The public repo's
# memory/MEMORY.md is a hand-written stub, and the private index's entry titles
# alone name the patient and their diagnoses. Never add memory/MEMORY.md — or a
# sync_dir over memory/ — to the lists above. They are appended by glob rather
# than listed inline so a new locale's glossary ships the day it is created.
shopt -s nullglob
for glossary in "$SRC"/memory/medical-term-translations*.md; do
  SYNC_FILES+=("memory/$(basename "$glossary")")
done
shopt -u nullglob

if [[ ${#SYNC_FILES[@]} -eq 0 ]]; then
  echo "ERROR: no files to sync — the allowlist came out empty." >&2
  exit 1
fi

# CLAUDE.md is deliberately NOT in either list. The private copy documents
# conventions with the patient's real medications and conditions as examples,
# and drifts back to them even after cleanups (ce2e982 genericized the
# examples; 158539c reintroduced the real drugs three days later). The public
# copy is hand-maintained instead: identical conventions, fictional examples.
# The CLAUDE.md review section at the end of this script flags private
# changes for manual porting and records each review in
# .sync-claude-md-reviewed (a private snapshot, also never synced).

added=()
updated=()
to_delete=()

# ── helpers ────────────────────────────────────────────────────────────────

# find_matches <abs_dir> <pattern...> — NUL-delimited files matching any pattern
find_matches() {
  local dir="$1"; shift
  local patterns=("$@")
  local find_expr=(\()
  local i
  for i in "${!patterns[@]}"; do
    [[ $i -eq 0 ]] || find_expr+=(-o)
    find_expr+=(-name "${patterns[$i]}")
  done
  find_expr+=(\))
  find "$dir" "${find_expr[@]}" -print0
}

sync_file() {
  local rel="$1"
  local src_file="$SRC/$rel"
  local dst_file="$DST/$rel"

  [[ -f "$src_file" ]] || return 0

  if [[ ! -f "$dst_file" ]]; then
    if [[ $DRY_RUN -eq 0 ]]; then
      mkdir -p "$(dirname "$dst_file")"
      cp "$src_file" "$dst_file"
    fi
    added+=("$rel")
  elif ! diff -q "$src_file" "$dst_file" > /dev/null 2>&1; then
    [[ $DRY_RUN -eq 0 ]] && cp "$src_file" "$dst_file"
    updated+=("$rel")
  fi
}

# sync_dir <rel_dir> <pattern ...>
sync_dir() {
  local rel_dir="$1"; shift
  local src_dir="$SRC/$rel_dir"
  local dst_dir="$DST/$rel_dir"
  local f rel

  # Copy new/modified files from src → dst
  if [[ -d "$src_dir" ]]; then
    [[ $DRY_RUN -eq 0 ]] && mkdir -p "$dst_dir"
    while IFS= read -r -d '' f; do
      sync_file "${f#"$SRC/"}"
    done < <(find_matches "$src_dir" "$@")
  fi

  # Detect files in dst that no longer exist in src (pending deletion)
  if [[ -d "$dst_dir" ]]; then
    while IFS= read -r -d '' f; do
      rel="${f#"$DST/"}"
      [[ -f "$SRC/$rel" ]] || to_delete+=("$rel")
    done < <(find_matches "$dst_dir" "$@")
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
    [[ "$rel" == "CLAUDE.md" ]] && continue  # hand-maintained, never synced
    [[ -f "$SRC/$rel" ]] || to_delete+=("$rel")
  done < <(git -C "$DST" ls-files -- '*.md' 2>/dev/null)
}

# ── privacy gate (fail-closed) ─────────────────────────────────────────────
# Derives patient-identifying terms from the vault at run time — medication
# generic names (basenames of medication-tagged concepts), their brand /
# local-brand-name field values, the patient's Chinese name(s) from
# memory/patient-name.md, and the facility / physician rosters out of
# memory/provenance-roster.md — then refuses to sync if any allowlisted file, or
# either hand-maintained public file (CLAUDE.md, memory/MEMORY.md), contains
# one. The list is derived rather than hardcoded for two reasons: a literal
# list here would itself leak (this script ships to the public repo), and a
# derived one cannot go stale when a medication is added. Clinical vocabulary
# (analyte names, conditions) is deliberately NOT denied — the shared
# glossary legitimately contains it as dictionary entries.
#
# Matching: ASCII terms match whole words, case-insensitively; CJK terms
# match as substrings (Chinese has no word boundaries). A brand that is also
# a common English word (checked against /usr/share/dict/words) cannot be
# word-gated without permanent false positives in legitimate prose — such a
# term is skipped with a notice, and the drug stays protected by its generic
# name, which is always gated.
run_privacy_gate() {
  local ascii_terms=()
  local cjk_terms=()
  local skipped=()
  local f v tok line

  for f in "$SRC"/wiki/concepts/*.md; do
    grep -q '^tags:.*medication' "$f" 2>/dev/null || continue
    ascii_terms+=("$(basename "$f" .md)")
    while IFS= read -r line; do
      v="$(echo "${line#*:}" | sed 's/#.*//; s/^[[:space:]]*//; s/[[:space:]]*$//')"
      [[ -n "$v" ]] || continue
      if LC_ALL=C grep -q '[^ -~]' <<< "$v"; then
        cjk_terms+=("$v")
      elif grep -qixF "$v" /usr/share/dict/words 2>/dev/null; then
        skipped+=("$v")
      else
        ascii_terms+=("$v")
        # Multi-word values (a class prefix plus the brand): gate the
        # distinctive tokens too, so the bare brand cannot slip through.
        for tok in $v; do
          [[ ${#tok} -ge 4 ]] || continue
          if ! grep -qixF "$tok" /usr/share/dict/words 2>/dev/null; then
            ascii_terms+=("$tok")
          fi
        done
      fi
    done < <(grep -h '^brand:\|^local-brand-name:' "$f")
  done

  if [[ -f "$SRC/memory/patient-name.md" ]]; then
    while IFS= read -r v; do
      cjk_terms+=("$v")
    done < <(perl -CSD -ne 'print "$1\n" while /(\p{Han}{3,})/g' \
               "$SRC/memory/patient-name.md" | sort -u)
  fi

  # Facility and physician rosters. They live only in memory/provenance-roster.md,
  # which never syncs, so that the two provenance checkers can ship without them
  # — see scripts/_provenance_vocab.py. Deriving them here closes the loop: the
  # loader stops a roster being written into a file that ships, and this stops
  # one being pasted back.
  #
  # Both checkers did carry hardcoded rosters, Chinese names included, and this
  # gate passed them on every run, because medications were the only thing it
  # knew to look for. A denylist that covers one category of identifier reads
  # as protection while providing none.
  local kind term vocab_terms
  if ! vocab_terms="$(python3 -c '
import sys
sys.path.insert(0, sys.argv[1] + "/scripts")
import _provenance_vocab as v
a, c = v.identifying_terms()
for t in a: print("ascii\t" + t)
for t in c: print("cjk\t" + t)
' "$SRC" 2>&1)"; then
    echo "=== PRIVACY GATE: SYNC BLOCKED ==="
    echo "Could not derive the facility/physician denylist from the roster:"
    echo
    printf '  %s\n' "$vocab_terms"
    echo
    echo "That list is what keeps the patient's clinics and clinicians out of the"
    echo "public repo, so the sync stops rather than running without it. Repair the"
    echo "tables in memory/provenance-roster.md — or _provenance_vocab.py — and"
    echo "rerun. Do not work around this by skipping the derivation."
    exit 1
  fi

  while IFS=$'\t' read -r kind term; do
    [[ -n "$term" ]] || continue
    if [[ "$kind" == "cjk" ]]; then
      cjk_terms+=("$term")
    elif [[ "$term" != *" "* ]] && grep -qixF "$term" /usr/share/dict/words 2>/dev/null; then
      skipped+=("$term")
    else
      ascii_terms+=("$term")
    fi
  done <<< "$vocab_terms"

  # An EMPTY roster is valid for a vault that has ingested nothing — that is
  # the state scripts/new-vault.sh leaves behind, and _provenance_vocab.py
  # accepts it. It is NOT valid for a vault that already holds summaries: a
  # vault with source documents has facilities, so a roster naming none means
  # the file was emptied or clobbered, and proceeding would ship those
  # documents with no facility/physician denylist at all. Fail closed.
  local summary_count
  summary_count="$(find "$SRC/wiki/summaries" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')"
  if [[ "$vocab_terms" == "" && "${summary_count:-0}" -gt 0 ]]; then
    echo "=== PRIVACY GATE: SYNC BLOCKED ==="
    echo "memory/provenance-roster.md yielded no facilities or physicians, but this"
    echo "vault has $summary_count summaries. A vault with source documents has clinics;"
    echo "an empty roster means the file was emptied or clobbered, and syncing now"
    echo "would ship with no facility/physician denylist. Restore the roster and rerun."
    exit 1
  fi

  if [[ ${#ascii_terms[@]} -eq 0 && ${#cjk_terms[@]} -eq 0 ]]; then
    echo "Privacy gate: no denylist derivable (no medication concepts found) — skipped."
    return 0
  fi

  # Scan set: every file the allowlist can ship, plus the hand-maintained
  # public files a porting slip could contaminate.
  local scan=()
  local spec
  while IFS= read -r -d '' f; do scan+=("$f"); done < <(
    for spec in "${SYNC_DIR_SPECS[@]}"; do
      IFS='|' read -ra parts <<< "$spec"
      if [[ -d "$SRC/${parts[0]}" ]]; then
        find_matches "$SRC/${parts[0]}" "${parts[@]:1}"
      fi
    done
    for f in "${SYNC_FILES[@]}"; do
      [[ -f "$SRC/$f" ]] && printf '%s\0' "$SRC/$f"
    done
    for f in "CLAUDE.md" "memory/MEMORY.md"; do
      [[ -f "$DST/$f" ]] && printf '%s\0' "$DST/$f"
    done
    true
  )

  local grep_ascii=() grep_cjk=()
  for v in "${ascii_terms[@]}"; do grep_ascii+=(-e "$v"); done
  for v in "${cjk_terms[@]}"; do grep_cjk+=(-e "$v"); done

  local hits="" h
  for f in "${scan[@]}"; do
    h="$(grep -inwHIF "${grep_ascii[@]}" "$f" 2>/dev/null || true)"
    [[ -n "$h" ]] && hits="${hits}${h}"$'\n'
    if [[ ${#grep_cjk[@]} -gt 0 ]]; then
      h="$(grep -inHIF "${grep_cjk[@]}" "$f" 2>/dev/null || true)"
      [[ -n "$h" ]] && hits="${hits}${h}"$'\n'
    fi
  done

  if [[ -n "$hits" ]]; then
    echo "=== PRIVACY GATE: SYNC BLOCKED ==="
    echo "Patient-identifying terms found in files that would ship (or in the"
    echo "hand-maintained public copies). Nothing was copied."
    echo
    printf '%s' "$hits" | sed "s|^$SRC/|  |; s|^$DST/|  [public] |"
    echo
    echo "Genericize the flagged lines, then rerun. If a hit is a false"
    echo "positive, adjust the derivation in run_privacy_gate() — do not"
    echo "bypass the gate."
    exit 1
  fi

  echo "Privacy gate: $(( ${#ascii_terms[@]} + ${#cjk_terms[@]} )) terms checked across ${#scan[@]} files — clean."
  if [[ ${#skipped[@]} -gt 0 ]]; then
    echo "  (skipped as common English words, still covered by generic names: ${skipped[*]})"
  fi
}

# ── CLAUDE.md review ───────────────────────────────────────────────────────
# .sync-claude-md-reviewed snapshots the private CLAUDE.md as of the last
# hand-port review. While it matches, the public copy is presumed current;
# when it differs, the cumulative diff is printed for porting. Only
# --claude-md-reviewed updates the snapshot — printing the diff does not
# count as a review.
claude_md_review() {
  local snap="$SRC/.sync-claude-md-reviewed"
  echo
  echo "=== CLAUDE.md review (never synced; public copy is hand-maintained) ==="
  if [[ $ACK_CLAUDE -eq 1 ]]; then
    cp "$SRC/CLAUDE.md" "$snap"
    echo "Recorded the current private CLAUDE.md as reviewed."
    return 0
  fi
  if [[ ! -f "$snap" ]]; then
    echo "No review snapshot found. After confirming the public CLAUDE.md"
    echo "reflects current conventions, record the baseline with:"
    echo "  bash scripts/sync-to-public.sh --claude-md-reviewed"
    return 0
  fi
  if diff -q "$snap" "$SRC/CLAUDE.md" > /dev/null 2>&1; then
    echo "Private CLAUDE.md unchanged since the last review."
  else
    echo "Private CLAUDE.md has CHANGED since the last review. Cumulative diff:"
    echo
    diff -u "$snap" "$SRC/CLAUDE.md" || true
    echo
    echo "Port convention changes into $DST/CLAUDE.md by hand — genericize any"
    echo "patient-specific example — then acknowledge with:"
    echo "  bash scripts/sync-to-public.sh --claude-md-reviewed"
  fi
}

# ── sync ───────────────────────────────────────────────────────────────────

run_privacy_gate

for spec in "${SYNC_DIR_SPECS[@]}"; do
  IFS='|' read -ra parts <<< "$spec"
  sync_dir "${parts[@]}"
done
for f in "${SYNC_FILES[@]}"; do
  sync_file "$f"
done

check_orphan_root_docs

# Glossaries ship by glob from SYNC_FILES, which only ever copies — so a
# glossary renamed or retired in this repo would linger in the public one
# forever. sync_dir does this for the directories it mirrors; memory/ is not
# one, deliberately, because only the glossaries there may ship.
check_orphan_glossaries() {
  [[ -d "$DST/.git" ]] || return 0
  local rel
  while IFS= read -r rel; do
    [[ -f "$SRC/$rel" ]] || to_delete+=("$rel")
  done < <(git -C "$DST" ls-files -- 'memory/medical-term-translations*.md' 2>/dev/null)
}
check_orphan_glossaries

# ── report ─────────────────────────────────────────────────────────────────

echo
if [[ ${#added[@]} -eq 0 && ${#updated[@]} -eq 0 && ${#to_delete[@]} -eq 0 ]]; then
  echo "Already in sync. Nothing to do."
else
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "=== Sync Summary (dry run — nothing was copied) ==="
  else
    echo "=== Sync Summary ==="
  fi
  for f in "${added[@]}";     do echo "  Added:            $f"; done
  for f in "${updated[@]}";   do echo "  Updated:          $f"; done
  for f in "${to_delete[@]}"; do echo "  Pending deletion (NOT deleted): $f"; done

  echo
  echo "=== Suggested git commit message ==="
  echo "feat: sync from my-wiki"
  echo
  for f in "${added[@]}";     do echo "- add $(label "$f")"; done
  for f in "${updated[@]}";   do echo "- update $(label "$f")"; done
  for f in "${to_delete[@]}"; do echo "- (pending) remove $(label "$f")"; done
fi

claude_md_review
