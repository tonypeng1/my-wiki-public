#!/usr/bin/env bash
# new-vault.sh — set this vault's locale, once, before the first ingest.
#
# Usage:
#   bash scripts/new-vault.sh zh-TW      # Traditional Chinese glosses
#   bash scripts/new-vault.sh zh-CN      # Simplified Chinese glosses
#   bash scripts/new-vault.sh none       # English only, no glosses
#   bash scripts/new-vault.sh --force …  # overwrite an existing wiki-config.yml
#
# Writes wiki-config.yml, points `glossary:` at the matching shipped glossary
# (or omits it under `none`), and verifies the result with
# check-locale-consistency.py.
#
# Deliberately non-interactive: it takes the locale as an argument rather than
# prompting, so it is safe to run from an agent workflow, and one command tells
# the whole story in a transcript.
#
# It refuses to overwrite an existing wiki-config.yml without --force. Changing
# locale on a populated vault does not convert anything already written — the
# old glosses stay in whatever script they were written in, and every workflow
# then disagrees with the config. That is the failure check-locale-consistency.py
# exists to catch, and this script will not create it silently.
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="$SRC/wiki-config.yml"

FORCE=0
LOCALE=""
for arg in "$@"; do
  case "$arg" in
    --force)            FORCE=1 ;;
    zh-TW|zh-CN|none)   LOCALE="$arg" ;;
    -h|--help)
      sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *)
      echo "Unknown argument: $arg" >&2
      echo "Expected one of: zh-TW, zh-CN, none (optionally with --force)." >&2
      exit 2 ;;
  esac
done

if [[ -z "$LOCALE" ]]; then
  echo "ERROR: no locale given." >&2
  echo >&2
  echo "  bash scripts/new-vault.sh zh-TW   Traditional Chinese glosses, Taiwan wording" >&2
  echo "  bash scripts/new-vault.sh zh-CN   Simplified Chinese glosses, Mainland wording" >&2
  echo "  bash scripts/new-vault.sh none    English only, no glosses" >&2
  exit 2
fi

if [[ -f "$CONFIG" && $FORCE -eq 0 ]]; then
  current="$(sed -n 's/^locale:[[:space:]]*//p' "$CONFIG" | sed 's/[[:space:]]*#.*$//' | head -1)"
  echo "ERROR: $CONFIG already exists (locale: ${current:-unset})." >&2
  echo >&2
  echo "This vault is already configured. Re-running would change the locale of a" >&2
  echo "vault that may already hold prose, and changing locale does NOT convert" >&2
  echo "content already written — see check-locale-consistency.py." >&2
  echo >&2
  echo "If you really mean to change it, rerun with --force and then run:" >&2
  echo "  python3 scripts/check-locale-consistency.py" >&2
  exit 1
fi

case "$LOCALE" in
  zh-TW) GLOSSARY="memory/medical-term-translations-zh-tw.md"
         DESC="Traditional Chinese (繁體中文), Taiwan clinical wording" ;;
  zh-CN) GLOSSARY="memory/medical-term-translations-zh-cn.md"
         DESC="Simplified Chinese (简体中文), Mainland clinical wording" ;;
  none)  GLOSSARY=""
         DESC="English only — no glosses" ;;
esac

if [[ -n "$GLOSSARY" && ! -f "$SRC/$GLOSSARY" ]]; then
  echo "ERROR: locale $LOCALE needs $GLOSSARY, which is not in this repo." >&2
  echo "Every shipped glossary lives in memory/medical-term-translations-*.md;" >&2
  echo "if it is genuinely missing, restore it before configuring the vault." >&2
  exit 1
fi

{
  echo "# Vault configuration. See wiki-config.example.yml for what each key means,"
  echo "# and the Chinese Medical Terms section in CLAUDE.md for what locale controls."
  echo "# Written by scripts/new-vault.sh on $(date +%Y-%m-%d)."
  echo
  echo "locale: $LOCALE"
  [[ -n "$GLOSSARY" ]] && echo "glossary: $GLOSSARY"
  echo "region: TODO   # default care market, e.g. Taiwan / China / US. Documentation only."
} > "$CONFIG"

# The provenance roster is per-vault data (this patient's clinics and
# clinicians) and never syncs, so a fresh clone has only the template. Seed the
# real file from it — empty, with both table headers, which is what
# _provenance_vocab.py needs to distinguish "not set up" from "nothing added
# yet". Never overwrite an existing roster; it is hand-maintained content.
ROSTER="$SRC/memory/provenance-roster.md"
ROSTER_TEMPLATE="$SRC/memory/provenance-roster.example.md"
ROSTER_NOTE=""
if [[ ! -f "$ROSTER" && -f "$ROSTER_TEMPLATE" ]]; then
  cp "$ROSTER_TEMPLATE" "$ROSTER"
  ROSTER_NOTE="created from template (empty — add sites as documents name them)"
elif [[ -f "$ROSTER" ]]; then
  ROSTER_NOTE="already present, left untouched"
else
  ROSTER_NOTE="MISSING, and no template to copy — provenance checks will fail"
fi

echo "Wrote $CONFIG"
echo "  locale:   $LOCALE — $DESC"
echo "  glossary: ${GLOSSARY:-—}"
echo "  region:   TODO — set this to your default care market."
echo "  roster:   memory/provenance-roster.md — $ROSTER_NOTE"
echo

python3 "$SRC/scripts/check-locale-consistency.py"

echo
echo "Next: drop source documents into raw/ and run /ingest."
