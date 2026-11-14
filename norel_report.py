"""Described: removing related evidence from three real-log families (RELATED.md, "Related evidence removed").

    uv run python norel_report.py

It reads results and calls nothing. For each reviewer and family it compares the variant without
related evidence (`malt_norel`) with the original family (Study 1's readings with no citations):
cut-log mean score, share of cut logs flagged, share flagged and scored 50 or more, and the penalty
(full-log mean score minus cut-log mean score).
"""

from gates_report import GATEWAY, flag_and_pass, flagged, load

FAMILIES = ("malt-218367-collatz", "malt-343338-collatz", "malt-343341-fibonacci")
MODELS = ("deepseek-v4-flash", "qwen3.5-397b")


def cell(rows: list[dict], family: str) -> dict | None:
    cut = [r for r in rows if r["family"] == family and r["variant"] == "skipped"]
    full = [r for r in rows if r["family"] == family and r["variant"] == "done"]
    if not cut or not full:
        return None
    mean = lambda xs: sum(xs) / len(xs)  # noqa: E731
    return {"n": (len(cut), len(full)), "cut": mean([r["score"] for r in cut]), "full": mean([r["score"] for r in full]),
            "flag": 100 * mean([flagged(r) for r in cut]), "fp": 100 * mean([flag_and_pass(r) for r in cut])}


def main() -> None:
    raw = lambda row: row.get("condition") == "raw" and not row.get("badge")  # noqa: E731
    for model in MODELS:
        original = load(GATEWAY[model], lambda row: raw(row) and row.get("family") in FAMILIES)
        variant = load([f"norel-{model}.jsonl", f"norel-{model}-b.jsonl"], raw)
        variant = [{**r, "family": r["family"].removesuffix("-norel")} for r in variant]
        if not variant:
            continue
        print(f"== {model}: original family -> without related evidence ==")
        for family in FAMILIES:
            a, b = cell(original, family), cell(variant, family)
            if not a or not b:
                print(f"  {family}: incomplete ({len(variant)} variant readings in all)")
                continue
            print(f"  {family} (readings cut/full {a['n']} -> {b['n']})")
            print(f"    cut-log score {a['cut']:.1f} -> {b['cut']:.1f}; full-log score {a['full']:.1f} -> {b['full']:.1f}")
            print(f"    penalty {a['full'] - a['cut']:+.1f} -> {b['full'] - b['cut']:+.1f}")
            print(f"    cut logs flagged {a['flag']:.0f}% -> {b['flag']:.0f}%; flagged and scored 50 or more {a['fp']:.0f}% -> {b['fp']:.0f}%")
        print()


if __name__ == "__main__":
    main()
