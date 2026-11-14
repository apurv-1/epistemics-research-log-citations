"""Draw Figure 1 from the raw readings: what share of logs fails as the pass line moves.

    python scripts/make_figure.py

Needs matplotlib, which this project does not depend on; use any Python that has it.
Every point is computed from `results/raw/main-<reviewer>.jsonl`, with no citations in the report.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from reasons_report import load  # noqa: E402

REVIEWERS = ("deepseek-v4-flash", "gemma-4-31b-it", "qwen3.5-397b")
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
CUT, FULL = "#2a78d6", "#eb6834"  # validated as a colour-blind-safe pair on this surface
LINES = list(range(50, 101, 5))


def shares(model: str) -> tuple[list[float], list[float]]:
    rows = [r for r in load(PROJECT / "results" / "raw" / f"main-{model}.jsonl") if r["condition"] == "raw"]
    cut = [r["score"] for r in rows if r["variant"] == "skipped"]
    full = [r["score"] for r in rows if r["variant"] == "done"]
    share = lambda scores, t: 100 * sum(s < t for s in scores) / len(scores)  # noqa: E731
    return [share(cut, t) for t in LINES], [share(full, t) for t in LINES]


def main() -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "text.color": INK,
                         "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED})
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.75), sharey=True, facecolor=SURFACE)
    for ax, model in zip(axes, REVIEWERS):
        cut, full = shares(model)
        ax.set_facecolor(SURFACE)
        for values, colour in ((cut, CUT), (full, FULL)):
            ax.plot(LINES, values, color=colour, linewidth=2, solid_capstyle="round", zorder=3)
            for x, y, ha, dx in ((LINES[0], values[0], "left", 1.0), (LINES[-1], values[-1], "right", -1.0)):
                ax.plot([x], [y], marker="o", markersize=5.5, color=colour, markeredgecolor=SURFACE, markeredgewidth=1.2, zorder=4)
                ax.text(x + dx, y + 4, f"{y:.0f}%", ha=ha, va="bottom", fontsize=8, color=INK, zorder=5)
        ax.set_xlim(47, 103)
        ax.set_ylim(0, 112)
        ax.set_xticks([50, 60, 70, 80, 90, 100])
        ax.set_yticks([0, 25, 50, 75, 100], ["0", "25", "50", "75", "100%"])
        ax.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(length=0)
        ax.set_title(model, fontsize=9.5, loc="left", color=INK, pad=6)
        ax.set_xlabel("pass line: work fails under this score", fontsize=8)
        print(model, "cut", [round(v) for v in cut], "full", [round(v) for v in full])
    axes[0].set_ylabel("share of logs failed", fontsize=8.5)
    handles = [plt.Line2D([0], [0], color=CUT, linewidth=2), plt.Line2D([0], [0], color=FULL, linewidth=2)]
    fig.legend(handles, ["cut logs, where one claim in the report is false", "full logs, where the report is true to the log"],
               loc="lower center", ncol=2, frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, -0.03))
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    out = PROJECT / "report" / "figures"
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "pass-line.png", dpi=300, facecolor=SURFACE)
    fig.savefig(out / "pass-line.svg", facecolor=SURFACE)


if __name__ == "__main__":
    main()
