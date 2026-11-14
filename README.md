# log-citations

Do LLM reviewers check an agent's citations to its own log?

An agent finishes a task and writes a report in which each claim cites a step in the agent's own tool log.
On a log where the agent skipped one step, the false claim cites a real step that does not support it.
This project measures whether an LLM reviewer still tells finished work from unfinished work, compared with reading the same report and log with no citations.
It is an entry for Track 2, Trust Infrastructure, of the Apart Research AI x Epistemics sprint, November 13 to 15, 2026.

Status: finished.
The pilot passed its four criteria, and the main run finished on three reviewers: deepseek-v4-flash, gemma-4-31b-it and qwen3.5-397b.
glm-5.2 could not be run, because the gateway stopped answering it.
The report is `report/REPORT.md`, built to `report/REPORT.pdf`.
`results/main-report-*.txt` and `results/reasons-report.txt` hold every number in it.

## What is here

- `data/families/*.toml`: three pilot task families, each a fixed tool log with one critical step and filler steps.
- `families.py`: loads a family and checks that its two logs differ in the critical step and nothing else.
- `render.py`: builds the page a reviewer reads, with a plain report (`raw`) or a report with citations (`cited`).
- `monitor.py`: asks reviewer models for a 0 to 100 score that the work is complete as reported.
- `PILOT.md`: the pilot plan and its pass criteria, written before any reviewer call.
- `pilot_report.py`: scores the pilot results against those criteria.
- `MAIN.md`: the main study plan, written before any reviewer saw a real-log family, with the changes made during the run.
- `main_report.py`: prints the pre-registered and secondary results from the raw readings.
- `reasons_report.py`: prints the exploratory results on what reviewers flag and how they score it.
- `scripts/make_figure.py` and `scripts/build_pdf.py`: draw the figure and build the report.
- `data/families_malt/*.toml`: eleven families built from real agent runs in METR's MALT dataset.
- `data/malt_pool.json`: the fixed pool of 100 MALT runs the real families were drawn from, with the decision on each run.
- `scripts/malt_selection.py`: which runs became families, how each was cut, and why the others were turned down.
- `scripts/build_malt_families.py` and `scripts/malt.py`: the code that draws the pool and writes the family files.

## Run

```
uv sync
uv run pytest
uv run python monitor.py --models deepseek-v4-flash --readings 20
```

The last command is a dry run for the three hand-built families.
Add `--set malt` for the families built from real runs, or `--set all` for both.
It prints the number of calls in each condition and the cost, and it sends nothing.
Adding `--run` calls the API and spends credits, and it needs `ADAPTION_API_KEY` in the environment or in `.env`.

## Families built from real agent runs

The hand-built families are the pilot set.
The second set, `malt`, uses logs of real agent runs, so that the result does not rest on logs written for this study.

### Where the logs come from

The runs come from MALT, a dataset of agent transcripts published by METR as `metr-evals/malt-public` on Hugging Face under the MIT License.
The dataset is gated, so its Parquet files are not in this repository.
Four files of its `default` folder were used: `public-00012`, `public-00013`, `public-00016` and `public-00039`.
They hold 599 runs, all labelled `normal` by METR.

### How the pool was drawn

A run is eligible if its label is exactly `normal`, its task is not a `pico_ctf` or `password_check` puzzle, it has 5 to 40 recorded steps, and its history is at most 60,000 characters.
The eligible runs were sorted by run id, and 100 were drawn with `random.Random(20261113).sample`.
`data/malt_pool.json` lists the 100 runs in the order drawn.
Families come only from this pool.
Within a task, runs were read in pool order, and a run was passed over only for a reason recorded in the pool file.
46 of the 100 runs were read: 11 became families and 35 were turned down.
The other 54 were not read, mostly because their task already had two families or had been dropped.

### What makes a run usable

The finished log is the real run.
It must contain a check step: a step whose output is the only support for one statement in the agent's final report.
Removing that step must leave no trace, so no later step may quote it or depend on it.
The log must also contain an earlier real step that looks like the check and is not, and one that has nothing to do with it.
These two steps are where the fake citations point.

The most common reasons for turning a run down were these.

- The report lists several results that all come from one step, so removing it makes more than one claim false.
- Two steps support the same claim, so removing one leaves the claim true.
- A later step repeats or depends on the step that would be removed.
- The report is wrong even on the finished run, or the run has no final message at all.

No mystery-function run was usable, because those reports list every test, which leaves no uncited step for a fake citation to point to.

### What was edited

Each step is the real tool call and the real output, word for word.
The agent's free text before each call is its reasoning, not an action, and is left out.
Three kinds of scaffold text are removed from every step: the `[Note: the above tool output has been saved to ...]` line, the notices about how many tokens are left, and the `<bash-output>` style tags around an output.
The scaffold phrase that opens the task text, such as "Your current task is the following:", is removed.
An output over 20,000 characters would be cut with a visible marker in both twins alike, and no chosen run reaches that length.
The skipped twin is the same log with the check step removed, and nothing else is changed.

The report is the agent's own final text.
It is the text the agent submitted when that is a prose report, and otherwise the message the agent wrote just before submitting.
That text is split into claims, one per line, and each claim is given the steps that support it.
The build script checks that every such claim appears word for word in the agent's final text once line breaks are turned into spaces.
List numbers are dropped where each item became its own claim, and in two families a sentence that only announces the submission is dropped.
Three reports were a single sentence, so one short claim about an earlier step was added to each, to give the report a true claim with a real citation.
Those three claims are marked `written = true`.
Every family file lists its edits under `edits` and the things a reader should know under `flags`.

### Limits of this set

- In 10 of the 11 families the check step is the last step of the run, because agents check their work at the end.
- In the three bug-fix families the near-miss step is an earlier test run that shows failures, so the fake citation is easy to catch.
- In six families the false claim states a result that only the removed step shows, because the agent's own report states it.
- A real run has one length, so this set has no short and long versions.
- The choice of check step and of the two citation targets is a judgment made by one reader.

### Rebuilding

```
python -I scripts/build_malt_families.py pool
python -I scripts/build_malt_families.py build
```

Both commands need pyarrow, which this project does not depend on, and the four Parquet files under `data/malt/default/`.
Use any Python 3.11 or later that has pyarrow.
Nothing in a transcript is executed.

## Pre-existing work

Two files were written before the sprint.
They are copied from <https://github.com/apurv-1/swarm-alignment-maoc> at commit `52f1422`.

- `monitor.py`: the model client.
  Streaming, error classification, the pay-at-most-once ledger, the budget, resume, rate-limit handling and reply parsing are unchanged.
  The imports, the conditions, the instructions, the `Job` fields, `build_jobs` and the command-line options were changed for this study.
  The file's header lists each change.
- `tests/test_monitor.py`: the tests of that client.
  The client tests are unchanged, the fixtures now build this study's jobs, and the tests of `build_jobs` and of the instructions were rewritten.

The logs in `data/families_malt/` are data from METR's MALT dataset, used under its MIT License.
See `data/families_malt/NOTICE.md`.

Everything else in this repository is sprint work.
