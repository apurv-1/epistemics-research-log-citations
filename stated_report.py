"""Secondary: the requirement stated in five real-log families (RELATED.md, "Stated requirement on real logs").

    uv run python stated_report.py

It reads results and calls nothing. For each family it compares the variant with the requirement
stated (`malt_stated`) with the original family (Study 1's deepseek-v4-flash readings with no
citations). The planned test is the change in the share of cut-log readings flagged and scored 50
or more, stated minus original, with the one-sided exact sign-flip test over the 5 families
(prediction: it falls). Described beside it: mean scores, penalty, flag rates and discrimination
under a pass line of 50.
"""

import itertools

from gates_report import GATEWAY, RELATED_EVIDENCE, flag_and_pass, flagged, load

MODEL = "deepseek-v4-flash"


def stats(rows: list[dict], family: str) -> dict | None:
    cut = [r for r in rows if r["family"] == family and r["variant"] == "skipped"]
    full = [r for r in rows if r["family"] == family and r["variant"] == "done"]
    if not cut or not full:
        return None
    pct = lambda rs, f: 100 * sum(map(f, rs)) / len(rs)  # noqa: E731
    mean = lambda rs: sum(r["score"] for r in rs) / len(rs)  # noqa: E731
    return {"n": (len(cut), len(full)), "fp": pct(cut, flag_and_pass), "cut": mean(cut), "full": mean(full),
            "flag_cut": pct(cut, flagged), "flag_full": pct(full, flagged),
            "disc": pct(cut, lambda r: r["score"] < 50) - pct(full, lambda r: r["score"] < 50)}


def one_sided_p(diffs: list[float]) -> float:
    """Share of sign assignments whose sum is at most the observed sum (prediction: negative)."""
    observed = sum(diffs)
    hits = sum(sum(d * s for d, s in zip(diffs, signs)) <= observed + 1e-9
               for signs in itertools.product((1, -1), repeat=len(diffs)))
    return hits / 2 ** len(diffs)


def main() -> None:
    raw = lambda row: row.get("condition") == "raw" and not row.get("badge")  # noqa: E731
    original = load(GATEWAY[MODEL], lambda row: raw(row) and row.get("family") in RELATED_EVIDENCE)
    stated = load([f"stated-{MODEL}.jsonl", f"stated-{MODEL}-b.jsonl"], raw)
    stated = [{**r, "family": r["family"].removesuffix("-stated")} for r in stated]
    print(f"== {MODEL}: original family -> requirement stated ==")
    diffs, keys = [], ("fp", "cut", "full", "flag_cut", "flag_full", "disc")
    sums = {k: [0.0, 0.0] for k in keys}
    for family in sorted(RELATED_EVIDENCE):
        a, b = stats(original, family), stats(stated, family)
        if not a or not b:
            print(f"  {family}: incomplete")
            continue
        diffs.append(b["fp"] - a["fp"])
        for k in keys:
            sums[k][0] += a[k]; sums[k][1] += b[k]
        print(f"  {family} (readings cut/full {a['n']} -> {b['n']})")
        print(f"    flagged and scored 50 or more, cut logs {a['fp']:.0f}% -> {b['fp']:.0f}%")
        print(f"    cut-log score {a['cut']:.1f} -> {b['cut']:.1f}; full-log score {a['full']:.1f} -> {b['full']:.1f}; "
              f"penalty {a['full'] - a['cut']:+.1f} -> {b['full'] - b['cut']:+.1f}")
        print(f"    flagged: cut {a['flag_cut']:.0f}% -> {b['flag_cut']:.0f}%, full {a['flag_full']:.0f}% -> {b['flag_full']:.0f}%; "
              f"discrimination, pass line 50: {a['disc']:.0f} -> {b['disc']:.0f}")
    if diffs:
        n = len(diffs)
        print(f"  means over {n} families: " + "; ".join(f"{k} {v[0] / n:.1f} -> {v[1] / n:.1f}" for k, v in sums.items()))
        print(f"  planned test: flagged-and-passed change {sum(diffs) / n:+.1f} points, {sum(d < 0 for d in diffs)} of {n} families down, "
              f"one-sided sign-flip p = {one_sided_p(diffs):.4f}")


if __name__ == "__main__":
    main()
