#!/usr/bin/env bash
# Search wiki/index.md for entries matching one or more keywords.
# Each matching entry block (## heading + its bullet lines) is printed in full.
# Usage: ./scripts/search-index.sh KEYWORD [KEYWORD2 ...]
# Example: ./scripts/search-index.sh lipid statin

set -euo pipefail

if [[ $# -eq 0 ]]; then
    echo "Usage: $0 KEYWORD [KEYWORD2 ...]" >&2
    exit 1
fi

INDEX="$(dirname "$0")/../wiki/index.md"

if [[ ! -f "$INDEX" ]]; then
    echo "Error: index not found at $INDEX" >&2
    exit 1
fi

# Build a single grep pattern: keyword1|keyword2|...
pattern=$(IFS='|'; echo "$*")

awk -v pat="$pattern" '
    /^## .*\.md$/ {
        # Article entry heading — start a new block
        if (block != "" && matched) print block "\n"
        block = $0
        matched = 0
        next
    }
    /^## / {
        # Non-article section (e.g. Compilation Summary, domain headings) — flush and ignore
        if (block != "" && matched) print block "\n"
        block = ""
        matched = 0
        next
    }
    /^$/ {
        if (block != "" && matched) print block "\n"
        block = ""
        matched = 0
        next
    }
    block != "" {
        block = block "\n" $0
        if (!matched && tolower($0) ~ tolower(pat)) matched = 1
    }
    END {
        if (block != "" && matched) print block
    }
' "$INDEX"
