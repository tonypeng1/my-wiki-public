#!/usr/bin/env python3
"""
Guard the vault's locale against the content already written under it.

Two failures this catches, both of which are otherwise diagnosed only by an
avalanche of unrelated-looking findings from check-bilingual-terms.py:

  1. wiki-config.yml is missing, unparseable, or internally inconsistent.
     Delegated to scripts/_vault_config.py, which raises with the fix named.

  2. The configured locale disagrees with the prose. Flipping `locale` in a
     populated vault does NOT convert anything already written — it only
     changes what gets written next. A zh-TW vault relabelled zh-CN keeps
     every Traditional gloss it had, and the glossary checker then flags
     essentially every article at once, which reads like the checker broke
     rather than like the config changed.

Script detection uses two character sets derived from this repo's own two
glossaries, which are the same 1232 terms written in both scripts — an
aligned corpus. Deriving the pairs positionally is not enough on its own:
same-length *relocalizations* look exactly like simplifications. `Pregnancy`
is 懷孕 in Taiwan and 妊娠 in Mainland usage, which would wrongly mark 妊 and
娠 as Simplified-only when both are ordinary Traditional characters.

Three filters fix that. A pair is kept only when the Simplified character is
the *dominant* mapping of the Traditional one and occurs more than once — a
relocalization is a one-off minority mapping, a real simplification is
consistent. Characters appearing on both sides of any pair are dropped. And a
Traditional-only character must never appear anywhere in the zh-CN glossary,
nor a Simplified-only character anywhere in the zh-TW glossary.

The result is a heuristic, not a complete Unihan table, and it does not need
to be: this check asks which script *dominates*, not whether a file is pure.
One irreducible case is worth knowing about — Simplified merges 誌 into 志,
but 志 is also an ordinary Traditional character (it appears in names), so it
cannot be classified cleanly either way. Residual noise of this kind runs well
under a percent on a real vault, against a 15% threshold.

Detection is deliberately about the DOMINANT script, not any occurrence: a
zh-TW vault may legitimately quote a Mainland source, and a Review Queue note
may discuss the other script's wording. Only a majority in the wrong script
means the vault and its config have diverged.

Exit code is 1 when the config is invalid or the content contradicts it,
otherwise 0. An empty vault is clean under any locale — that is the state a
fresh clone is supposed to be in.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _vault_config  # noqa: E402

ROOT = Path(__file__).parent.parent
DEFAULT_PATHS = [
    ROOT / "wiki" / "concepts",
    ROOT / "wiki" / "summaries",
    ROOT / "wiki" / "mocs",
    ROOT / "wiki" / "queries",
    ROOT / "wiki" / "deliverables",
    ROOT / "wiki" / "index.md",
    ROOT / "wiki" / "home.md",
]

TRAD_ONLY = frozenset(
    "乾亞併候傳傷兒內劑動區品單圍圖報塊壓套學完實對導層島師張強後復徵惡態慮憂應披抽損據攝數斷時晝極構標樞機橫檢權殘氣減測準溫滯漿潛潤濃為無營狀狹現異療癇癲發監盤確礙積穩窩竇節範篩紅紙級細結絞統絲經維線緩縮總織續纖脈脫腎腦腫腸膚膽膿臟臨與葉藥號術裝複視覺觀觸計訊記診試誌認調謝證變負貧費質蹤輸轉迴追連週進運過邊醫醯釋鈉鈣錄鎮鏡鐵長閉間閾關陰隨險雙離難電霍靜音項預頸頻顆顎顏類顯顱顳風飽養餘驗體鬆鬱鹼鹽點黴"
)
SIMP_ONLY = frozenset(
    "与临为亚传伤体余信儿关养内准减剂动区医单压双发变叶号后围图块声备复学实对导层岛师并应异张强录征志态总恶报损据数断无时昼显术机权松极构枢标检横残气浆测浓润温滞潜点状狭现电疗痫癫盐监盘确碍碱离积稳窝窦筛类红纤级纸线组细织经结绞统续维综缓缩肠肤肾肿胆脉脏脑脓脱节范药营虑观视觉触计认记设访证诊试调谢负质贫费转输过运进连郁酰采释钙钠铁镇镜长闭间阈阴险随难静项预颅颈颌频颗颞风饱验"
)

# Below this many script-exclusive characters the vault has too little Chinese
# to judge — a fresh or nearly empty vault, which is clean under any locale.
MIN_SIGNAL = 50
# A minority script below this share is noise (a quoted source, a review note),
# not evidence that the vault was written in it.
NOISE_SHARE = 0.15


def iter_markdown_files(paths: list[Path]) -> list[Path]:
    files: set[Path] = set()
    for path in paths:
        if path.is_file() and path.suffix == ".md":
            files.add(path.resolve())
        elif path.is_dir():
            for md_file in path.rglob("*.md"):
                files.add(md_file.resolve())
    return sorted(files)


def count_scripts(files: list[Path]) -> tuple[Counter[str], dict[Path, tuple[int, int]]]:
    totals: Counter[str] = Counter()
    per_file: dict[Path, tuple[int, int]] = {}
    for md_file in files:
        text = md_file.read_text(encoding="utf-8")
        t = sum(1 for ch in text if ch in TRAD_ONLY)
        s = sum(1 for ch in text if ch in SIMP_ONLY)
        if t or s:
            per_file[md_file] = (t, s)
        totals["trad"] += t
        totals["simp"] += s
    return totals, per_file


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check that the configured locale matches the vault's content."
    )
    parser.add_argument(
        "paths", nargs="*", help="Markdown files or directories. Defaults to wiki content."
    )
    args = parser.parse_args()

    # --- check 1: the config itself loads -----------------------------------
    try:
        locale = _vault_config.locale()
    except _vault_config.LocaleError as exc:
        print("LOCALE CONFIG INVALID")
        print(f"  {exc}")
        return 1
    print(f"locale: {locale}  ({_vault_config.language_name() or 'English only'})")

    # --- check 2: the content agrees with it --------------------------------
    scan_paths = [Path(p).resolve() for p in args.paths] if args.paths else DEFAULT_PATHS
    files = iter_markdown_files(scan_paths)
    totals, per_file = count_scripts(files)
    trad, simp = totals["trad"], totals["simp"]
    signal = trad + simp

    print(f"content: {len(files)} file(s) scanned; "
          f"{trad} Traditional-only, {simp} Simplified-only character(s).")

    if signal < MIN_SIGNAL:
        print("OK — too little Chinese to judge; any locale is consistent with this vault.")
        return 0

    dominant = "zh-TW" if trad > simp else "zh-CN"
    minority_share = min(trad, simp) / signal

    if locale == "none":
        print("MISMATCH — locale is 'none' but the vault carries Chinese prose.")
        print("  An English-only vault should have no glosses. Either set locale back to")
        print(f"  {dominant}, or strip the existing glosses; switching the config does not")
        print("  remove them.")
        _report_files(per_file, "zh-TW" if dominant == "zh-CN" else "zh-CN")
        return 1

    if dominant != locale:
        print(f"MISMATCH — locale is {locale} but the prose is predominantly {dominant}.")
        print("  Changing locale does not convert content already written. Either set")
        print(f"  locale back to {dominant}, or re-gloss the vault into {locale} before")
        print("  ingesting anything further.")
        _report_files(per_file, locale)
        return 1

    if minority_share > NOISE_SHARE:
        print(f"WARNING — {minority_share:.0%} of script-exclusive characters are not "
              f"{locale}.")
        print("  Above the noise threshold for quoted sources and review notes. Worth a")
        print("  look, but not treated as a mismatch.")
        _report_files(per_file, locale)
        return 0

    print(f"OK — content is consistent with locale {locale}.")
    return 0


def _report_files(per_file: dict[Path, tuple[int, int]], expected: str, limit: int = 15) -> None:
    """List the files carrying the most characters of the unexpected script."""
    wrong_index = 1 if expected == "zh-TW" else 0
    ranked = sorted(per_file.items(), key=lambda kv: kv[1][wrong_index], reverse=True)
    ranked = [(f, c) for f, c in ranked if c[wrong_index] > 0][:limit]
    if not ranked:
        return
    label = "Simplified" if expected == "zh-TW" else "Traditional"
    print(f"\n  Files with the most {label}-only characters:")
    for md_file, counts in ranked:
        print(f"    {counts[wrong_index]:>6}  {md_file.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    raise SystemExit(main())
