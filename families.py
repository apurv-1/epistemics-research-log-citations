"""Task families: a fixed tool log, its skipped twin, and the agent's final report.

A family is one small agent task, stored as data/families/<id>.toml.

- `steps` is the full log of the run in which the work was done, in order. Each step is one
  tool call and its output.
- Exactly one step is `critical`. The `skipped` twin is the same log without that step, so the
  twins differ in one step and nothing else.
- Steps marked `filler` are routine work that does not bear on any claim. The `short` log leaves
  them out and the `long` log keeps them, so length is the only thing that changes between the two.
- The report is a list of claims, and it says the work is complete. Its text is the same for both
  twins. Exactly one claim is `false_when_skipped`: the critical step is its only support.
- `nearmiss` and `unrelated` name the steps a fake citation for that claim points to. Both are
  in every log, and no claim cites either, so a fake citation changes one pointer and nothing else.

`validate` enforces all of this, so a family that loads is a valid twin pair.

There are five sets of families.

- `pilot`, in data/families: three hand-built families, each with a short and a long log.
- `malt`, in data/families_malt: families built from real agent runs in METR's MALT dataset by
  scripts/build_malt_families.py. A real run has one length, `full`, and no filler steps. Its
  report is the agent's own closing words where they exist (`report_source = "agent"`), and the
  file's `source` table names the run it came from.
- `dilution`, in data/families_dilution: constructed families written by
  scripts/build_dilution_families.py. Each is one task with a single acceptance check, which is
  the critical step and the last claim, plus k other pieces of verified work. They have one
  length, `full`, and are read with no citations.
- `related`, in data/families_related: constructed families written by
  scripts/build_related_families.py on the same eight tasks. Each has the acceptance check and
  exactly 7 other claims, which are neutral work, related evidence or lookalike checks, and in
  two conditions the task does not state its requirement.
- `malt_norel`, in data/families_malt_norel: three `malt` families with their related evidence
  removed by scripts/build_malt_norel_families.py. Related evidence is a passing run of the
  agent's own program on an input other than the reported one. Every claim that rested only on a
  removed step is dropped, and each file's [norel] table lists what was removed. They follow the
  rules of a real run.
"""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

FAMILIES_DIR = Path(__file__).parent / "data" / "families"
MALT_FAMILIES_DIR = Path(__file__).parent / "data" / "families_malt"
DILUTION_FAMILIES_DIR = Path(__file__).parent / "data" / "families_dilution"
RELATED_FAMILIES_DIR = Path(__file__).parent / "data" / "families_related"
MALT_NOREL_FAMILIES_DIR = Path(__file__).parent / "data" / "families_malt_norel"
SETS = {"pilot": FAMILIES_DIR, "malt": MALT_FAMILIES_DIR, "dilution": DILUTION_FAMILIES_DIR,
        "related": RELATED_FAMILIES_DIR, "malt_norel": MALT_NOREL_FAMILIES_DIR}
REAL_SETS = ("malt", "malt_norel")  # sets whose logs are real runs
DILUTION_ID = re.compile(r"dil-[a-z]+-(k01|k03|k07|k15|pad)")
RELATED_ID = re.compile(r"rel-[a-z]+-(r1|r3|r7|look|imp0|imp7)")
RELATED_CLAIMS = 8  # 7 other claims and the acceptance claim
# The constructed sets share one shape: one length, an opening sentence, the acceptance check as
# the last step before the closing step, and its claim last. Each has its own way of naming files.
CONSTRUCTED = {
    "dilution": (DILUTION_ID, "a dilution family is named dil-<template>-<k01|k03|k07|k15|pad>"),
    "related": (RELATED_ID, "a related family is named rel-<template>-<r1|r3|r7|look|imp0|imp7>"),
}
VARIANTS = ("done", "skipped")
LENGTHS = ("short", "long")  # the hand-built families
FULL = "full"  # a real run has one length
REPORT_SOURCES = ("agent", "written")


@dataclass(frozen=True)
class Step:
    id: str
    tool: str
    input: str
    output: str
    filler: bool = False
    critical: bool = False


@dataclass(frozen=True)
class Claim:
    text: str
    cites: tuple[str, ...]
    false_when_skipped: bool = False


@dataclass(frozen=True)
class Family:
    id: str
    task: str
    steps: tuple[Step, ...]
    intro: str
    claims: tuple[Claim, ...]
    nearmiss: str
    unrelated: str
    set: str = "pilot"
    report_source: str = "written"
    source: tuple[tuple[str, object], ...] = ()  # where a real run came from, as sorted items

    @property
    def lengths(self) -> tuple[str, ...]:
        return LENGTHS if self.set == "pilot" else (FULL,)

    @property
    def critical(self) -> Step:
        return next(s for s in self.steps if s.critical)

    @property
    def false_claim(self) -> Claim:
        return next(c for c in self.claims if c.false_when_skipped)

    @property
    def false_claim_number(self) -> int:
        """The false claim's place in the report, counting from 1."""
        return next(n for n, c in enumerate(self.claims, 1) if c.false_when_skipped)

    def log(self, variant: str, length: str) -> tuple[Step, ...]:
        """The steps a reviewer is shown, in order."""
        if variant not in VARIANTS or length not in self.lengths:
            raise ValueError(f"unknown variant or length for {self.id}: {variant!r}, {length!r}")
        return tuple(
            s for s in self.steps
            if not (length == "short" and s.filler) and not (variant == "skipped" and s.critical)
        )


class FamilyError(ValueError):
    """A family file that breaks a twin invariant."""


def validate(family: Family) -> None:
    def fail(message: str):
        raise FamilyError(f"{family.id}: {message}")

    if family.set not in SETS:
        fail(f"unknown set {family.set!r}")
    if family.report_source not in REPORT_SOURCES:
        fail(f"report_source must be one of {REPORT_SOURCES}")
    if not family.id or not family.task:
        fail("id and task are required")
    if family.set == "pilot" and not family.intro:
        fail("a hand-built report needs an intro")
    if family.set in REAL_SETS:
        if any(step.filler for step in family.steps):
            fail("a real run has no filler steps")
        if not dict(family.source).get("run_id"):
            fail("a real run must name its source run_id")
    if family.set in CONSTRUCTED:
        id_pattern, naming = CONSTRUCTED[family.set]
        if not id_pattern.fullmatch(family.id):
            fail(naming)
        if any(step.filler for step in family.steps):
            fail(f"a {family.set} family has one length, so no filler steps")
        if not family.intro:
            fail(f"a {family.set} report needs an opening sentence")
        if len(family.steps) < 2 or not family.steps[-2].critical:
            fail("the acceptance check must be the last step before the closing step")
        if not family.claims or not family.claims[-1].false_when_skipped:
            fail("the acceptance claim must be the last claim in the report")
    if family.set == "related" and len(family.claims) != RELATED_CLAIMS:
        fail(f"a related report has {RELATED_CLAIMS} claims: 7 other claims and the acceptance claim")
    ids = [s.id for s in family.steps]
    if len(set(ids)) != len(ids):
        fail("step ids must be unique")
    for step in family.steps:
        if not step.id or not step.tool or not step.input:
            fail(f"step {step.id!r} needs an id, a tool and an input")
    by_id = {s.id: s for s in family.steps}

    critical = [s for s in family.steps if s.critical]
    if len(critical) != 1:
        fail(f"exactly one step must be critical, found {len(critical)}")
    if critical[0].filler:
        fail("the critical step cannot be filler")
    critical_id = critical[0].id

    false_claims = [c for c in family.claims if c.false_when_skipped]
    if len(false_claims) != 1:
        fail(f"exactly one claim must be false_when_skipped, found {len(false_claims)}")
    if false_claims[0].cites != (critical_id,):
        fail("the false claim must cite the critical step and nothing else")

    cited = set()
    for claim in family.claims:
        if not claim.text or "\n" in claim.text:
            fail("each claim is one line of text")
        if not claim.cites:
            fail(f"claim {claim.text!r} cites no step")
        for step_id in claim.cites:
            if step_id not in by_id:
                fail(f"claim {claim.text!r} cites unknown step {step_id!r}")
            if by_id[step_id].filler:
                fail(f"claim {claim.text!r} cites filler step {step_id!r}, which the short log lacks")
            if step_id == critical_id and not claim.false_when_skipped:
                fail(f"claim {claim.text!r} also cites the critical step, so two claims would be false")
            cited.add(step_id)

    if family.nearmiss == family.unrelated:
        fail("nearmiss and unrelated must be different steps")
    for name, step_id in (("nearmiss", family.nearmiss), ("unrelated", family.unrelated)):
        if step_id not in by_id:
            fail(f"{name} names unknown step {step_id!r}")
        if by_id[step_id].filler or by_id[step_id].critical:
            fail(f"{name} step {step_id!r} must be in every log, so it cannot be filler or critical")
        if step_id in cited:
            fail(f"{name} step {step_id!r} is cited by a claim, so a fake citation would repeat a real one")


def _text(value: str) -> str:
    """TOML multi-line strings end with a newline before the closing quotes; drop it."""
    return value.strip("\n")


def load_family(path: Path) -> Family:
    data = tomllib.loads(path.read_text())
    report = data["report"]
    family = Family(
        id=data["id"],
        task=_text(data["task"]),
        steps=tuple(
            Step(s["id"], s["tool"], _text(s["input"]), _text(s.get("output", "")),
                 bool(s.get("filler", False)), bool(s.get("critical", False)))
            for s in data["steps"]
        ),
        intro=_text(report["intro"]),
        claims=tuple(
            Claim(_text(c["text"]), tuple(c["cites"]), bool(c.get("false_when_skipped", False)))
            for c in report["claims"]
        ),
        nearmiss=report["nearmiss"],
        unrelated=report["unrelated"],
        set=data.get("set", "pilot"),
        report_source=data.get("report_source", "written"),
        source=tuple(sorted(data.get("source", {}).items())),
    )
    if family.id != path.stem:
        raise FamilyError(f"{path.name}: id {family.id!r} does not match the file name")
    validate(family)
    return family


def load_all(directory: Path = FAMILIES_DIR) -> list[Family]:
    return [load_family(path) for path in sorted(directory.glob("*.toml"))]


def load_set(name: str) -> list[Family]:
    """The families of one set, or of every set for "all"."""
    names = list(SETS) if name == "all" else [name]
    return [family for set_name in names for family in load_all(SETS[set_name])]
