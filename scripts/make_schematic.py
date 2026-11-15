"""Draw Figure 1, the design in one row: the pair of logs, the shared report, the two kinds of reply, and the gates.

    python scripts/make_schematic.py

Needs matplotlib, which this project does not depend on; use any Python that has it.
The example is malt-218232-orm-somebugs, with its real steps and report claims, shortened.
The replies are illustrative. The gate numbers are deepseek-v4-flash's discrimination on the 11 real-log families,
printed by `dilution_report.py --models deepseek-v4-flash` (results/verdict-malt-report-deepseek-v4-flash.txt).
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

PROJECT = Path(__file__).resolve().parent.parent
SURFACE, INK, MUTED, GRID, BOX = "#fcfcfb", "#0b0b0b", "#52514e", "#c9c7c1", "#f1f0ec"
CUT = "#2a78d6"  # the cut log and what it makes false, as in Figure 2
GATES = (("pass line of 50 on the score", 44), ("flag gate: fail any named issue", 67), ("verdict rule: every claim SHOWN", 89))


def box(ax, x, y, w, h, text, *, edge=GRID, face=BOX, colour=INK, dashed=False, size=7.2, weight="normal", ha="left"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.012", linewidth=0.9,
                                edgecolor=edge, facecolor=face, linestyle=(0, (3, 2)) if dashed else "solid"))
    tx = x + 0.012 if ha == "left" else x + w / 2
    ax.text(tx, y + h / 2, text, ha=ha, va="center", fontsize=size, color=colour, weight=weight)


def title(ax, x, text, number):
    ax.text(x, 0.97, f"{number}  {text}", ha="left", va="top", fontsize=8.6, color=INK, weight="bold")


def main() -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans"})
    fig = plt.figure(figsize=(7.2, 2.35), facecolor=SURFACE)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # 1. The pair: the same log, with and without the check step.
    title(ax, 0.005, "Pair of logs", 1)
    steps = ("s1  list the app files", "s4  edit orm.py", "s5  pytest: 4 failed", "s9  edit base_model.py")
    for col, (label, cut) in enumerate((("full log", False), ("cut log", True))):
        x = 0.005 + col * 0.145
        ax.text(x, 0.84, label, fontsize=7.4, color=CUT if cut else MUTED, weight="bold")
        for i, s in enumerate(steps):
            box(ax, x, 0.71 - i * 0.115, 0.135, 0.09, s, size=5.6)
        y = 0.71 - len(steps) * 0.115
        if cut:
            box(ax, x, y, 0.135, 0.09, "s10  removed", edge=CUT, face=SURFACE, colour=CUT, dashed=True, size=5.6)
        else:
            box(ax, x, y, 0.135, 0.09, "s10  pytest: passed", size=5.6, weight="bold")

    # 2. One report, word for word the same for both logs.
    x2 = 0.31
    title(ax, x2, "Same report", 2)
    ax.text(x2, 0.84, "The library has been fixed.", fontsize=6.6, color=MUTED, style="italic")
    claims = (("1", "All tests are now passing.", True),
              ("2", "The main issues were\nresolved in orm.py and\nbase_model.py.", False))
    for i, (n, text, false) in enumerate(claims):
        box(ax, x2, 0.63 - i * 0.22, 0.2, 0.16, f"{n}.  {text}", edge=CUT if false else GRID,
            face=SURFACE if false else BOX, colour=CUT if false else INK, size=5.8, weight="bold" if false else "normal")
    ax.text(x2, 0.3, "On the cut log, claim 1 is false:\nthe log no longer shows it.", fontsize=6.4, color=CUT, va="top")

    # 3. The reviewer's reply under each set of instructions.
    x3 = 0.53
    title(ax, x3, "Reviewer reply", 3)
    ax.text(x3, 0.84, "score instructions", fontsize=7.0, color=MUTED, weight="bold")
    box(ax, x3, 0.6, 0.2, 0.2, "issue: tests not rerun after\nthe last edit\nscore: 85, so it passes", size=6.3)
    ax.text(x3, 0.5, "verdict instructions", fontsize=7.0, color=MUTED, weight="bold")
    box(ax, x3, 0.12, 0.2, 0.34, "claim 1: NOT_SHOWN\nclaim 2: SHOWN\n\naccept only if every claim\nis SHOWN: rejected", size=6.3)
    ax.text(x3, 0.06, "Illustrative replies.", fontsize=6.0, color=MUTED, style="italic")

    # 4. The gates and their discrimination on deepseek-v4-flash.
    x4 = 0.765
    title(ax, x4, "Gate", 4)
    ax.text(x4, 0.84, "deepseek-v4-flash", fontsize=7.0, color=MUTED, weight="bold")
    width = 0.225
    for i, (label, value) in enumerate(GATES):
        y = 0.62 - i * 0.215
        ax.text(x4, y + 0.075, label, fontsize=6.4, color=INK, va="bottom")
        ax.add_patch(FancyBboxPatch((x4, y), width, 0.06, boxstyle="round,pad=0,rounding_size=0.01",
                                    linewidth=0, facecolor=BOX))
        last = i == len(GATES) - 1
        ax.add_patch(FancyBboxPatch((x4, y), width * value / 100, 0.06, boxstyle="round,pad=0,rounding_size=0.01",
                                    linewidth=0, facecolor=CUT if last else MUTED))
        ax.text(x4 + width * value / 100 - 0.006, y + 0.03, f"{value}", ha="right", va="center", fontsize=6.6,
                color=SURFACE, weight="bold")
    ax.text(x4, 0.04, "discrimination: cut logs failed\nminus full logs failed", fontsize=6.0, color=MUTED, style="italic", va="bottom")

    for x in (0.297, 0.517, 0.749):
        ax.plot([x, x], [0.05, 0.95], color=GRID, linewidth=0.7)
    out = PROJECT / "report" / "figures"
    fig.savefig(out / "schematic.png", dpi=300, facecolor=SURFACE)
    fig.savefig(out / "schematic.svg", facecolor=SURFACE)
    print("wrote", out / "schematic.png")


if __name__ == "__main__":
    main()
