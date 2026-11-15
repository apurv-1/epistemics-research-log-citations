"""Tests for main_report.py, on synthetic rows with known answers."""

import pytest

from main_report import (
    CITED_DONE, EASY_NEARMISS, LEAKS_RESULT, RAW_DONE, RAW_SKIPPED, badge_effect, bootstrap_ci, catch_rate,
    cited_skipped, collect, done_shift, holm, report_model, separation_effect, sign_flip_p, skipped_shift, summary,
)
from families import load_set
from render import POINTERS

FAMILIES = tuple(f"fam{i}" for i in range(6))


def rows_for(scores: dict, families=FAMILIES, readings=10, badge=False) -> list[dict]:
    """`scores` maps a cell to the score every reading of it gets; None means a missing reading."""
    return [
        {"family": family, "condition": cell[0], "variant": cell[1], "pointer": cell[2], "badge": badge, "score": score}
        for family in families for cell, score in scores.items() for _ in range(readings)
    ]


def base_scores(nearmiss=60.0) -> dict:
    scores = {RAW_DONE: 90.0, RAW_SKIPPED: 30.0, CITED_DONE: 88.0,
              cited_skipped("none"): 20.0, cited_skipped("unrelated"): 30.0, cited_skipped("nearmiss"): nearmiss}
    assert set(p for _, _, p in scores if p not in ("", "real")) == set(POINTERS)
    return scores


def test_separation_effect_is_cited_separation_minus_raw_separation():
    data = collect(rows_for(base_scores()))
    # cited separation 88 - 60 = 28, raw separation 90 - 30 = 60
    assert separation_effect(data, "fam0", "nearmiss") == -32.0
    assert skipped_shift(data, "fam0", "nearmiss") == 30.0


def test_a_cell_with_too_few_scores_drops_the_family():
    rows = rows_for(base_scores(), readings=9)
    assert separation_effect(collect(rows), "fam0", "nearmiss") is None


def test_missing_readings_are_counted_and_left_out():
    rows = rows_for(base_scores(), readings=12)
    for row in rows[::12]:
        row["score"] = None
    data = collect(rows)
    assert data["missing"] == len(rows) // 12
    assert separation_effect(data, "fam0", "nearmiss") == -32.0


def test_sign_flip_is_exact_and_two_sided():
    assert sign_flip_p([1.0, 2.0, 3.0]) == 2 / 8  # only all-plus and all-minus are as extreme
    assert sign_flip_p([-1.0, -2.0, -3.0]) == 2 / 8
    assert sign_flip_p([5.0, -5.0]) == 1.0
    assert sign_flip_p([]) == 1.0
    assert sign_flip_p([1.0] * 11) == 2 / 2 ** 11


def test_bootstrap_interval_brackets_the_mean_and_is_repeatable():
    values = [-30.0, -10.0, -20.0, 5.0, -15.0, -25.0]
    low, high = bootstrap_ci(values)
    assert low < sum(values) / len(values) < high
    assert bootstrap_ci(values) == (low, high)


def test_holm_is_monotone_and_capped():
    adjusted = holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adjusted == {"a": pytest.approx(0.03), "c": pytest.approx(0.06), "b": pytest.approx(0.06)}
    assert holm({"a": 0.9, "b": 0.8})["a"] == 1.0


def test_summary_can_leave_families_out():
    effects = {"fam0": -10.0, "fam1": -20.0, "fam2": 30.0, "fam3": None}
    assert summary(effects)["n"] == 3
    left = summary(effects, without=frozenset({"fam2"}))
    assert (left["n"], left["mean"], left["negative"], left["positive"]) == (2, -15.0, 2, 0)


def test_badge_effect_compares_cited_cells_with_and_without_the_line():
    plain = rows_for(base_scores(nearmiss=40.0))
    badged = rows_for({CITED_DONE: 88.0, cited_skipped("nearmiss"): 70.0}, badge=True)
    data = collect(plain + badged)
    # with the line 88 - 70 = 18, without 88 - 40 = 48
    assert badge_effect(data, "fam0") == -30.0
    assert catch_rate(data, cited_skipped("nearmiss"), badge=True) == 0.0
    assert catch_rate(data, cited_skipped("nearmiss")) == 1.0


def test_report_runs_and_marks_the_confirmatory_reviewer():
    data = collect(rows_for(base_scores()))
    text, p = report_model("deepseek-v4-flash", data)
    assert "Primary comparison" in text and p == 2 / 2 ** len(FAMILIES)
    text, _ = report_model("glm-5.2", data)
    assert "Primary comparison" not in text and "Badge line" not in text


def test_finished_logs_report_false_alarms_and_the_shift_from_real_citations():
    data = collect(rows_for({**base_scores(), RAW_DONE: 40.0, CITED_DONE: 70.0}))
    assert done_shift(data, "fam0") == 30.0
    assert catch_rate(data, RAW_DONE) == 1.0 and catch_rate(data, CITED_DONE) == 0.0
    text, _ = report_model("glm-5.2", data)
    assert "false alarms): raw 100%, cited 0%" in text
    assert "finished log with real citations minus without: mean +30.0" in text


def test_report_handles_an_empty_results_file():
    data = collect(rows_for({cell: None for cell in base_scores()}))
    text, p = report_model("deepseek-v4-flash", data)
    assert p is None and "n/a" in text


def test_flag_lists_name_real_families_and_do_not_overlap():
    ids = {family.id for family in load_set("malt")}
    assert EASY_NEARMISS <= ids and LEAKS_RESULT <= ids
    assert not EASY_NEARMISS & LEAKS_RESULT
