"""Tests for the constructed families of the dilution experiment.

Each template is one task with a single acceptance check and 15 other pieces of verified work.
A condition keeps the first k other pieces, or keeps one and pads the log with routine steps.
"""

import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

import pytest

from families import DILUTION_FAMILIES_DIR, FULL, FamilyError, load_set, validate
from monitor import build_jobs
from render import raw

PROJECT_DIR = Path(__file__).parent.parent
DILUTION = load_set("dilution")
CONDITIONS = ("k01", "k03", "k07", "k15", "pad")
DOSES = {"k01": 1, "k03": 3, "k07": 7, "k15": 15}
REPORT_HEADING = "AGENT'S FINAL REPORT\n"
NUMBER = re.compile(r"\d+(?:\.\d+)?")
SETUP_STEPS = 3
PAD_STEPS = 14

TEMPLATES = defaultdict(dict)
for _family in DILUTION:
    _, _template, _condition = _family.id.split("-")
    TEMPLATES[_template][_condition] = _family

by_family = pytest.mark.parametrize("family", DILUTION, ids=[f.id for f in DILUTION])
by_template = pytest.mark.parametrize("template", sorted(TEMPLATES))


def report_of(page: str) -> str:
    return page.split(REPORT_HEADING, 1)[1]


def other_claims(family):
    return family.claims[:-1]


def step_ids(family, prefix: str) -> list[str]:
    return [s.id for s in family.steps if s.id.startswith(prefix)]


def test_there_are_eight_templates_with_all_five_conditions():
    assert len(DILUTION) == 40
    assert len(TEMPLATES) == 8
    for template, families in TEMPLATES.items():
        assert tuple(sorted(families)) == CONDITIONS, template


@by_family
def test_the_id_names_the_template_and_the_condition(family):
    assert re.fullmatch(r"dil-[a-z]+-(k01|k03|k07|k15|pad)", family.id)
    assert family.set == "dilution" and family.report_source == "written"
    source = dict(family.source)
    assert family.id == f"dil-{source['template']}-{source['condition']}"
    assert source["other_claims"] == len(other_claims(family))
    assert source["routine_steps"] == len(step_ids(family, "p"))


@by_family
def test_a_dilution_family_has_one_length_and_no_filler(family):
    assert family.lengths == (FULL,)
    assert not any(step.filler for step in family.steps)


@by_family
def test_the_false_claim_is_last_and_its_check_is_the_last_step_before_the_close(family):
    assert family.false_claim is family.claims[-1]
    assert family.false_claim_number == len(family.claims)
    assert family.critical is family.steps[-2]
    assert family.critical.id == "accept" and family.steps[-1].id == "close"
    assert family.false_claim.cites == ("accept",)


@by_family
def test_the_two_logs_differ_in_exactly_the_acceptance_step(family):
    done, skipped = family.log("done", FULL), family.log("skipped", FULL)
    assert len(done) == len(skipped) + 1
    assert [s for s in done if s not in skipped] == [family.critical]
    assert [s for s in done if s is not family.critical] == list(skipped)


@by_family
def test_the_report_is_the_same_text_for_both_logs(family):
    done, skipped = raw(family, "done", FULL), raw(family, "skipped", FULL)
    assert report_of(done) == report_of(skipped)
    assert done != skipped
    for numbered in (False, True):
        assert report_of(raw(family, "done", FULL, numbered=numbered)) == report_of(raw(family, "skipped", FULL, numbered=numbered))


@by_family
def test_every_other_claim_rests_on_its_own_step_and_stays_true_on_the_cut_log(family):
    cites = [claim.cites for claim in other_claims(family)]
    assert all(len(c) == 1 for c in cites)
    assert [c[0] for c in cites] == step_ids(family, "w")  # one claim per work step, in log order
    shown = {s.id for s in family.log("skipped", FULL)}
    assert all(c[0] in shown for c in cites)


@by_family
def test_the_report_states_no_number_that_only_the_acceptance_step_shows(family):
    elsewhere = family.task + "".join(s.input + s.output for s in family.steps if not s.critical)
    only_there = set(NUMBER.findall(family.critical.output)) - set(NUMBER.findall(elsewhere))
    assert not only_there & set(NUMBER.findall(report_of(raw(family, "skipped", FULL))))


@by_family
def test_the_task_states_the_acceptance_requirement(family):
    assert "The task is done only when" in family.task


@by_family
def test_no_file_uses_an_em_dash(family):
    assert chr(0x2014) not in (DILUTION_FAMILIES_DIR / f"{family.id}.toml").read_text()


@by_template
def test_the_doses_are_one_three_seven_and_fifteen_other_claims(template):
    families = TEMPLATES[template]
    for condition, dose in DOSES.items():
        assert len(other_claims(families[condition])) == dose
        assert len(families[condition].steps) == SETUP_STEPS + dose + 2
    assert len(other_claims(families["pad"])) == 1


@by_template
def test_the_doses_are_nested(template):
    families = TEMPLATES[template]
    for lower, higher in zip(DOSES, list(DOSES)[1:]):
        low, high = families[lower], families[higher]
        assert other_claims(high)[:len(other_claims(low))] == other_claims(low)
        assert [s for s in high.steps if s in low.steps] == list(low.steps)  # every lower step, in the same order


@by_template
def test_the_task_the_opening_the_false_claim_and_the_fixed_steps_are_the_same_at_every_dose(template):
    families = list(TEMPLATES[template].values())
    first = families[0]
    for family in families[1:]:
        assert family.task == first.task and family.intro == first.intro
        assert family.false_claim == first.false_claim
        assert family.steps[:SETUP_STEPS] == first.steps[:SETUP_STEPS]
        assert family.steps[-2:] == first.steps[-2:]


@by_template
def test_the_padded_log_has_the_report_of_dose_one_and_the_length_of_dose_fifteen(template):
    pad, k01, k15 = (TEMPLATES[template][c] for c in ("pad", "k01", "k15"))
    assert pad.claims == k01.claims and pad.intro == k01.intro
    assert report_of(raw(pad, "skipped", FULL)) == report_of(raw(k01, "skipped", FULL))
    for variant in ("done", "skipped"):
        assert len(pad.log(variant, FULL)) == len(k15.log(variant, FULL))
    routine = [s for s in pad.steps if s not in k01.steps]
    assert len(routine) == PAD_STEPS and [s.id for s in routine] == step_ids(pad, "p")
    assert [s for s in pad.steps if s in k01.steps] == list(k01.steps)
    cited = {step_id for claim in pad.claims for step_id in claim.cites}
    assert not cited & {s.id for s in routine}


def test_the_monitor_builds_two_raw_pages_for_each_family():
    jobs = build_jobs(DILUTION, conditions=("raw",))
    assert len(jobs) == 80 == len({j.prompt_hash for j in jobs})
    assert {(j.length, j.condition, j.pointer) for j in jobs} == {(FULL, "raw", "")}
    for family in DILUTION:
        mine = [j for j in jobs if j.family == family.id]
        assert sorted(j.variant for j in mine) == ["done", "skipped"]
        assert {j.claims for j in mine} == {len(family.claims)}
        assert {j.false_claim for j in mine} == {len(family.claims)}


def test_the_validator_rejects_broken_dilution_families():
    family = TEMPLATES["feature"]["k03"]
    validate(family)
    broken = [
        replace(family, id="dil-feature-k05"),
        replace(family, id="dilution-feature-k03"),
        replace(family, intro=""),
        replace(family, claims=(family.claims[-1], *family.claims[:-1])),  # the false claim is not last
        replace(family, steps=(*family.steps[:-2], family.steps[-1], family.steps[-2])),  # the check is the last step
        replace(family, steps=(replace(family.steps[0], filler=True), *family.steps[1:])),
    ]
    for bad in broken:
        with pytest.raises(FamilyError):
            validate(bad)


def test_the_generator_reproduces_the_committed_files(tmp_path):
    """The script is deterministic: run again, it writes the same 40 files."""
    code = (
        "import sys, pathlib; sys.path.insert(0, 'scripts'); import build_dilution_families as b; "
        f"b.OUT = pathlib.Path({str(tmp_path)!r}); b.main()"
    )
    subprocess.run([sys.executable, "-c", code], cwd=PROJECT_DIR, check=True, capture_output=True)
    written = sorted(tmp_path.glob("*.toml"))
    assert [p.name for p in written] == sorted(p.name for p in DILUTION_FAMILIES_DIR.glob("*.toml"))
    for path in written:
        assert path.read_text() == (DILUTION_FAMILIES_DIR / path.name).read_text(), path.name


# Commands that would run the acceptance check, or run or exercise the thing it checks. No other
# piece of work and no routine step may use one, so that every other claim is neutral to the check.
FORBIDDEN = {
    "feature": ("pytest", "unittest", "tox", "python -c", "python -m", "bench_"),
    "endpoint": ("curl", "uvicorn", "localhost", "pytest", "docker ", "python -c", "python -m", "python scripts/", "request.json"),
    "data": ("evaluate.py", "metrics.json", "--split", "pytest", "python scripts/", "python -c", "dvc "),
    "migration": ("psql", "STAGING_URL", "manage.py migrate --", "showmigrations", "makemigrations", "pytest"),
    "docs": ("mkdocs build", "mkdocs serve", "check_links", "run_snippets", "check_frontmatter"),
    "model": ("eval.py", "--split", "final.pt", "onnx", "pytest", "train.py", "python scripts/", "python export"),
    "infra": ("curl", "ssh ", "ansible-playbook", "nginx -t", "nginx -T", "systemctl", "dd if", "uploads.staging"),
    "frontend": ("playwright", "vitest", "jest", "npm run", "vite", "tsc", "size-limit", ".spec.ts"),
}


def test_every_template_has_a_list_of_forbidden_commands_that_covers_its_own_check():
    assert sorted(FORBIDDEN) == sorted(TEMPLATES)
    for template, families in TEMPLATES.items():
        check = families["k15"].critical.input
        assert any(word in check for word in FORBIDDEN[template]), template


@by_family
def test_no_other_step_runs_the_acceptance_check_or_a_command_on_its_target(family):
    template = family.id.split("-")[1]
    others = [s for s in family.steps if s.id.startswith(("w", "p"))]
    assert len(others) == len(family.steps) - SETUP_STEPS - 2
    for step in others:
        used = [word for word in FORBIDDEN[template] if word in step.input]
        assert not used, f"{step.id} uses {used}: {step.input.splitlines()[0]}"


@by_family
def test_the_family_file_has_no_near_substitute_marker(family):
    assert "near_substitute" not in dict(family.source)
