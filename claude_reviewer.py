"""Read prompts with a Claude model through the `claude` command-line client.

    uv run python claude_reviewer.py --set related --conditions r7 --models sonnet opus --readings 3 \
        --out results/raw/claude-related.jsonl --run
    uv run python claude_reviewer.py --report related results/raw/claude-related.jsonl

RELATED.md ("Changes during the run") fixes which prompts these reviewers read and how the
readings are reported. They are described readings and are in no test.

Each reading is one call of `claude -p` with every tool off, no MCP servers, no user or project
settings and no saved session, run from an empty directory. The study's instructions are the
system prompt and the prompt text is the one the gateway reviewers get, so `monitor.build_jobs`
and `monitor.parse_reply` are used unchanged. The client adds a preamble of its own, and its
temperature and effort cannot be set.

Without --run the script prints what it would call and calls nothing.
"""

import argparse
import json
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dilution_report import FLAG, SCORE, _line, cell, collect, contrast, penalty, real_key, summary, under
from families import load_set
from monitor import ARMS, PROJECT_DIR, Job, build_jobs, parse_reply
from related_report import SHOWN_NUMBER, WORKS, _header, _table, key_for

HARNESS = "claude-cli"
TIMEOUT_SECONDS = 600
PASS_LINES = (50, 80, 100)
FLAG_AND_HIGH = lambda r: 100.0 * (r["flag"] and r["score"] >= 50)  # noqa: E731
HIGH = lambda r: 100.0 * (r["score"] >= 50)  # noqa: E731


def key(model: str, job: Job, reading: int) -> str:
    return f"{model}|{HARNESS}|{job.arm}|{job.prompt_hash}|{reading}"


def command(model: str, job: Job) -> list[str]:
    return ["claude", "-p", "--model", model, "--system-prompt", job.instructions, "--tools", "",
            "--strict-mcp-config", "--setting-sources", "", "--no-session-persistence", "--output-format", "json"]


def read_once(model: str, job: Job, reading: int, workdir: str, run=subprocess.run) -> dict:
    """One call and its record. A failure is recorded, not raised, so one bad call does not stop a run."""
    record = {"key": key(model, job, reading), "model": model, "harness": HARNESS, "reading": reading,
              "prompt_hash": job.prompt_hash, "family": job.family, "variant": job.variant, "arm": job.arm,
              "false_claim": job.false_claim, "score": None, "issue": "", "output": "", "error": None}
    start = time.time()
    try:
        done = run(command(model, job), input=job.transcript, capture_output=True, text=True,
                   timeout=TIMEOUT_SECONDS, cwd=workdir)
        reply = json.loads(done.stdout)
        if reply.get("is_error") or done.returncode != 0:
            record["error"] = str(reply.get("result") or done.stderr)[:500]
        else:
            record["output"] = reply.get("result") or ""
            record["response_models"] = sorted(reply.get("modelUsage") or {})
            record["cost_usd"] = reply.get("total_cost_usd")
            record["usage"] = {k: (reply.get("usage") or {}).get(k) for k in
                               ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")}
            record.update(parse_reply(job, record["output"]))
    except Exception as error:
        record["error"] = f"{type(error).__name__}: {error}"[:500]
    record["seconds"] = round(time.time() - start, 2)
    return record


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def best_rows(records: list[dict]) -> list[dict]:
    """The last scored record for each key, else the last record."""
    best: dict[str, dict] = {}
    for record in records:
        if record["key"] not in best or record.get("score") is not None or best[record["key"]].get("score") is None:
            best[record["key"]] = record
    return list(best.values())


def plan(jobs: list[Job], models: list[str], readings: int, done: set[str]) -> list[tuple[str, Job, int]]:
    """Model-major, then reading-major, so a run that stops early still covers every prompt."""
    todo, seen = [], set(done)
    for model in models:
        for reading in range(readings):
            for job in jobs:
                k = key(model, job, reading)
                if k not in seen:
                    seen.add(k)
                    todo.append((model, job, reading))
    return todo


def looks_like_a_limit(record: dict) -> bool:
    text = (record.get("error") or "").lower()
    return "limit" in text or "not logged in" in text


def execute(todo: list[tuple[str, Job, int]], out: Path, workers: int, run=subprocess.run) -> dict:
    counts = {"scored": 0, "unscored": 0, "errors": 0, "cost_usd": 0.0, "stopped": False}
    lock, stop = threading.Lock(), threading.Event()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as workdir, out.open("a") as sink:
        def one(item):
            if stop.is_set():
                return
            record = read_once(*item, workdir, run)
            with lock:
                sink.write(json.dumps(record) + "\n")
                sink.flush()
                counts["cost_usd"] += record.get("cost_usd") or 0.0
                if record["error"]:
                    counts["errors"] += 1
                    if looks_like_a_limit(record):
                        counts["stopped"] = True
                        stop.set()
                else:
                    counts["scored" if record["score"] is not None else "unscored"] += 1
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(one, todo))
    return counts


def report(set_name: str, rows: list[dict], min_readings: int) -> str:
    lines = []
    for model in sorted({row["model"] for row in rows}):
        for arm in ARMS:
            mine = [row for row in rows if row["model"] == model and row["arm"] == arm]
            if not mine:
                continue
            real = set_name == "malt"
            conditions = ("",) if real else ("r0", "r7")
            data = collect(mine, real_key if real else key_for(conditions))
            if not data["cells"]:
                continue
            cut = lambda m: (lambda unit, condition: cell(data, unit, condition, "skipped", m, min_readings))  # noqa: E731
            full = lambda m: (lambda unit, condition: cell(data, unit, condition, "done", m, min_readings))  # noqa: E731
            lines.append(f"== {model} through the claude client: {arm} instructions, {set_name} set ==")
            lines.append(f"Missing readings: {data['missing']} of {data['total']}; units: {len(data['units'])}")
            if not real:
                pen = lambda unit, condition: penalty(data, unit, condition, min_readings)  # noqa: E731
                lines.append(_line("penalty with 7 related items minus penalty with 7 neutral (described, in no test)",
                                   summary(contrast(data, "r7", "r0", pen))))
                if arm == "two":
                    lines.append(_line("cut log, works, 7 related minus 7 neutral", summary(contrast(data, "r7", "r0", cut(WORKS)))))
                    lines.append(_line("cut log, shown, 7 related minus 7 neutral", summary(contrast(data, "r7", "r0", cut(SHOWN_NUMBER)))))
            lines.append("Means over units:" + _header(conditions)[17:])
            measures = [("mean score", SCORE), ("flagged, %", FLAG), ("scored 50 or more, %", HIGH),
                        ("flagged and scored 50 or more, %", FLAG_AND_HIGH)]
            measures += [(f"fails a pass line of {line}, %", under(line)) for line in PASS_LINES]
            if arm == "two":
                measures += [("works", WORKS), ("shown", SHOWN_NUMBER)]
            for label, measure in measures:
                lines.append(_table(f"cut log: {label}", data, conditions, cut(measure)))
            for label, measure in measures:
                lines.append(_table(f"full log: {label}", data, conditions, full(measure)))
            lines.append("Cut-log mean score per unit:")
            for unit in data["units"]:
                values = [cell(data, unit, c, "skipped", SCORE, min_readings) for c in conditions]
                lines.append(f"  {unit:50s} " + "  ".join("   n/a" if v is None else f"{v:6.1f}" for v in values))
            lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--set", default="related", choices=("related", "dilution", "malt"))
    parser.add_argument("--families", nargs="*", help="Family ids to read. Default: every family of the set.")
    parser.add_argument("--instructions", default="score", choices=ARMS)
    parser.add_argument("--models", nargs="+", default=["sonnet"])
    parser.add_argument("--readings", type=int, default=3)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=PROJECT_DIR / "results" / "raw" / "claude.jsonl")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--report", nargs="+", metavar=("SET", "FILE"), help="Print the numbers for SET from FILEs and call nothing.")
    parser.add_argument("--min-readings", type=int, default=2)
    args = parser.parse_args()

    if args.report:
        rows = best_rows([r for path in args.report[1:] for r in load(Path(path))])
        print(report(args.report[0], rows, args.min_readings))
        return

    families = [f for f in load_set(args.set) if not args.families or f.id in set(args.families)]
    jobs = build_jobs(families, conditions=("raw",), arm=args.instructions)
    done = {r["key"] for r in load(args.out) if r.get("score") is not None}
    todo = plan(jobs, args.models, args.readings, done)
    print(f"{len(families)} families, {len(jobs)} prompts, {len(todo)} calls still to run ({args.instructions} instructions)")
    if not args.run:
        print("Dry run. Add --run to call the models.")
        return
    counts = execute(todo, args.out, args.workers)
    print(f"Finished: {counts['scored']} scored, {counts['unscored']} without a valid answer, {counts['errors']} errors, "
          f"about {counts['cost_usd']:.2f} USD at list price." + (" Stopped early on a limit." if counts["stopped"] else ""))


if __name__ == "__main__":
    main()
