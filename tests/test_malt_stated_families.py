"""Tests for the malt_stated set: five real-run families whose task states its acceptance requirement.

The only content change from each source is one sentence appended to the task text. These tests
read only files in the repository.
"""

import re
import tomllib
from pathlib import Path

import pytest

from families import FULL, load_family, load_set
from monitor import build_jobs

PROJECT_DIR = Path(__file__).parent.parent
STATED_DIR = PROJECT_DIR / "data" / "families_malt_stated"
SOURCE_DIR = PROJECT_DIR / "data" / "families_malt"
STATED = load_set("malt_stated")
SOURCES = ("malt-218367-collatz", "malt-229647-webserver", "malt-343338-collatz",
           "malt-343341-fibonacci", "malt-343423-webserver")
OPENING = "The task is done only when "


def by_family():
    return pytest.mark.parametrize("family", STATED, ids=[f.id for f in STATED])


def record(family) -> dict:
    return tomllib.loads((STATED_DIR / f"{family.id}.toml").read_text())["stated"]


def source(family):
    return load_family(SOURCE_DIR / f"{record(family)['source']}.toml")


def test_the_set_loads_five_families_derived_from_the_named_sources():
    assert len(STATED) == 5
    assert sorted(record(f)["source"] for f in STATED) == list(SOURCES)
    assert sorted(f.id for f in STATED) == [f"{s}-stated" for s in SOURCES]
    for family in STATED:
        assert family.set == "malt_stated" and family.lengths == (FULL,) and family.report_source == "agent"
        assert dict(family.source)["derived_from"] == record(family)["source"]


@by_family()
def test_steps_report_and_critical_step_equal_the_source(family):
    original = source(family)
    assert family.steps == original.steps
    assert family.critical == original.critical
    assert family.claims == original.claims and family.false_claim == original.false_claim
    assert family.intro == original.intro
    assert (family.nearmiss, family.unrelated) == (original.nearmiss, original.unrelated)


@by_family()
def test_full_and_cut_logs_differ_in_exactly_the_critical_step(family):
    done, skipped = family.log("done", FULL), family.log("skipped", FULL)
    assert [s for s in done if s not in skipped] == [family.critical]
    assert len(done) == len(skipped) + 1


@by_family()
def test_the_task_is_the_source_task_plus_exactly_one_sentence(family):
    original = source(family).task
    sentence = record(family)["sentence"]
    raw = tomllib.loads((STATED_DIR / f"{family.id}.toml").read_text())["task"]
    raw_source = tomllib.loads((SOURCE_DIR / f"{record(family)['source']}.toml").read_text())["task"]
    assert raw == raw_source.rstrip("\n") + "\n\n" + sentence + "\n"
    assert family.task == original + "\n\n" + sentence
    assert sentence.startswith(OPENING) and sentence.endswith(".")
    assert sentence.count(". ") == 0 and "\n" not in sentence
    assert sentence not in original


@by_family()
def test_the_sentence_does_not_point_at_the_cut(family):
    sentence = record(family)["sentence"]
    critical_digits = set(re.findall(r"\d", family.critical.input))
    assert critical_digits, "the critical step has an input"
    assert not set(re.findall(r"\d", sentence)) & critical_digits
    assert not re.search(r"\b(step|steps|report|log|agent)\b", sentence, re.IGNORECASE)


@by_family()
def test_the_edit_log_names_the_added_sentence(family):
    edits = "\n".join(tomllib.loads((STATED_DIR / f"{family.id}.toml").read_text())["report"]["edits"])
    assert record(family)["sentence"] in edits
    assert record(family)["reason"]


def test_the_monitor_builds_raw_pages_for_the_set():
    jobs = build_jobs(STATED, ["raw"])
    assert len(jobs) == 2 * len(STATED)
    assert len({j.transcript for j in jobs}) == len(jobs)


def test_the_notice_travels_with_the_copies():
    assert "metr-evals/malt-public" in (STATED_DIR / "NOTICE.md").read_text()
