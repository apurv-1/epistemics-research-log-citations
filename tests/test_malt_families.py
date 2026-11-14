"""Tests for the families built from real MALT runs, and for the pool they were drawn from.

These tests read only files in the repository. They do not need the MALT Parquet files.
"""

import json
import re
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from families import FULL, LENGTHS, FamilyError, Step, load_all, load_set, validate
from monitor import build_jobs
from render import POINTERS, REAL, cited, raw

PROJECT_DIR = Path(__file__).parent.parent
MALT = load_set("malt")
POOL = json.loads((PROJECT_DIR / "data" / "malt_pool.json").read_text())
REPORT_HEADING = "AGENT'S FINAL REPORT"


def by_family(name="family"):
    return pytest.mark.parametrize(name, MALT, ids=[f.id for f in MALT])


def source(family) -> dict:
    return dict(family.source)


def test_there_are_ten_to_fifteen_real_families_from_at_least_eight_tasks():
    assert 10 <= len(MALT) <= 15
    tasks = Counter(source(f)["task_id"] for f in MALT)
    assert len(tasks) >= 8
    assert max(tasks.values()) <= 2


def test_the_default_set_is_still_the_three_hand_built_families():
    assert [f.id for f in load_all()] == ["analysis", "bugfix", "review"]
    assert [f.id for f in load_set("pilot")] == ["analysis", "bugfix", "review"]
    assert len(load_set("all")) == 3 + len(MALT) + len(load_set("dilution")) + len(load_set("related")) + len(load_set("malt_norel"))


@by_family()
def test_a_real_run_has_one_length_and_no_filler(family):
    assert family.set == "malt" and family.lengths == (FULL,)
    assert not any(step.filler for step in family.steps)
    assert family.report_source == "agent"
    for length in LENGTHS:
        with pytest.raises(ValueError):
            family.log("done", length)


@by_family()
def test_the_skipped_twin_is_the_real_log_without_the_critical_step(family):
    done, skipped = family.log("done", FULL), family.log("skipped", FULL)
    assert done == family.steps
    assert skipped == tuple(step for step in done if step is not family.critical)
    assert len(done) == len(skipped) + 1


@by_family()
def test_the_report_text_is_byte_identical_across_twins(family):
    done, skipped = raw(family, "done", FULL), raw(family, "skipped", FULL)
    assert done.split(REPORT_HEADING)[1] == skipped.split(REPORT_HEADING)[1]
    assert "[step" not in done.split(REPORT_HEADING)[1]


@by_family()
def test_exactly_one_claim_rests_on_the_critical_step(family):
    false_claims = [c for c in family.claims if c.false_when_skipped]
    assert len(false_claims) == 1
    assert false_claims[0].cites == (family.critical.id,)
    assert all(family.critical.id not in c.cites for c in family.claims if not c.false_when_skipped)
    assert any(not c.false_when_skipped for c in family.claims), "the report needs a true claim with a real citation"


@by_family()
def test_every_citation_in_every_condition_resolves_to_a_step_on_the_page(family):
    pages = [(cited(family, "done", FULL, REAL, badge), len(family.steps)) for badge in (False, True)]
    pages += [(cited(family, "skipped", FULL, pointer), len(family.steps) - 1) for pointer in POINTERS]
    for page, step_count in pages:
        assert f"WORK LOG ({step_count} steps)" in page
        numbers = [int(n) for n in re.findall(r"\[step (\d+)\]", page.split(REPORT_HEADING)[1])]
        assert numbers and all(1 <= n <= step_count for n in numbers)


@by_family()
def test_fake_citation_targets_are_real_steps_that_no_claim_cites(family):
    ids = {step.id for step in family.steps}
    cited_ids = {step_id for claim in family.claims for step_id in claim.cites}
    for target in (family.nearmiss, family.unrelated):
        assert target in ids and target != family.critical.id and target not in cited_ids
    assert family.nearmiss != family.unrelated


@by_family()
def test_the_monitor_builds_six_pages_for_a_real_family(family):
    jobs = build_jobs([family])
    assert [(j.length, j.condition, j.variant, j.pointer) for j in jobs] == [
        (FULL, "raw", "done", ""), (FULL, "raw", "skipped", ""),
        (FULL, "cited", "done", REAL),
        *((FULL, "cited", "skipped", pointer) for pointer in POINTERS),
    ]
    assert len({j.transcript for j in jobs}) == 6


def test_hand_built_families_still_get_short_and_long_pages_only():
    jobs = build_jobs(load_all())
    assert len(jobs) == 36 and {j.length for j in jobs} == set(LENGTHS)


@by_family()
def test_each_file_records_where_it_came_from_and_what_was_edited(family):
    data = (PROJECT_DIR / "data" / "families_malt" / f"{family.id}.toml").read_text()
    info = source(family)
    assert info["dataset"] == "metr-evals/malt-public" and info["report_from"] in ("submit", "closing")
    assert str(info["run_id"]) in family.id
    assert "edits = [" in data and "flags = [" in data
    assert data.count("written = true") == info["written_claims"]


def test_the_validator_rejects_broken_real_families():
    family = MALT[0]
    with pytest.raises(FamilyError, match="filler"):
        validate(replace(family, steps=(*family.steps, Step("extra", "bash", "ls", "", filler=True))))
    with pytest.raises(FamilyError, match="run_id"):
        validate(replace(family, source=()))
    with pytest.raises(FamilyError, match="unknown set"):
        validate(replace(family, set="other"))
    with pytest.raises(FamilyError, match="report_source"):
        validate(replace(family, report_source="model"))
    with pytest.raises(FamilyError, match="intro"):
        validate(replace(load_all()[0], intro=""))


def test_the_pool_is_a_fixed_draw_of_one_hundred_runs():
    rule, runs = POOL["rule"], POOL["runs"]
    assert rule["seed"] == 20261113 and rule["size"] == 100 and len(runs) == 100
    assert len({run["run_id"] for run in runs}) == 100
    for run in runs:
        assert rule["steps"][0] <= run["steps"] <= rule["steps"][1]
        assert run["task_id"].split("/")[0] not in rule["excluded_task_families"]


def test_every_family_comes_from_the_pool_and_every_rejection_has_a_reason():
    by_id = {run["run_id"]: run for run in POOL["runs"]}
    for family in MALT:
        run = by_id[source(family)["run_id"]]
        assert run["decision"] == "family" and run["family"] == family.id
        assert run["task_id"] == source(family)["task_id"]
    assert sum(run["decision"] == "family" for run in POOL["runs"]) == len(MALT)
    for run in POOL["runs"]:
        assert run["decision"] in ("family", "rejected", "not examined")
        if run["decision"] == "rejected":
            assert len(run["reason"]) > 20


def test_families_follow_the_pool_order_within_each_task():
    """Within a task, every pool run ahead of a chosen run was either chosen or read and rejected."""
    seen: dict[str, list[str]] = {}
    for run in POOL["runs"]:
        earlier = seen.setdefault(run["task_id"], [])
        if run["decision"] == "family":
            assert "not examined" not in earlier, f"{run['run_id']} was chosen ahead of an unread run of its task"
        earlier.append(run["decision"])

