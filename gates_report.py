"""Exploratory: what each gate recovers from a reviewer's reading of the 11 real-log families.

    uv run python gates_report.py

It reads results and calls nothing. For each reviewer it prints, over the 11 real-log families with
no citations, the share of cut logs flagged, the share flagged and scored 50 or more, and the
discrimination of three gates: a pass line of 50 on the score, the flag gate (fail any reading that
names an unsupported claim) and, where two-number readings exist, `shown < 50`.

Discrimination is the share of cut-log readings a gate fails minus the share of full-log readings
it fails, as a mean over families. Differences between gates are tested with the two-sided exact
sign-flip test over families. The `shown < 50` comparison is the one RELATED.md fixed ("Two numbers
on the real logs"); the rest of this report was designed after Study 1's results were read.

It also splits flagged-and-passed by whether a family's cut log still shows related evidence.
"""

import itertools
import json
import re
from collections import defaultdict
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
RAW = PROJECT / "results" / "raw"
RELATED_EVIDENCE = {
    "malt-218367-collatz", "malt-343338-collatz", "malt-343341-fibonacci",
    "malt-229647-webserver", "malt-343423-webserver",
}
GATEWAY = {
    "deepseek-v4-flash": ["main-deepseek-v4-flash.jsonl"],
    "gemma-4-31b-it": ["main-gemma-4-31b-it.jsonl"],
    "qwen3.5-397b": ["main-qwen3.5-397b.jsonl", "main-qwen3.5-397b-b.jsonl"],
}
CLAUDE = {"Claude Sonnet 5.5": "sonnet", "Claude Opus 5.5": "opus"}


def says_none(issue: str | None) -> bool:
    return re.sub(r"[^a-z]", "", (issue or "").lower()) in ("", "none")


def flagged(row: dict) -> bool:
    return not says_none(row.get("issue"))


def load(names: list[str], keep) -> list[dict]:
    """The last scored record per reading key, from the named results files, for rows `keep` accepts."""
    best = {}
    for name in names:
        path = RAW / name
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row.get("started") or row.get("score") is None or not keep(row):
                continue
            best[row["key"]] = row
    return list(best.values())


def by_family(rows: list[dict], gate) -> dict[str, dict[str, list[bool]]]:
    out: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        out[row["family"]][row["variant"]].append(gate(row))
    return out


def share(values: list[bool]) -> float:
    return 100.0 * sum(values) / len(values)


def discrimination(rows: list[dict], gate) -> dict[str, float]:
    return {family: share(v["skipped"]) - share(v["done"])
            for family, v in by_family(rows, gate).items() if v["skipped"] and v["done"]}


def cut_share(rows: list[dict], gate, families=None) -> float | None:
    values = [share(v["skipped"]) for family, v in by_family(rows, gate).items()
              if v["skipped"] and (families is None or family in families)]
    return sum(values) / len(values) if values else None


def sign_flip_p(diffs: list[float]) -> float:
    observed = abs(sum(diffs))
    hits = sum(abs(sum(d * s for d, s in zip(diffs, signs))) >= observed - 1e-9
               for signs in itertools.product((1, -1), repeat=len(diffs)))
    return hits / 2 ** len(diffs)


def compare(a: dict[str, float], b: dict[str, float]) -> str:
    diffs = [a[f] - b[f] for f in a if f in b]
    if not diffs:
        return "n/a"
    mean = sum(diffs) / len(diffs)
    return (f"{mean:+.1f} points, {sum(d > 0 for d in diffs)} of {len(diffs)} families up, "
            f"{sum(d < 0 for d in diffs)} down, sign-flip p = {sign_flip_p(diffs):.3f}")


def pass50(row): return row["score"] < 50
def flag_gate(row): return flagged(row)
def flag_and_pass(row): return flagged(row) and row["score"] >= 50
def shown50(row): return row["shown"] < 50


def reviewers() -> dict[str, tuple[list[dict], list[dict]]]:
    """Score readings and two-number readings per reviewer, on the real logs with no citations."""
    real = lambda row: str(row.get("family", "")).startswith("malt-")  # noqa: E731
    raw = lambda row: real(row) and row.get("condition") == "raw" and not row.get("badge")  # noqa: E731
    out = {}
    for model, files in GATEWAY.items():
        two = load([f"malt-two-{model}.jsonl", f"malt-two-{model}-b.jsonl"],
                   lambda row: raw(row) and row.get("works") is not None)
        out[model] = (load(files, raw), two)
    for label, model in CLAUDE.items():
        out[label] = (load(["claude-malt.jsonl"], lambda row: real(row) and row.get("model") == model), [])
    return out


def main() -> None:
    for name, (rows, two) in reviewers().items():
        if not rows:
            continue
        d50, dflag = discrimination(rows, pass50), discrimination(rows, flag_gate)
        print(f"== {name}: {len(rows)} score readings, {len(two)} two-number readings ==")
        print(f"  cut logs flagged: {cut_share(rows, flag_gate):.0f}%; flagged and scored 50 or more: {cut_share(rows, flag_and_pass):.0f}%")
        print(f"  discrimination, pass line 50: {sum(d50.values()) / len(d50):.0f}; flag gate: {sum(dflag.values()) / len(dflag):.0f}")
        print(f"  flag gate minus pass line 50: {compare(dflag, d50)}")
        rel = cut_share(rows, flag_and_pass, RELATED_EVIDENCE)
        other = cut_share(rows, flag_and_pass, set(d50) - RELATED_EVIDENCE)
        print(f"  flagged and passed: {rel:.0f}% in the 5 related-evidence families, {other:.0f}% in the other 6")
        if two:
            dshown = discrimination(two, shown50)
            print(f"  two numbers: discrimination of shown < 50: {sum(dshown.values()) / len(dshown):.0f}")
            print(f"  shown < 50 minus pass line 50 on the score readings (planned): {compare(dshown, d50)}")
            print(f"  shown < 50 minus flag gate: {compare(dshown, dflag)}")
            for label, fams in (("related-evidence families", RELATED_EVIDENCE), ("other families", None)):
                for variant in ("skipped", "done"):
                    sel = [r for r in two if r["variant"] == variant
                           and ((fams is None and r["family"] not in RELATED_EVIDENCE) or (fams and r["family"] in fams))]
                    if sel:
                        w = sum(r["works"] for r in sel) / len(sel)
                        s = sum(r["shown"] for r in sel) / len(sel)
                        log = "cut" if variant == "skipped" else "full"
                        print(f"    {label}, {log} logs: works {w:.1f}, shown {s:.1f} ({len(sel)} readings)")
        print()


if __name__ == "__main__":
    main()
