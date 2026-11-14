"""Tests for the malt_norel set: three real-run families with their related evidence removed.

Related evidence is a passing run of the agent's own program on an input other than the reported
one. These tests read only files in the repository.
"""

import re
import tomllib
from pathlib import Path

import pytest

from families import FULL, load_family, load_set
from monitor import build_jobs

PROJECT_DIR = Path(__file__).parent.parent
NOREL_DIR = PROJECT_DIR / "data" / "families_malt_norel"
SOURCE_DIR = PROJECT_DIR / "data" / "families_malt"
NOREL = load_set("malt_norel")
SOURCES = ("malt-218367-collatz", "malt-343338-collatz", "malt-343341-fibonacci")
# A run of a program the agent wrote under /home/agent, on one input.
AGENT_RUN = re.compile(r"\./interpreter (/home/agent/\S+) (\S+)")


def by_family():
    return pytest.mark.parametrize("family", NOREL, ids=[f.id for f in NOREL])


def record(family) -> dict:
    return tomllib.loads((NOREL_DIR / f"{family.id}.toml").read_text())["norel"]


def source(family):
    return load_family(SOURCE_DIR / f"{record(family)['source']}.toml")


def passing_agent_runs_on_other_inputs(family) -> set[str]:
    """Steps that run an agent-written program, without an error, on an input other than the reported one."""
    reported = AGENT_RUN.fullmatch(family.critical.input)
    assert reported, "the critical step is a run of the agent's program"
    return {
        step.id for step in family.steps
        if (run := AGENT_RUN.fullmatch(step.input)) and run[2] != reported[2] and "error" not in step.output
    }


def test_the_set_loads_three_families_derived_from_the_named_sources():
    assert len(NOREL) == 3
    assert [record(f)["source"] for f in NOREL] == list(SOURCES)
    assert [f.id for f in NOREL] == [f"{s}-norel" for s in SOURCES]
    for family in NOREL:
        assert family.set == "malt_norel" and family.lengths == (FULL,) and family.report_source == "agent"
        assert dict(family.source)["derived_from"] == record(family)["source"]


@by_family()
def test_full_and_cut_logs_differ_in_exactly_the_source_critical_step(family):
    done, skipped = family.log("done", FULL), family.log("skipped", FULL)
    assert len(done) == len(skipped) + 1
    assert [s for s in done if s not in skipped] == [family.critical]
    assert family.critical == source(family).critical


@by_family()
def test_the_false_claim_is_the_source_false_claim_word_for_word(family):
    assert family.false_claim == source(family).false_claim
    assert family.false_claim.text in [c.text for c in family.claims]


@by_family()
def test_the_log_is_the_source_log_minus_exactly_the_recorded_steps(family):
    removed = record(family)["removed_steps"]
    original = source(family)
    assert removed and family.critical.id not in removed
    assert family.steps == tuple(s for s in original.steps if s.id not in removed)
    assert set(removed) == {s.id for s in original.steps} - {s.id for s in family.steps}
    assert family.task == original.task and family.intro == original.intro
    assert (family.nearmiss, family.unrelated) == (original.nearmiss, original.unrelated)


@by_family()
def test_every_passing_run_on_another_input_was_removed_and_nothing_else(family):
    original = source(family)
    assert not passing_agent_runs_on_other_inputs(family)
    assert passing_agent_runs_on_other_inputs(original) == set(record(family)["removed_steps"])


@by_family()
def test_every_other_claim_is_a_source_claim_and_dropped_claims_cited_only_removed_steps(family):
    original = source(family)
    removed = set(record(family)["removed_steps"])
    source_claims = {c.text: c for c in original.claims}
    for claim in family.claims:
        assert source_claims[claim.text] == claim
        assert not set(claim.cites) & removed
    dropped = record(family)["dropped_claims"]
    assert dropped == [c.text for c in original.claims if c not in family.claims]
    assert all(set(source_claims[text].cites) <= removed for text in dropped)
    assert any(not c.false_when_skipped for c in family.claims), "a true claim with a real citation is left"


@by_family()
def test_the_edit_log_names_each_removed_step_and_dropped_claim(family):
    text = (NOREL_DIR / f"{family.id}.toml").read_text()
    edits = "\n".join(tomllib.loads(text)["report"]["edits"])
    for step_id in record(family)["removed_steps"]:
        assert f"Step {step_id} is removed." in edits
    for claim in record(family)["dropped_claims"]:
        assert claim in edits


def test_the_monitor_builds_raw_pages_for_the_set():
    jobs = build_jobs(NOREL, ["raw"])
    assert len(jobs) == 2 * len(NOREL)
    assert len({j.transcript for j in jobs}) == len(jobs)


def test_the_notice_travels_with_the_copies():
    assert "metr-evals/malt-public" in (NOREL_DIR / "NOTICE.md").read_text()
