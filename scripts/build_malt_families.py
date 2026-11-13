"""Build the real-log families from the downloaded MALT files.

    python -I scripts/build_malt_families.py pool    # write data/malt_pool.json
    python -I scripts/build_malt_families.py build   # write data/families_malt/*.toml

Both commands need pyarrow, which this project does not depend on. Use any Python 3.11 or later
that has it. They read data/malt/default/*.parquet, which is not in the repository: the files
come from the gated dataset metr-evals/malt-public on Hugging Face.

`pool` draws the fixed pool of runs that families may come from. `build` turns each run chosen
in scripts/malt_selection.py into a family file, and checks it:

- every step is the real tool call and the real output, and reads back from the file unchanged;
- every claim not marked `written` appears word for word in the agent's own final text;
- the file passes the same twin checks as the hand-built families.

Nothing in a transcript is ever executed.
"""

import json
import re
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parent.parent)]

import malt  # noqa: E402
from families import MALT_FAMILIES_DIR, load_family  # noqa: E402
from malt_selection import FAMILIES, REJECTED  # noqa: E402

POOL_FILE = malt.PROJECT_DIR / "data" / "malt_pool.json"
# The task text starts with one of these scaffold phrases. They are dropped, and the rest is kept.
TASK_PREFIXES = ("Your current task is the following:", "You are assigned this task:")
# An output longer than this is cut, with a marker, in both twins alike. No chosen run reaches it.
MAX_OUTPUT_CHARS = 20_000


def collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def task_text(text: str) -> str:
    text = text.strip()
    for prefix in TASK_PREFIXES:
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    raise ValueError(f"unexpected start of task text: {text[:60]!r}")


def cut(output: str) -> str:
    if len(output) <= MAX_OUTPUT_CHARS:
        return output
    dropped = len(output) - MAX_OUTPUT_CHARS
    return f"{output[:MAX_OUTPUT_CHARS]}\n[... {dropped} more characters of this output are not shown ...]"


def toml_string(text: str) -> str:
    """A TOML string that reads back as exactly `text`.

    Text is written verbatim between ''' marks when TOML allows it, so a person can read the file.
    Text with control characters, or with ''' in it, is written as one escaped line instead.
    """
    plain = all(ch in "\n\t" or (ord(ch) >= 32 and ord(ch) != 127) for ch in text)
    if text and plain and "'''" not in text and not text.endswith("'") and "\n" in text:
        return f"'''\n{text}\n'''"
    return json.dumps(text, ensure_ascii=False).replace("\x7f", "\\u007f")


def step_id(number: int) -> str:
    return f"s{number}"


def family_toml(spec: dict, row, pool_entry: dict) -> str:
    task, steps, submission, closing = malt.parse_steps(row)
    meta = row["metadata"]
    count = len(steps)
    for name in ("critical", "nearmiss", "unrelated"):
        if not 1 <= spec[name] <= count:
            raise ValueError(f"{spec['id']}: {name} step {spec[name]} is outside 1..{count}")

    final_text = collapse({"submit": submission, "closing": closing}[spec["report_from"]])
    agent_lines = [spec["intro"], *(c["text"] for c in spec["claims"] if not c.get("written"))]
    for line in agent_lines:
        if line and collapse(line) not in final_text:
            raise ValueError(f"{spec['id']}: not the agent's wording: {line!r}")
    written = [c["text"] for c in spec["claims"] if c.get("written")]
    false_claims = [c for c in spec["claims"] if c.get("false")]
    if len(false_claims) != 1 or false_claims[0].get("written"):
        raise ValueError(f"{spec['id']}: exactly one claim is false, and it must be the agent's wording")

    lines = [
        f"# Built by scripts/build_malt_families.py from run {meta['run_id']} of {malt.DATASET} (MIT License, METR).",
        "# The steps are the run's real tool calls and outputs. The skipped twin is this log without the critical step.",
        "# See [report] for every edit made to the agent's report and for what a reader should know.",
        "",
        f"id = {json.dumps(spec['id'])}",
        'set = "malt"',
        'report_source = "agent"',
        f"task = {toml_string(task_text(task))}",
        "",
        "[source]",
        f"dataset = {json.dumps(malt.DATASET)}",
        f"run_id = {meta['run_id']}",
        f"task_id = {json.dumps(meta['task_id'])}",
        f"model = {json.dumps(meta['model'])}",
        f"file = {json.dumps(pool_entry['file'])}",
        f"report_from = {json.dumps(spec['report_from'])}",
        f"written_claims = {len(written)}",
        "",
    ]
    for number, step in enumerate(steps, 1):
        lines += [
            "[[steps]]",
            f"id = {json.dumps(step_id(number))}",
            *(["critical = true"] if number == spec["critical"] else []),
            f"tool = {json.dumps(step['tool'])}",
            f"input = {toml_string(step['input'])}",
            f"output = {toml_string(cut(step['output']))}",
            "",
        ]
    lines += [
        "[report]",
        f"intro = {toml_string(spec['intro'])}",
        f"nearmiss = {json.dumps(step_id(spec['nearmiss']))}",
        f"unrelated = {json.dumps(step_id(spec['unrelated']))}",
        "edits = [",
        *(f"  {json.dumps(edit, ensure_ascii=False)}," for edit in spec["edits"]),
        "]",
        "flags = [",
        *(f"  {json.dumps(flag, ensure_ascii=False)}," for flag in spec["flags"]),
        "]",
        "",
    ]
    for claim in spec["claims"]:
        lines += [
            "[[report.claims]]",
            f"text = {toml_string(claim['text'])}",
            f"cites = {json.dumps([step_id(n) for n in claim['cites']])}",
            *(["false_when_skipped = true"] if claim.get("false") else []),
            *(["written = true"] if claim.get("written") else []),
            "",
        ]
    return "\n".join(lines)


def check_round_trip(path: Path, row) -> None:
    """The file must load as a valid twin pair, with every step exactly as the run has it."""
    family = load_family(path)
    _, steps, _, _ = malt.parse_steps(row)
    if len(family.steps) != len(steps):
        raise ValueError(f"{path.name}: {len(family.steps)} steps in the file, {len(steps)} in the run")
    for loaded, real in zip(family.steps, steps):
        if (loaded.tool, loaded.input, loaded.output) != (real["tool"], real["input"], cut(real["output"])):
            raise ValueError(f"{path.name}: step {loaded.id} does not read back as the run has it")


def pool_command() -> None:
    families = {spec["run_id"]: spec["id"] for spec in FAMILIES}
    rejected = dict(REJECTED)
    runs = []
    for entry in malt.draw_pool():
        run_id = entry["run_id"]
        if run_id in families:
            decision = {"decision": "family", "family": families[run_id]}
        elif run_id in rejected:
            decision = {"decision": "rejected", "reason": rejected[run_id]}
        else:
            decision = {"decision": "not examined"}
        runs.append({**entry, **decision})
    missing = (set(families) | set(rejected)) - {run["run_id"] for run in runs}
    if missing:
        raise ValueError(f"runs named in malt_selection.py are not in the pool: {sorted(missing)}")
    manifest = {
        "dataset": malt.DATASET,
        "license": "MIT, METR",
        "rule": {
            "label": ["normal"],
            "excluded_task_families": list(malt.EXCLUDED_TASK_FAMILIES),
            "steps": [malt.MIN_STEPS, malt.MAX_STEPS],
            "max_history_chars": malt.MAX_HISTORY_CHARS,
            "order": "eligible runs sorted by run_id, then random.Random(seed).sample(runs, size)",
            "seed": malt.SEED,
            "size": malt.POOL_SIZE,
            "files": sorted({run["file"] for run in runs}),
        },
        "runs": runs,
    }
    POOL_FILE.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    counts = {name: sum(run["decision"] == name for run in runs) for name in ("family", "rejected", "not examined")}
    print(f"wrote {POOL_FILE.relative_to(malt.PROJECT_DIR)}: {len(runs)} runs, {counts}")


def build_command() -> None:
    pool = {entry["run_id"]: entry for entry in malt.draw_pool()}
    wanted = {spec["run_id"]: spec for spec in FAMILIES}
    if set(wanted) - set(pool):
        raise ValueError(f"families outside the pool: {sorted(set(wanted) - set(pool))}")
    rows = {row["metadata"]["run_id"]: row for _, _, row in malt.read_rows() if row["metadata"]["run_id"] in wanted}
    MALT_FAMILIES_DIR.mkdir(parents=True, exist_ok=True)
    for old in MALT_FAMILIES_DIR.glob("*.toml"):
        old.unlink()
    for run_id, spec in wanted.items():
        path = MALT_FAMILIES_DIR / f"{spec['id']}.toml"
        path.write_text(family_toml(spec, rows[run_id], pool[run_id]) + "\n")
        check_round_trip(path, rows[run_id])
        family = load_family(path)
        longest = max(len(step.output) for step in family.steps)
        print(f"{path.name}: {len(family.steps)} steps, {len(family.claims)} claims, longest output {longest} characters")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "pool":
        pool_command()
    elif command == "build":
        build_command()
    else:
        sys.exit(__doc__)
