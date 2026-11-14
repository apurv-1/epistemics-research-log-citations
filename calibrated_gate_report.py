"""Exploratory: does one calibration procedure pick a gate that beats a pass line of 50 on every reviewer?

    uv run python calibrated_gate_report.py

It reads results and calls nothing. For each reviewer and each of the 11 real-log families with no
citations, the gate is chosen on the other 10 families, as the candidate with the highest mean
discrimination there, and is then scored on the held-out family. Candidates: fail if the score is
under T, for T in 10, 20, ..., 100; fail any flagged reading; fail if flagged or the score is under T.
The held-out discrimination is compared with a pass line of 50 by the two-sided exact sign-flip
test over families. Designed after every gate result in this repository was read.
"""

from gates_report import compare, discrimination, flagged, reviewers

LINES = range(10, 101, 10)
CANDIDATES = {f"score < {t}": (lambda r, t=t: r["score"] < t) for t in LINES}
CANDIDATES["flagged"] = flagged
CANDIDATES.update({f"flagged or score < {t}": (lambda r, t=t: flagged(r) or r["score"] < t) for t in LINES})


def main() -> None:
    for name, (rows, _) in reviewers().items():
        if not rows:
            continue
        table = {label: discrimination(rows, gate) for label, gate in CANDIDATES.items()}
        families = sorted(table["flagged"])
        held, chosen = {}, []
        for family in families:
            train = lambda label: sum(v for f, v in table[label].items() if f != family) / (len(families) - 1)  # noqa: E731
            best = max(CANDIDATES, key=train)
            chosen.append(best)
            held[family] = table[best][family]
        base = table["score < 50"]
        picks = sorted(set(chosen), key=chosen.count, reverse=True)
        print(f"== {name} ==")
        print(f"  gates chosen: " + ", ".join(f"{p} ({chosen.count(p)})" for p in picks))
        print(f"  held-out discrimination {sum(held.values()) / len(held):.0f}; pass line 50: {sum(base.values()) / len(base):.0f}")
        print(f"  calibrated minus pass line 50: {compare(held, base)}")
        print()


if __name__ == "__main__":
    main()
