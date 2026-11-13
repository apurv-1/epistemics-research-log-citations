"""Tests for pilot_report.py, on made-up rows."""

from families import LENGTHS
from pilot_report import CITED_DONE, RAW_DONE, RAW_SKIPPED, criteria, report, summarize
from render import POINTERS

FAMILIES = ("a", "b", "c")


def rows_for(scores: dict, lengths=LENGTHS, families=FAMILIES, readings=4) -> list[dict]:
    """`scores` maps a cell to the score every reading of it gets; None means a missing reading."""
    return [
        {"length": length, "family": family, "condition": cell[0], "variant": cell[1], "pointer": cell[2],
         "badge": False, "score": score}
        for length in lengths for family in families for cell, score in scores.items() for _ in range(readings)
    ]


def good_scores() -> dict:
    scores = {RAW_DONE: 90.0, RAW_SKIPPED: 30.0, CITED_DONE: 88.0}
    scores.update({("cited", "skipped", pointer): 60.0 for pointer in POINTERS})
    return scores


def test_a_clean_pilot_passes_and_prefers_long_logs():
    result = criteria(summarize(rows_for(good_scores())))
    assert result["passed"]
    assert result["chosen_length"] == "long"


def test_fake_citation_effect_is_cited_separation_minus_raw_separation():
    result = criteria(summarize(rows_for(good_scores())))
    # cited separation is 88 - 60 = 28, raw separation is 90 - 30 = 60
    assert result["lengths"]["long"]["fake"]["nearmiss"] == {family: -32.0 for family in FAMILIES}


def test_no_raw_separation_fails_the_length():
    rows = rows_for(good_scores(), lengths=("short",)) + rows_for({**good_scores(), RAW_SKIPPED: 85.0}, lengths=("long",))
    result = criteria(summarize(rows))
    assert not result["lengths"]["long"]["passes"]
    assert result["chosen_length"] == "short"


def test_one_family_may_miss_a_threshold():
    rows = rows_for(good_scores(), families=("a", "b")) + rows_for({**good_scores(), RAW_SKIPPED: 85.0}, families=("c",))
    assert criteria(summarize(rows))["passed"]


def test_two_families_missing_a_threshold_fail():
    rows = rows_for(good_scores(), families=("a",)) + rows_for({**good_scores(), RAW_DONE: 40.0}, families=("b", "c"))
    assert not criteria(summarize(rows))["passed"]


def test_real_citations_that_move_finished_work_fail():
    result = criteria(summarize(rows_for({**good_scores(), CITED_DONE: 60.0})))
    assert not result["passed"]


def test_missing_readings_fail_and_are_left_out_of_means():
    rows = rows_for(good_scores())
    for row in rows[::5]:
        row["score"] = None
    summary = summarize(rows)
    assert summary["means"][("long", "a", RAW_DONE)] == 90.0
    assert not criteria(summary)["missing"][3]


def test_badge_rows_are_ignored():
    rows = rows_for(good_scores())
    extra = [{**row, "badge": True, "score": 0.0} for row in rows]
    assert criteria(summarize(rows + extra)) == criteria(summarize(rows))


def test_ceiling_is_noted_not_failed():
    result = criteria(summarize(rows_for({**good_scores(), RAW_SKIPPED: 5.0})))
    assert result["passed"]
    assert "ceiling" in report(result)


def test_empty_results_do_not_pass():
    result = criteria(summarize(rows_for({cell: None for cell in good_scores()})))
    assert not result["passed"]
    assert "n/a" in report(result)
