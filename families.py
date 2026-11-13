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
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path

FAMILIES_DIR = Path(__file__).parent / "data" / "families"
VARIANTS = ("done", "skipped")
LENGTHS = ("short", "long")


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

    @property
    def critical(self) -> Step:
        return next(s for s in self.steps if s.critical)

    @property
    def false_claim(self) -> Claim:
        return next(c for c in self.claims if c.false_when_skipped)

    def log(self, variant: str, length: str) -> tuple[Step, ...]:
        """The steps a reviewer is shown, in order."""
        if variant not in VARIANTS or length not in LENGTHS:
            raise ValueError(f"unknown variant or length: {variant!r}, {length!r}")
        return tuple(
            s for s in self.steps
            if not (length == "short" and s.filler) and not (variant == "skipped" and s.critical)
        )


class FamilyError(ValueError):
    """A family file that breaks a twin invariant."""


def validate(family: Family) -> None:
    def fail(message: str):
        raise FamilyError(f"{family.id}: {message}")

    if not family.id or not family.task or not family.intro:
        fail("id, task and report intro are required")
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
    )
    if family.id != path.stem:
        raise FamilyError(f"{path.name}: id {family.id!r} does not match the file name")
    validate(family)
    return family


def load_all(directory: Path = FAMILIES_DIR) -> list[Family]:
    return [load_family(path) for path in sorted(directory.glob("*.toml"))]
