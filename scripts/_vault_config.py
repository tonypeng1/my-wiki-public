#!/usr/bin/env python3
"""
Load the vault's configuration out of wiki-config.yml.

The vault's prose language is a per-vault setting, not a repo constant: the
same workflows serve a Traditional Chinese reader in Taiwan, a Simplified
Chinese reader in China, and an English-only vault with no glosses at all.
Every consumer reads the value from here at run time rather than keeping a
copy, the same way scripts/_provenance_vocab.py reads the closed provenance
vocabularies out of CLAUDE.md.

Config lives in its own file rather than a CLAUDE.md table because scripts/
ships to the public repo and CLAUDE.md deliberately does not. A checker whose
glossary path came from CLAUDE.md would have nothing to read once synced;
wiki-config.yml ships alongside the scripts and keeps them runnable standalone.

Parsed with a regex rather than PyYAML: the file is flat key/value, no script
in this repo depends on PyYAML today (frontmatter is parsed the same way), and
the checkers must run on a bare Python install.

Named _vault_config rather than _locale because `_locale` is compiled into
CPython as a built-in module: built-ins are resolved before any sys.path
search, so `import _locale` can never reach a file in this directory.

Not a CLI in normal use, but running it prints the resolved configuration,
which is the quickest way to see what a vault is set to.
"""

import re
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "wiki-config.yml"

BILINGUAL_LOCALES: frozenset[str] = frozenset({"zh-TW", "zh-CN"})
VALID_LOCALES: frozenset[str] = BILINGUAL_LOCALES | {"none"}

# Derived rather than configured, so the label cannot drift out of step with
# the locale it describes.
_LANGUAGE_NAMES: dict[str, str] = {
    "zh-TW": "Traditional Chinese (繁體中文)",
    "zh-CN": "Simplified Chinese (简体中文)",
}

_KV_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$")


class LocaleError(RuntimeError):
    """wiki-config.yml is missing, unparseable, or internally inconsistent.

    Raised rather than falling back to a default. A silent default is the
    expensive failure here: ingest writes summaries, concepts, MOCs and the
    index in one pass, so a vault that quietly assumed the wrong locale needs
    every file it touched re-glossed by hand.
    """


@lru_cache(maxsize=1)
def _config() -> dict[str, str]:
    if not CONFIG_PATH.exists():
        raise LocaleError(
            f"{CONFIG_PATH.name} not found at {CONFIG_PATH}. Every vault needs "
            "one; see the bootstrap section in README.md. It must set `locale` "
            f"to one of: {', '.join(sorted(VALID_LOCALES))}."
        )

    config: dict[str, str] = {}
    for lineno, raw in enumerate(CONFIG_PATH.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].strip() if not raw.lstrip().startswith("#") else ""
        if not line:
            continue
        match = _KV_RE.match(line)
        if not match:
            raise LocaleError(f"{CONFIG_PATH.name}:{lineno}: not a `key: value` line: {raw!r}")
        config[match.group(1)] = match.group(2).strip().strip("'\"")

    if "locale" not in config:
        raise LocaleError(f"{CONFIG_PATH.name} has no `locale:` key.")

    value = config["locale"]
    if value not in VALID_LOCALES:
        raise LocaleError(
            f"{CONFIG_PATH.name}: locale is {value!r}; expected one of "
            f"{', '.join(sorted(VALID_LOCALES))}."
        )

    has_glossary = bool(config.get("glossary"))
    if value in BILINGUAL_LOCALES:
        if not has_glossary:
            raise LocaleError(
                f"{CONFIG_PATH.name}: locale is {value!r}, which needs a "
                "`glossary:` path. A bilingual vault with no glossary would let "
                "every workflow invent its own wording for the same term."
            )
        resolved = ROOT / config["glossary"]
        if not resolved.is_file():
            raise LocaleError(
                f"{CONFIG_PATH.name}: glossary {config['glossary']!r} does not "
                f"exist (looked in {resolved})."
            )
    elif has_glossary:
        raise LocaleError(
            f"{CONFIG_PATH.name}: locale is 'none', so `glossary:` must be "
            "removed. Leaving it set suggests the vault is bilingual when no "
            "gloss will ever be written or checked."
        )

    return config


def locale() -> str:
    """The configured locale: 'zh-TW', 'zh-CN', or 'none'."""
    return _config()["locale"]


def is_bilingual() -> bool:
    """True when this vault glosses clinical terms in Chinese."""
    return locale() in BILINGUAL_LOCALES


def glossary_path() -> Path | None:
    """Absolute path to the shared glossary, or None under locale 'none'."""
    if not is_bilingual():
        return None
    return ROOT / _config()["glossary"]


def require_glossary() -> Path:
    """glossary_path() for callers that cannot proceed without one."""
    path = glossary_path()
    if path is None:
        raise LocaleError(
            f"This operation needs a glossary, but locale is {locale()!r}."
        )
    return path


def language_name() -> str | None:
    """Human-readable language label, or None under locale 'none'."""
    return _LANGUAGE_NAMES.get(locale())


def region() -> str:
    """Default care market. Documentation only; no checker enforces it."""
    return _config().get("region", "")


def skip_if_monolingual(tool: str) -> bool:
    """Print a skip notice and return True when there is nothing to check.

    Callers exit 0 on True. A glossary checker that hard-failed under locale
    'none' would break /lint, which runs all of them unconditionally.
    """
    if is_bilingual():
        return False
    print(f"{tool}: skipped (locale: {locale()} — vault carries no Chinese glosses)")
    return True


def main() -> int:
    try:
        print(f"locale:    {locale()}")
        print(f"bilingual: {is_bilingual()}")
        print(f"language:  {language_name() or '—'}")
        print(f"glossary:  {glossary_path() or '—'}")
        print(f"region:    {region() or '—'}")
    except LocaleError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
