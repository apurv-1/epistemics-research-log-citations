# Why LLM Reviewers Need a Verdict on Every Claim

Code, data, plans and report for an entry to the Apart Research AI x Epistemics Research Sprint, November 13 to 15, 2026.
Track 2: Trust Infrastructure.

**[Read the report (PDF)](report/REPORT.pdf)** · [Report as Markdown](report/REPORT.md) · [Reproduce the numbers](#reproduce-the-numbers) · [Pre-registered plans](#pre-registered-plans)

## The question

When an AI agent finishes a task, it writes a report on its own work.
More and more often a second model, the reviewer, decides whether to believe that report.
This project tests whether a reviewer that finds a false claim in a report also acts on what it found.

Every test uses a pair of logs.
The **full log** is a real agent run, word for word.
The **cut log** is the same run with one check step removed.
The agent's report is the same text for both, so on the cut log exactly one claim states something the log no longer shows.

![The design on one real family](report/figures/schematic.png)

## What we found

1. **A forged citation did not fool the reviewers.**
   We made the false claim cite a real step that looks relevant and does not support it.
   On the confirmatory reviewer this changed the penalty for the false claim by +0.5 points, 95% CI -2.2 to +3.1 (pre-registered).
   A true line saying "all citations resolve" created no false trust either.
2. **The score was the weak point.**
   The open-weight reviewers named an unsupported claim in 77% to 96% of cut logs.
   They still scored 26% to 40% of cut logs at 50 or more, mostly where the cut log shows related checks that passed (exploratory).
3. **A verdict on each claim closed the gap.**
   The reviewer marks every claim SHOWN, NOT_SHOWN or CONTRADICTED, and the report is accepted only if every claim is SHOWN.
   This rule separated cut logs from full logs better than a pass line of 50 on all three open-weight reviewers.
   The gain was significant on the confirmatory reviewer (pre-registered secondary) and on the planned replication, and it pointed the same way on the third.

Discrimination is the share of cut logs a gate fails minus the share of full logs it fails, in percentage points, on the 11 real-log pairs.

| Reviewer | Pass line of 50 | Fail any flagged log | Verdict per claim | Verdict minus pass line |
|---|---|---|---|---|
| deepseek-v4-flash (confirmatory) | 44 | 67 | 89 | +45.5 (p = 0.020) |
| gemma-4-31b-it (planned replication) | 35 | 75 | 90 | +54.9 (p = 0.016) |
| qwen3.5-397b (added replication) | 52 | 78 | 91 | +38.6 (p = 0.055) |

The p-values are uncorrected sign-flip tests over families.
The report gives the bounds for unreadable replies, the check without two families whose reports overclaim in the full run, and the results that did not go our way.
Two of those are worth knowing up front.
The primary prediction of Study 2 failed.
Stating the task's requirement did not help on real logs.

The practical conclusion is a design rule.
A trust signal read by another AI system should carry a verdict for each claim, and the consumer should gate on those verdicts and not on one score.

## What is in this repository

| Path | What it holds |
|---|---|
| `report/` | The report as Markdown and PDF, and its two figures. |
| `PILOT.md`, `MAIN.md`, `DILUTION.md`, `RELATED.md` | The four plans, each committed before any reviewer saw its material, with every later change listed. |
| `data/` | The task families: 3 hand-built, 11 from real agent runs, and the constructed tasks of Studies 2 and 3. |
| `results/raw/` | Every reviewer reading, as JSON lines. |
| `results/*.txt` | Saved output of the report scripts. |
| `results/*.log` | Run logs of the reviewer calls. |
| `families.py`, `render.py` | Load a family, check its two logs, and build the page a reviewer reads. |
| `monitor.py` | The client that asks reviewer models for a score, two numbers or a verdict per claim. |
| `claude_reviewer.py` | The same prompts read by Claude models through the `claude` client. These readings are descriptive and enter no test. |
| `*_report.py` | One script per analysis. Each reads `results/raw/` and calls nothing. |
| `scripts/` | Builders for the family files, the figures and the PDF, and the shell scripts that ran each study. |
| `tests/` | 1,568 tests of the loaders, the renderer, the client and the analysis scripts. |

### Task families

A family is one task with a fixed tool log, its cut log and the agent's report.
The code calls the full log `done` and the cut log `skipped`.

| Set | Folder | Files | Used in |
|---|---|---|---|
| `pilot` | `data/families/` | 3 hand-built tasks | Pilot (Appendix D) |
| `malt` | `data/families_malt/` | 11 pairs from real agent runs | Study 1 and Sections 5 and 6 |
| `malt_norel` | `data/families_malt_norel/` | 3 real pairs with the related evidence removed | Section 5.2 |
| `malt_stated` | `data/families_malt_stated/` | 5 real pairs with the requirement stated | Section 5.4 |
| `dilution` | `data/families_dilution/` | 8 constructed tasks in 5 conditions | Study 2 |
| `related` | `data/families_related/` | 8 constructed tasks in 6 conditions | Study 3 |

## Reproduce the numbers

The analysis needs no API key and no network.
It needs Python 3.12 or later and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

```bash
uv run pytest
```

Each script below prints its numbers from the raw readings.

| Report section | Command | Saved output |
|---|---|---|
| Study 1, forged citations (Table 1) | `uv run python main_report.py --models deepseek-v4-flash gemma-4-31b-it qwen3.5-397b` | `results/main-report-*.txt` |
| Flagged, then passed (Section 5) | `uv run python reasons_report.py --models deepseek-v4-flash gemma-4-31b-it qwen3.5-397b` | `results/reasons-report.txt` |
| Gates compared (Table 2, Section 5.3) | `uv run python gates_report.py` | `results/gates-report.txt` |
| Gate chosen on held-out families | `uv run python calibrated_gate_report.py` | `results/calibrated-gate-report.txt` |
| Related evidence removed (Section 5.2) | `uv run python norel_report.py` | `results/norel-report.txt` |
| Requirement stated (Section 5.4) | `uv run python stated_report.py` | `results/stated-report.txt` |
| Study 2 and the verdict rule (Table 3) | `uv run python dilution_report.py --models deepseek-v4-flash gemma-4-31b-it` | `results/dilution-report-*.txt`, `results/verdict-malt-report-*.txt` |
| Study 3, related evidence (Table 4) | `uv run python related_report.py --models deepseek-v4-flash gemma-4-31b-it` | `results/related-report-*.txt` |
| Pilot criteria (Appendix D) | `uv run python pilot_report.py --model deepseek-v4-flash --out results/raw/pilot-joined.jsonl` | `results/pilot-report-deepseek.txt` |

### Taking new readings

```bash
uv run python monitor.py --models deepseek-v4-flash --readings 20 --set malt
```

This is a dry run.
It prints the number of calls in each condition and their cost, and it sends nothing.
`--set` takes any set name from the table above, or `all`.
`--instructions` takes `score`, `two` or `verdict`.
Adding `--run` calls the reviewer models through the Adaption gateway and spends credits.
It needs `ADAPTION_API_KEY` in the environment or in `.env`.

## Pre-registered plans

Each plan fixes its definitions, thresholds and tests, and was committed before any reviewer saw the material it covers.
Each file lists the changes made during its run.
No change altered a prompt, a definition, a threshold or a test after its results were read.

| Plan | Commit | Committed (IST) | Covers |
|---|---|---|---|
| `PILOT.md` | `4b9f50a` | 13 Nov, 21:25 | The pilot and its four pass criteria |
| `MAIN.md` | `23e2465` | 13 Nov, 23:07 | Study 1: forged citations on real logs |
| `DILUTION.md` | `fbd07f5` | 14 Nov, 20:35 | Study 2: dilution, and the verdict per claim |
| `RELATED.md` | `05f1439` | 14 Nov, 22:34 | Study 3: related evidence, and the Claude readings (`a46cd14`) |

The report labels every result as pre-registered, planned, exploratory or descriptive.
Appendix B of the report lists every planned arm that was not completed.

## How the real-log families were built

The hand-built families are the pilot set.
The `malt` set uses logs of real agent runs, so that the result does not rest on logs written for this study.

### Where the logs come from

The runs come from MALT, a dataset of agent transcripts published by METR as `metr-evals/malt-public` on Hugging Face under the MIT License.
The dataset is gated, so its Parquet files are not in this repository.
Four files of its `default` folder were used: `public-00012`, `public-00013`, `public-00016` and `public-00039`.
They hold 599 runs, all labelled `normal` by METR.

### How the pool was drawn

A run is eligible if its label is exactly `normal`, its task is not a `pico_ctf` or `password_check` puzzle, it has 5 to 40 recorded steps, and its history is at most 60,000 characters.
The eligible runs were sorted by run id, and 100 were drawn with `random.Random(20261113).sample`.
`data/malt_pool.json` lists the 100 runs in the order drawn, with the decision on each.
Families come only from this pool.
Within a task, runs were read in pool order, and a run was passed over only for a reason recorded in the pool file.
46 of the 100 runs were read: 11 became families and 35 were turned down.
The other 54 were not read, mostly because their task already had two families or had been dropped.
`scripts/malt_selection.py` records which runs became families and how each was cut.

### What makes a run usable

The full log is the real run.
It must contain a check step: a step whose output is the only support for one statement in the agent's final report.
Removing that step must leave no trace, so no later step may quote it or depend on it.
The log must also contain an earlier real step that looks like the check and is not, and one that has nothing to do with it.
These two steps are where the fake citations point.

The most common reasons for turning a run down were these.

- The report lists several results that all come from one step, so removing it makes more than one claim false.
- Two steps support the same claim, so removing one leaves the claim true.
- A later step repeats or depends on the step that would be removed.
- The report is wrong even on the full run, or the run has no final message at all.

No mystery-function run was usable, because those reports list every test, which leaves no uncited step for a fake citation to point to.

### What was edited

Each step is the real tool call and the real output, word for word.
The agent's free text before each call is its reasoning, not an action, and is left out.
Three kinds of scaffold text are removed from every step: the `[Note: the above tool output has been saved to ...]` line, the notices about how many tokens are left, and the `<bash-output>` style tags around an output.
The scaffold phrase that opens the task text, such as "Your current task is the following:", is removed.
An output over 20,000 characters would be cut with a visible marker in both logs alike, and no chosen run reaches that length.
The cut log is the same log with the check step removed, and nothing else is changed.

The report is the agent's own final text.
It is the text the agent submitted when that is a prose report, and otherwise the message the agent wrote just before submitting.
That text is split into claims, one per line, and each claim is given the steps that support it.
The build script checks that every such claim appears word for word in the agent's final text once line breaks are turned into spaces.
List numbers are dropped where each item became its own claim, and in two families a sentence that only announces the submission is dropped.
Three reports were a single sentence, so one short claim about an earlier step was added to each, to give the report a true claim with a real citation.
Those three claims are marked `written = true`.
Every family file lists its edits under `edits` and the things a reader should know under `flags`.

### Rebuilding the family files

```bash
python -I scripts/build_malt_families.py pool
```

```bash
python -I scripts/build_malt_families.py build
```

Both commands need pyarrow, which this project does not depend on, and the four Parquet files under `data/malt/default/`.
Use any Python 3.11 or later that has pyarrow.
Nothing in a transcript is executed.

## Limits

Appendix A of the report gives the full list.
These are the ones a reader should have in mind first.

- The results rest on one confirmatory reviewer, 11 real-log pairs or 8 constructed tasks, and one prompt wording at temperature 1.0.
- The false claim comes from removing a step, not from an agent that overclaimed on its own.
- In the two web-server families the claim the cut makes false is also false in the full run, because the agent's server has a bug the log never tests.
  The report gives the verdict test without them.
- The finding that reviewers flag a claim and still pass the work came from exploratory analysis.
- The verdict rule needs the report split into claims, and we split them by hand.
- In 10 of the 11 real-log families the check step is the last step of the run, because agents check their work at the end.
- An AI coding agent chose which step to remove and where the citations point, under written rules, with a recorded decision for each run.
- glm-5.2 was planned as a reviewer and could not be run, because the gateway stopped answering it.

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

## Data notice

The logs in `data/families_malt/`, `data/families_malt_norel/` and `data/families_malt_stated/` are edited copies of runs from METR's MALT dataset, used under its MIT License.
Each of those folders has a `NOTICE.md` and METR's `LICENSE` file, and each family file names the run it came from.

## Citing

```text
Gupta, A. (2026). Why LLM Reviewers Need a Verdict on Every Claim.
Apart Research AI x Epistemics Research Sprint, Track 2: Trust Infrastructure.
https://github.com/apurv-1/epistemics-research-log-citations
```
