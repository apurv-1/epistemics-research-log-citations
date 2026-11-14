"""Tests for claude_reviewer.py. No test calls a model: the runner is replaced by a fake."""

import json
from types import SimpleNamespace

from claude_reviewer import best_rows, command, execute, key, load, plan, read_once, report
from families import load_set
from monitor import build_jobs

FAMILIES = [f for f in load_set("related") if f.id in ("rel-docs-r7", "rel-data-r7")]
JOBS = build_jobs(FAMILIES, conditions=("raw",))
REPLY = "<reasoning>x</reasoning><issue>The check is not in the log.</issue><score>70</score>"


def fake(result=REPLY, is_error=False, returncode=0):
    def run(cmd, input, **kwargs):
        run.calls.append((cmd, input, kwargs))
        body = {"result": result, "is_error": is_error, "total_cost_usd": 0.01, "modelUsage": {"claude-sonnet-5-5": {}}, "usage": {"output_tokens": 5}}
        return SimpleNamespace(stdout=json.dumps(body), stderr="", returncode=returncode)
    run.calls = []
    return run


def test_the_call_turns_every_tool_and_setting_off_and_sends_the_same_prompt():
    job = JOBS[0]
    cmd = command("sonnet", job)
    assert cmd[cmd.index("--tools") + 1] == "" and cmd[cmd.index("--setting-sources") + 1] == ""
    assert "--strict-mcp-config" in cmd and "--no-session-persistence" in cmd
    assert cmd[cmd.index("--system-prompt") + 1] == job.instructions
    run = fake()
    record = read_once("sonnet", job, 0, "/tmp", run)
    assert run.calls[0][1] == job.transcript
    assert (record["score"], record["family"], record["variant"], record["error"]) == (70.0, job.family, job.variant, None)
    assert record["response_models"] == ["claude-sonnet-5-5"] and record["key"] == key("sonnet", job, 0)


def test_an_error_is_recorded_with_no_score():
    record = read_once("sonnet", JOBS[0], 0, "/tmp", fake(result="Usage limit reached", is_error=True))
    assert record["score"] is None and "limit" in record["error"].lower()

    def broken(*args, **kwargs):
        raise TimeoutError("too slow")
    assert read_once("sonnet", JOBS[0], 0, "/tmp", broken)["error"].startswith("TimeoutError")


def test_plan_is_model_major_and_skips_what_is_done():
    todo = plan(JOBS, ["sonnet", "opus"], 2, set())
    assert len(todo) == len(JOBS) * 4
    assert [m for m, _, _ in todo] == ["sonnet"] * (len(JOBS) * 2) + ["opus"] * (len(JOBS) * 2)
    assert [r for _, _, r in todo[: len(JOBS) * 2]] == [0] * len(JOBS) + [1] * len(JOBS)
    assert len(plan(JOBS, ["sonnet"], 2, {key("sonnet", JOBS[0], 0)})) == len(JOBS) * 2 - 1


def test_execute_writes_one_record_per_call_and_stops_on_a_limit(tmp_path):
    out = tmp_path / "claude.jsonl"
    counts = execute(plan(JOBS, ["sonnet"], 2, set()), out, 2, fake())
    assert counts["scored"] == len(JOBS) * 2 and len(load(out)) == len(JOBS) * 2
    counts = execute(plan(JOBS, ["opus"], 3, set()), tmp_path / "limit.jsonl", 1, fake(result="usage limit reached", is_error=True))
    assert counts["stopped"] and len(load(tmp_path / "limit.jsonl")) == 1


def test_a_later_scored_record_replaces_an_error_for_the_same_key():
    rows = best_rows([{"key": "a", "score": None, "error": "x"}, {"key": "a", "score": 5.0}, {"key": "a", "score": None, "error": "y"}])
    assert rows == [{"key": "a", "score": 5.0}]


def test_report_describes_real_logs_by_family():
    rows = [{"key": f"{f}{v}{i}", "model": "sonnet", "arm": "score", "family": f, "variant": v, "score": s, "issue": issue}
            for f in ("malt-1", "malt-2") for v, s, issue in (("skipped", 80.0, "the check is missing"), ("done", 100.0, "none")) for i in range(3)]
    text = report("malt", rows, 2)
    assert "sonnet through the claude client: score instructions, malt set" in text
    assert "cut log: flagged and scored 50 or more, %" in text and " 100.0" in text
