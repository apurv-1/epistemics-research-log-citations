"""Draw Figure 1 from the raw readings: failing work on the score against failing it on the stated issue.

    python scripts/make_figure.py

Needs matplotlib, which this project does not depend on; use any Python that has it.
Every bar is computed by `reasons_report.tally` from `results/raw/main-<reviewer>.jsonl`.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from reasons_report import load, tally  # noqa: E402

REVIEWERS = ("gemma-4-31b-it", "qwen3.5-397b", "deepseek-v4-flash")
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BY_SCORE, BY_ISSUE = "#2a78d6", "#eb6834"  # validated as a colour-blind-safe pair on this surface
PANELS = (
    ("Unfinished work that gets failed", "higher is better", ("skipped", "raw", "")),
    ("Finished work that gets failed", "lower is better", ("done", "raw", "")),
)


def rates(model: str) -> dict:
    cells = tally(load(PROJECT / "results" / "raw" / f"main-{model}.jsonl"))
    out = {}
    for _, _, cell in PANELS:
        c = cells[cell]
        out[cell] = (100 * (c["n"] - c["passed"]) / c["n"], 100 * c["flagged_by_issue"] / c["n"])
    return out


def main() -> None:
    data = {model: rates(model) for model in REVIEWERS}
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "text.color": INK,
                         "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED})
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9), sharey=True, facecolor=SURFACE)
    width, gap = 0.30, 0.03
    for ax, (title, note, cell) in zip(axes, PANELS):
        ax.set_facecolor(SURFACE)
        for i, model in enumerate(REVIEWERS):
            by_score, by_issue = data[model][cell]
            for offset, value, colour in ((-(width + gap) / 2, by_score, BY_SCORE), ((width + gap) / 2, by_issue, BY_ISSUE)):
                ax.bar(i + offset, value, width=width, color=colour, linewidth=0, zorder=3)
                ax.text(i + offset, value + 2, f"{value:.0f}%", ha="center", va="bottom", fontsize=8, color=INK, zorder=4)
        ax.set_xticks(range(len(REVIEWERS)), [m.split("-")[0] for m in REVIEWERS])
        ax.set_ylim(0, 112)
        ax.set_yticks([0, 25, 50, 75, 100], ["0", "25", "50", "75", "100%"])
        ax.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(length=0)
        ax.set_title(title, fontsize=9.5, loc="left", color=INK, pad=14)
        ax.text(0, 1.02, note, transform=ax.transAxes, fontsize=8, color=MUTED, va="bottom")
    handles = [plt.Rectangle((0, 0), 1, 1, color=BY_SCORE), plt.Rectangle((0, 0), 1, 1, color=BY_ISSUE)]
    fig.legend(handles, ["fail if the score is under 50", "fail if the reviewer names an unsupported claim"],
               loc="lower center", ncol=2, frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    out = PROJECT / "report" / "figures"
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "score-vs-issue.png", dpi=300, facecolor=SURFACE)
    fig.savefig(out / "score-vs-issue.svg", facecolor=SURFACE)
    for model in REVIEWERS:
        print(model, {cell[0]: tuple(round(v) for v in data[model][cell]) for _, _, cell in PANELS})


if __name__ == "__main__":
    main()
