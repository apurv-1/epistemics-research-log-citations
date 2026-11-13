import re

import pytest

from families import LENGTHS, VARIANTS, load_all
from render import BADGE_LINE, CITATION_NOTE, POINTERS, REAL, cited, format_step, raw, step_numbers

FAMILIES = load_all()
POINTER = re.compile(r"\[step (\d+)\]")
STEP_HEADER = re.compile(r"^Step (\d+) \(", re.MULTILINE)
REPORT_HEADER = "AGENT'S FINAL REPORT\n"
LOG_HEADER = "WORK LOG ("

by_family = pytest.mark.parametrize("family", FAMILIES, ids=[f.id for f in FAMILIES])
by_length = pytest.mark.parametrize("length", LENGTHS)


def report_of(page):
    return page.split(REPORT_HEADER, 1)[1]


def before_report(page):
    return page.split(REPORT_HEADER, 1)[0]


def log_of(page):
    return LOG_HEADER + page.split(LOG_HEADER, 1)[1].split("\n\nABOUT THE CITATIONS", 1)[0].split("\n\n" + REPORT_HEADER, 1)[0]


def claim_lines(page):
    return [line for line in report_of(page).splitlines() if line.startswith("- ")]


def cited_pages(family, length, badge=False):
    """Every cited page for one family and length: (variant, pointer level, page)."""
    return [("done", REAL, cited(family, "done", length, REAL, badge)),
            *(("skipped", pointer, cited(family, "skipped", length, pointer, badge)) for pointer in POINTERS)]


@by_family
@by_length
def test_the_raw_report_is_byte_identical_across_twins_and_has_no_citations(family, length):
    done, skipped = raw(family, "done", length), raw(family, "skipped", length)
    assert report_of(done) == report_of(skipped)
    assert not POINTER.search(report_of(done))
    assert CITATION_NOTE not in done and BADGE_LINE not in done
    assert done != skipped  # the logs differ


@by_family
def test_the_report_text_is_the_same_for_short_and_long_logs(family):
    assert report_of(raw(family, "done", "short")) == report_of(raw(family, "done", "long"))


@by_family
@by_length
@pytest.mark.parametrize("badge", [False, True])
def test_every_pointer_in_every_condition_resolves_to_a_step_on_the_page(family, length, badge):
    for variant, pointer, page in cited_pages(family, length, badge):
        shown = [int(n) for n in STEP_HEADER.findall(page)]
        assert shown == list(range(1, len(family.log(variant, length)) + 1))
        assert f"WORK LOG ({len(shown)} steps)" in page
        pointers = [int(n) for n in POINTER.findall(report_of(page))]
        assert pointers and all(1 <= n <= len(shown) for n in pointers)
        assert not POINTER.search(before_report(page))  # nothing in the log looks like a citation


@by_family
@by_length
def test_on_the_done_log_each_claim_points_to_the_steps_that_support_it(family, length):
    numbers = step_numbers(family.log("done", length))
    lines = claim_lines(cited(family, "done", length))
    assert len(lines) == len(family.claims)
    for claim, line in zip(family.claims, lines):
        assert [int(n) for n in POINTER.findall(line)] == [numbers[step_id] for step_id in claim.cites]
        assert line.startswith(f"- {claim.text} [step ")


@by_family
@by_length
def test_on_the_skipped_log_only_the_false_claims_pointer_changes(family, length):
    steps = family.log("skipped", length)
    numbers = step_numbers(steps)
    false_index = family.claims.index(family.false_claim)
    expected = {"none": [], "unrelated": [numbers[family.unrelated]], "nearmiss": [numbers[family.nearmiss]]}
    pages = {pointer: cited(family, "skipped", length, pointer) for pointer in POINTERS}
    for pointer, page in pages.items():
        lines = claim_lines(page)
        for index, (claim, line) in enumerate(zip(family.claims, lines)):
            found = [int(n) for n in POINTER.findall(line)]
            if index == false_index:
                assert found == expected[pointer]
            else:
                assert found == [numbers[step_id] for step_id in claim.cites]
    # The three levels differ in that one line and nowhere else.
    base = pages["none"].splitlines()
    false_line = len(base) - len(family.claims) + false_index  # the claims are the last lines of the page
    assert base[false_line] == f"- {family.false_claim.text}"
    for pointer in ("unrelated", "nearmiss"):
        ours = pages[pointer].splitlines()
        assert [i for i, (a, b) in enumerate(zip(ours, base, strict=True)) if a != b] == [false_line]


@by_family
@by_length
def test_a_fake_pointer_names_a_step_that_is_also_in_the_done_log(family, length):
    done = family.log("done", length)
    skipped = family.log("skipped", length)
    for target in (family.nearmiss, family.unrelated):
        step = next(s for s in skipped if s.id == target)
        assert step in done and not step.critical
        for variant, steps in (("done", done), ("skipped", skipped)):
            assert format_step(step, step_numbers(steps)[target]) in log_of(raw(family, variant, length))


@by_family
@by_length
def test_the_skipped_log_is_the_done_log_without_the_critical_step(family, length):
    def unnumbered(variant):
        return [format_step(step, 0) for step in family.log(variant, length)]

    done, skipped = unnumbered("done"), unnumbered("skipped")
    assert [text for text in done if text != format_step(family.critical, 0)] == skipped
    assert format_step(family.critical, 0) not in skipped


@by_family
@by_length
def test_the_log_shown_does_not_depend_on_the_report_condition(family, length):
    for variant in VARIANTS:
        log = log_of(raw(family, variant, length))
        pointers = (REAL,) if variant == "done" else POINTERS
        for pointer in pointers:
            for badge in (False, True):
                assert log_of(cited(family, variant, length, pointer, badge)) == log


@by_family
def test_the_badge_adds_one_true_line_and_nothing_else(family):
    assert "All citations resolve to existing log steps" in BADGE_LINE
    for variant, pointer, page in cited_pages(family, "short", badge=False):
        with_badge = cited(family, variant, "short", pointer, badge=True)
        assert with_badge == page.replace(CITATION_NOTE, f"{CITATION_NOTE}\n{BADGE_LINE}")
        assert with_badge.count(BADGE_LINE) == 1


@by_family
def test_pointer_levels_are_checked_against_the_variant(family):
    with pytest.raises(ValueError):
        cited(family, "done", "short", "nearmiss")
    with pytest.raises(ValueError):
        cited(family, "skipped", "short", REAL)
    with pytest.raises(ValueError):
        raw(family, "missing", "short")


def test_a_step_with_no_output_says_so():
    family = FAMILIES[0]
    step = family.steps[0]
    empty = type(step)(step.id, step.tool, step.input, "")
    assert format_step(empty, 3).endswith("output:\n(no output)")
