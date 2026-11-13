"""Read runs from the downloaded MALT Parquet files.

This module needs pyarrow, which is not a dependency of this project. Run it with any Python
that has pyarrow, in isolated mode, for example:

    /path/to/env/bin/python -I scripts/build_malt_families.py pool

The Parquet files are data from outside this project. Nothing in a transcript is ever executed:
the text is parsed and written out, and that is all.
"""

import glob
import json
import os
import random
import re
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
MALT_DIR = PROJECT_DIR / "data" / "malt" / "default"
DATASET = "metr-evals/malt-public"

# The pool rule, fixed before any run was read for suitability.
SEED = 20261113
POOL_SIZE = 100
EXCLUDED_TASK_FAMILIES = ("pico_ctf", "password_check")  # the answer is a flag or a password, not checkable work
MIN_STEPS, MAX_STEPS = 5, 40
MAX_HISTORY_CHARS = 60_000

CALL = re.compile(r"<(bash|python|submit|timeout)>(.*)", re.DOTALL)
OUTPUT = re.compile(r"^<(bash|python|submit|timeout)-output>(.*)</\1-output>\s*$", re.DOTALL)
# Scaffold lines that say where an output was saved, or how many tokens are left. They are not
# part of what a tool printed, and they are removed from every step.
SAVED_NOTE = re.compile(r"\n*\[Note: the above tool output has been saved to [^\]]*\]")
TOKEN_NOTICE = re.compile(r"^So far in this attempt at the task, you have used [\d.]+%? tokens, out of the total limit of \d+( tokens)?\.\s*$")
TOOL_NAMES = {"run_bash": "bash", "run_python": "python", "set_timeout": "timeout"}


def read_rows():
    """Every run in the downloaded files, as (file name, row index, row)."""
    import pyarrow.parquet as pq

    for path in sorted(glob.glob(str(MALT_DIR / "*.parquet"))):
        for index, row in enumerate(pq.ParquetFile(path).read().to_pylist()):
            yield os.path.basename(path), index, row


def history(row) -> list[dict]:
    """The run's messages after the system prompt: the task, then calls and outputs, then the final reply."""
    final = row["samples"][-1]
    # The final reply can be a reasoning message followed by the reply itself; the reply is last.
    return final["input"][1:] + [final["output"][0][-1]]


def eligible(row) -> bool:
    meta = row["metadata"]
    if meta["labels"] != ["normal"] or meta["task_id"].split("/")[0] in EXCLUDED_TASK_FAMILIES:
        return False
    chars = sum(len(m.get("content") or "") for m in row["samples"][-1]["input"][1:])
    return MIN_STEPS <= len(row["samples"]) <= MAX_STEPS and chars <= MAX_HISTORY_CHARS


def draw_pool() -> list[dict]:
    """All eligible runs sorted by run id, then POOL_SIZE of them drawn with a fixed seed."""
    runs = {}
    for name, index, row in read_rows():
        if eligible(row):
            meta = row["metadata"]
            runs[meta["run_id"]] = {
                "run_id": meta["run_id"], "task_id": meta["task_id"], "model": meta["model"],
                "file": f"default/{name}", "steps": len(row["samples"]),
            }
    ordered = [runs[run_id] for run_id in sorted(runs)]
    return random.Random(SEED).sample(ordered, POOL_SIZE)


def clean_output(text: str) -> str:
    text = SAVED_NOTE.sub("", text)
    match = OUTPUT.match(text)
    if match:
        text = match.group(2)
    return text.strip("\n")


def _call(message) -> tuple[str, str] | None:
    """The tool and its input for an assistant message, or None if the message is only reasoning."""
    call = message.get("function_call")
    if call:
        arguments = json.loads(call["arguments"])
        if len(arguments) != 1:
            raise ValueError(f"expected one argument, got {sorted(arguments)}")
        return TOOL_NAMES.get(call["name"], call["name"]), str(next(iter(arguments.values())))
    match = CALL.search(message.get("content") or "")
    if not match:
        return None
    tool, text = match.group(1), match.group(2)
    return tool, re.sub(rf"</{tool}>\s*$", "", text)


def parse_steps(row) -> tuple[str, list[dict], str, str]:
    """The task text, the tool steps, the final submission and the agent's closing message of a run.

    A step is one tool call and the output that followed it. The agent's free text before a call,
    and any message with no call, is its reasoning and not an action, so it is left out.
    """
    messages = history(row)
    task = messages[0]["content"]
    steps: list[dict] = []
    submission = closing = ""
    for message in messages[1:]:
        content = message.get("content") or ""
        if message["role"] == "assistant":
            call = _call(message)
            if call is None:
                continue
            tool, text = call
            if tool == "submit":
                submission = text
                closing = content if message.get("function_call") else content[: CALL.search(content).start()]
                continue
            steps.append({"tool": tool, "input": text.strip("\n"), "output": ""})
        elif TOKEN_NOTICE.match(content) or not steps:
            continue
        else:
            cleaned = clean_output(content)
            steps[-1]["output"] = (steps[-1]["output"] + "\n" + cleaned).strip("\n") if steps[-1]["output"] else cleaned
    return task, steps, submission.strip(), closing.strip()
