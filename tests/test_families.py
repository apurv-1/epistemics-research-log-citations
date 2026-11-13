from dataclasses import replace
from pathlib import Path

import pytest

from families import LENGTHS, Claim, FamilyError, load_all, validate

FAMILIES = load_all()
PROJECT_DIR = Path(__file__).parent.parent


def by_family(name="family"):
    return pytest.mark.parametrize(name, FAMILIES, ids=[f.id for f in FAMILIES])


def test_the_three_pilot_families_load():
    assert [f.id for f in FAMILIES] == ["analysis", "bugfix", "review"]


@by_family()
def test_twins_differ_in_the_critical_step_and_nothing_else(family):
    for length in LENGTHS:
        done, skipped = family.log("done", length), family.log("skipped", length)
        assert len(done) == len(skipped) + 1
        assert tuple(s for s in done if s is not family.critical) == skipped
        assert family.critical in done and family.critical not in skipped


@by_family()
def test_filler_is_identical_across_twins_and_absent_from_the_short_log(family):
    filler = [s for s in family.steps if s.filler]
    assert filler
    for variant in ("done", "skipped"):
        assert [s for s in family.log(variant, "long") if s.filler] == filler
        assert not [s for s in family.log(variant, "short") if s.filler]
        # The short log is the long log with the filler taken out, in the same order.
        assert tuple(s for s in family.log(variant, "long") if not s.filler) == family.log(variant, "short")


@by_family()
def test_short_and_long_logs_carry_the_same_critical_steps(family):
    """Every step a claim or a fake citation can name is in both lengths."""
    named = {step_id for claim in family.claims for step_id in claim.cites} | {family.nearmiss, family.unrelated}
    for length in LENGTHS:
        ids = {s.id for s in family.log("done", length)}
        assert named <= ids
        assert named - {family.critical.id} <= {s.id for s in family.log("skipped", length)}


@by_family()
def test_log_lengths_are_about_eight_and_about_forty_steps(family):
    assert 7 <= len(family.log("done", "short")) <= 10
    assert 36 <= len(family.log("done", "long")) <= 44


@by_family()
def test_exactly_one_claim_is_false_on_the_skipped_log(family):
    skipped = {s.id for s in family.log("skipped", "long")}
    unsupported = [c for c in family.claims if not set(c.cites) <= skipped]
    assert unsupported == [family.false_claim]
    assert family.false_claim.cites == (family.critical.id,)


@by_family()
def test_fake_citation_targets_are_in_both_twins_and_cited_by_no_claim(family):
    cited = {step_id for claim in family.claims for step_id in claim.cites}
    for target in (family.nearmiss, family.unrelated):
        assert target not in cited
        for variant in ("done", "skipped"):
            for length in LENGTHS:
                assert target in {s.id for s in family.log(variant, length)}


def test_the_critical_step_sits_early_in_one_family_and_late_in_another():
    positions = []
    for family in FAMILIES:
        log = family.log("done", "long")
        positions.append(log.index(family.critical) / len(log))
    assert min(positions) < 0.4 and max(positions) > 0.6
    assert max(positions) - min(positions) > 0.3


def _first(family, **wanted):
    return next(s for s in family.steps if all(getattr(s, k) == v for k, v in wanted.items()))


def _with_step(family, step_id, **changes):
    return replace(family, steps=tuple(replace(s, **changes) if s.id == step_id else s for s in family.steps))


def _with_claim(family, index, **changes):
    claims = list(family.claims)
    claims[index] = replace(claims[index], **changes)
    return replace(family, claims=tuple(claims))


def _true_claim_index(family):
    return next(i for i, c in enumerate(family.claims) if not c.false_when_skipped)


BROKEN = {
    "two critical steps": lambda f: _with_step(f, _first(f, filler=False, critical=False).id, critical=True),
    "no critical step": lambda f: _with_step(f, f.critical.id, critical=False),
    "critical step is filler": lambda f: _with_step(f, f.critical.id, filler=True),
    "duplicate step id": lambda f: replace(f, steps=(*f.steps, f.steps[0])),
    "no false claim": lambda f: _with_claim(f, f.claims.index(f.false_claim), false_when_skipped=False),
    "two false claims": lambda f: _with_claim(f, _true_claim_index(f), false_when_skipped=True),
    "false claim has other support": lambda f: _with_claim(
        f, f.claims.index(f.false_claim), cites=(f.critical.id, f.claims[_true_claim_index(f)].cites[0])),
    "a true claim cites the critical step": lambda f: _with_claim(
        f, _true_claim_index(f), cites=(*f.claims[_true_claim_index(f)].cites, f.critical.id)),
    "claim cites nothing": lambda f: _with_claim(f, _true_claim_index(f), cites=()),
    "claim cites an unknown step": lambda f: _with_claim(f, _true_claim_index(f), cites=("no-such-step",)),
    "claim cites filler": lambda f: _with_claim(f, _true_claim_index(f), cites=(_first(f, filler=True).id,)),
    "claim spans two lines": lambda f: replace(f, claims=(*f.claims, Claim("one\ntwo", f.claims[_true_claim_index(f)].cites))),
    "nearmiss is the critical step": lambda f: replace(f, nearmiss=f.critical.id),
    "nearmiss is filler": lambda f: replace(f, nearmiss=_first(f, filler=True).id),
    "nearmiss is cited by a claim": lambda f: replace(f, nearmiss=f.claims[_true_claim_index(f)].cites[0]),
    "unrelated is unknown": lambda f: replace(f, unrelated="no-such-step"),
    "unrelated is filler": lambda f: replace(f, unrelated=_first(f, filler=True).id),
    "nearmiss equals unrelated": lambda f: replace(f, unrelated=f.nearmiss),
}


@pytest.mark.parametrize("name", BROKEN)
def test_the_validator_rejects_a_broken_family(name):
    for family in FAMILIES:
        with pytest.raises(FamilyError):
            validate(BROKEN[name](family))


def test_no_file_contains_an_em_dash():
    em_dash = chr(0x2014)
    paths = [*PROJECT_DIR.glob("*.py"), *PROJECT_DIR.glob("*.md"), *PROJECT_DIR.glob("data/families/*.toml"),
             *PROJECT_DIR.glob("data/families_malt/*"), *PROJECT_DIR.glob("data/*.json"),
             *PROJECT_DIR.glob("scripts/*.py"), *PROJECT_DIR.glob("tests/*.py")]
    assert paths
    assert [str(p) for p in paths if em_dash in p.read_text()] == []
