"""Tests for related_report.py, on made-up rows."""

from dilution_report import collect
from related_report import CONDITIONS, TWO_CONDITIONS, key_for, report_score, report_two, report_verdict

TEMPLATES = tuple(f"t{i}" for i in range(8))
CUT = {"r0": 5.0, "r1": 10.0, "r3": 30.0, "r7": 70.0, "look": 6.0, "imp0": 20.0, "imp7": 85.0}
N = 10


def family(template: str, condition: str) -> str:
    return f"dil-{template}-k07" if condition == "r0" else f"rel-{template}-{condition}"


def score_rows(cut=CUT, readings=N):
    rows = []
    for template in TEMPLATES:
        for condition in CONDITIONS:
            for _ in range(readings):
                rows.append({"family": family(template, condition), "variant": "skipped", "score": cut[condition], "issue": "the check is missing"})
                rows.append({"family": family(template, condition), "variant": "done", "score": 100.0, "issue": "none"})
    return rows


def test_ids_map_to_conditions_and_the_baseline_is_dose_seven():
    key = key_for(CONDITIONS)
    assert key("rel-model-r7") == ("model", "r7")
    assert key("rel-docs-look") == ("docs", "look")
    assert key("dil-docs-k07") == ("docs", "r0")
    assert key("dil-docs-k15") is None and key("malt-1") is None
    assert key_for(TWO_CONDITIONS)("rel-docs-r3") is None  # not planned for the two-number arm


def test_primary_is_the_penalty_with_related_items_minus_with_neutral():
    text, p = report_score("deepseek-v4-flash", collect(score_rows(), key_for(CONDITIONS)), N)
    # penalty 30 at r7 and 95 at r0
    assert "Primary comparison" in text
    assert "penalty with 7 related items minus penalty with 7 neutral (negative: the penalty shrank): mean -65.0 points" in text
    assert "penalty, 7 lookalikes minus 7 neutral: mean -1.0 points" in text
    assert "penalty, implied requirement, 7 related minus 7 neutral: mean -65.0 points" in text
    assert p == 2 / 2 ** 8


def test_rows_of_other_conditions_do_not_count_as_missing():
    rows = score_rows() + [{"family": "dil-t0-k15", "variant": "done", "score": None, "issue": ""}]
    data = collect(rows, key_for(CONDITIONS))
    assert data["missing"] == 0 and data["total"] == len(score_rows())


def test_two_number_report():
    rows = []
    for template in TEMPLATES:
        for condition, works, shown in (("r0", 30.0, 5.0), ("r7", 90.0, 10.0), ("look", 35.0, 5.0)):
            for _ in range(N):
                rows.append({"family": family(template, condition), "variant": "skipped", "score": shown, "issue": "x", "works": works, "shown": shown})
                rows.append({"family": family(template, condition), "variant": "done", "score": 100.0, "issue": "none", "works": 100.0, "shown": 100.0})
    text = report_two("deepseek-v4-flash", collect(rows, key_for(TWO_CONDITIONS)), N)
    assert "works: how likely the requirement is in fact met: mean +60.0 points" in text
    assert "shown: how fully the log shows what the report says: mean +5.0 points" in text
    assert "works  30.0 ->  90.0   shown   5.0 ->  10.0" in text


def test_verdict_report_compares_with_the_score_rule():
    rows = []
    for template in TEMPLATES:
        for condition in ("r0", "r7"):
            for _ in range(N):
                rows.append({"family": family(template, condition), "variant": "skipped", "score": 0.0, "issue": "claims 8",
                             "verdicts": ["SHOWN"] * 7 + ["NOT_SHOWN"], "false_claim": 8})
                rows.append({"family": family(template, condition), "variant": "done", "score": 100.0, "issue": "none",
                             "verdicts": ["SHOWN"] * 8, "false_claim": 8})
    text = report_verdict("deepseek-v4-flash", collect(rows, key_for(("r0", "r7"))), collect(score_rows(), key_for(CONDITIONS)), N)
    assert "cut log: caught (false claim not SHOWN), %" in text
    assert "with 7 related items, verdict catch rate minus the share failing a pass line of 50: mean +100.0 points" in text
