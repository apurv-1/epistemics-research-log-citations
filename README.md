# log-citations

Do LLM reviewers check an agent's citations to its own log?

An agent finishes a task and writes a report in which each claim cites a step in the agent's own tool log.
On a log where the agent skipped one step, the false claim cites a real step that does not support it.
This project measures whether an LLM reviewer still tells finished work from unfinished work, compared with reading the same report and log with no citations.
It is an entry for Track 2, Trust Infrastructure, of the Apart Research AI x Epistemics sprint, November 13 to 15, 2026.

Status: pilot scaffold.
No model has been called yet, so there are no results.

## What is here

- `data/families/*.toml`: three pilot task families, each a fixed tool log with one critical step and filler steps.
- `families.py`: loads a family and checks that its two logs differ in the critical step and nothing else.
- `render.py`: builds the page a reviewer reads, with a plain report (`raw`) or a report with citations (`cited`).
- `monitor.py`: asks reviewer models for a 0 to 100 score that the work is complete as reported.
- `PILOT.md`: the pilot plan and its pass criteria, written before any reviewer call.
- `pilot_report.py`: scores the pilot results against those criteria.

## Run

```
uv sync
uv run pytest
uv run python monitor.py --models deepseek-v4-flash --readings 20
```

The last command is a dry run.
It prints the number of calls in each condition and the cost, and it sends nothing.
Adding `--run` calls the API and spends credits, and it needs `ADAPTION_API_KEY` in the environment or in `.env`.

## Pre-existing work

Two files were written before the sprint.
They are copied from <https://github.com/apurv-1/swarm-alignment-maoc> at commit `52f1422`.

- `monitor.py`: the model client.
  Streaming, error classification, the pay-at-most-once ledger, the budget, resume, rate-limit handling and reply parsing are unchanged.
  The imports, the conditions, the instructions, the `Job` fields, `build_jobs` and the command-line options were changed for this study.
  The file's header lists each change.
- `tests/test_monitor.py`: the tests of that client.
  The client tests are unchanged, the fixtures now build this study's jobs, and the tests of `build_jobs` and of the instructions were rewritten.

Everything else in this repository is sprint work.
