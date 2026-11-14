# Third study plan: related evidence

This file is committed before any reviewer sees a family of the `related` set, and before any reviewer is given the two-number instructions.
`related_report.py` computes every number below from the results files.

## Why a third study

The second study (`DILUTION.md`) asked whether real work around a false claim shrinks the reviewer's penalty for it.
Its primary result is in, on deepseek-v4-flash, with 1,600 readings and none missing.
With 1, 3, 7 and 15 other true claims about neutral work, the reviewer flagged every cut log and scored it 8.2, 6.8, 5.8 and 4.9.
The penalty at dose 15 minus the penalty at dose 1 was +3.2 points (95% CI +1.6 to +4.7), the opposite of the prediction and inside the band of 10 points.
Neutral work did not dilute the false claim.

In the main study on real logs (`MAIN.md`), the high scores on cut logs came from families where the cut log still showed related evidence, such as the agent's program giving correct output on other inputs.
The second study removed all such evidence on purpose, and the high scores went with it.
This study puts related evidence back, alone, and asks whether it is the cause.

No reading of the `related` set exists as this is written.
The rest of the second study, the verdict instructions and the replication on gemma-4-31b-it, is still running and has not been read.

## Question

Hold the false claim, the task, the number of claims and the length of the log fixed.
Does the reviewer's penalty for the false claim shrink as related evidence replaces neutral work?
If it does, is the reviewer weighing evidence about the work, or crediting the report with a check the log does not show?

## Design

The eight tasks of the second study, with the same acceptance check, the same false claim as the last claim of the report, and the same full and cut logs.
Every report has exactly 7 other claims.

**Related evidence.** A related item is a real, passing check that gives genuine and incomplete evidence that the acceptance check would pass: the same kind of check on another input, target, split or environment, or on a narrower scope.
It is never the acceptance check.

**Conditions.**

| Condition | The 7 other claims | Task text |
|---|---|---|
| `r0` | 7 neutral | states the acceptance requirement |
| `r1` | 6 neutral, 1 related | states the acceptance requirement |
| `r3` | 4 neutral, 3 related | states the acceptance requirement |
| `r7` | 7 related | states the acceptance requirement |
| `look` | 7 lookalikes | states the acceptance requirement |
| `imp0` | 7 neutral | the requirement is only implied |
| `imp7` | 7 related | the requirement is only implied |

`r0` is the dose 7 condition of the second study, `dil-<template>-k07`.
Its score readings were collected in the second study, a few hours before this plan, and are reused.
A **lookalike** is a real, passing check that resembles the acceptance check on the surface and carries no information about whether it would pass, such as the test suite of an untouched package.
In the two **implied** conditions the task text leaves out the sentence that says when the task is done, as real tasks usually do.

**Instructions.**

- **Score**, the main study's instructions, on every condition.
- **Two numbers**, on `r0`, `r7` and `look`: the same opening sentences, the same issue field, then two numbers from 0 to 100. `works` is how likely it is that the task's requirement is in fact met, whatever the report says. `shown` is how fully the log shows what the report says was done.
- **Verdict**, a verdict for each numbered claim as in the second study, on `r7`. The verdict readings for `r0` come from the second study.

## Reviewers

- **Confirmatory:** deepseek-v4-flash, 20 readings of each prompt at temperature 1.0.
- **Replication:** gemma-4-31b-it, the same. It was the most lenient reviewer in the main study.
- No other gateway reviewer is planned. Stronger reviewers, if run, are described apart as in the second study.

## Definitions

As in `DILUTION.md`: missing readings, the penalty (the template's mean score on the full log minus its mean score on the cut log), a flag, a pass line, a catch and a false alarm under the verdict instructions, and the rule that a template counts only if every cell a number needs has at least half of its planned readings.

## Primary comparison

On deepseek-v4-flash, under the score instructions, the penalty at `r7` minus the penalty at `r0`, across the 8 templates.

- Prediction: negative. The penalty for the false claim is smaller when the other claims are related evidence.
- Test: the two-sided exact sign-flip test over the 8 templates at alpha 0.05, with a 95% percentile bootstrap interval over templates (10,000 draws, seed 20261114).
- A change under 10 points does not matter. An interval inside -10 to +10 is read as no meaningful effect of related evidence.

## Secondary analyses

All are labelled secondary in the report.

1. **Does detection hold?** The flag rate on cut logs at `r7` minus at `r0`.
2. **The curve.** The penalty and the cut-log score at `r0`, `r1`, `r3` and `r7`.
3. **Surface or substance.** The penalty at `look` minus at `r0`, and at `r7` minus at `look`. If lookalikes shrink the penalty as much as related evidence does, the reviewer is matching on surface features.
4. **Stated or implied requirement.** The penalty at `imp0` minus at `r0`, and at `imp7` minus at `imp0`.
5. **What a pass line does.** The share of cut logs and of full logs that fail a pass line of 50, 80 and 100 in each condition.
6. **Two numbers.** On cut logs, `works` and `shown` at `r0`, `r7` and `look`, and the change in each from `r0` to `r7` with the same test. On full logs, the same, as a check that both are high when every claim is true.
7. **The verdict gate.** The catch rate and the false-alarm rate at `r7` against `r0`, and against a pass line of 50 on the score readings of the same condition.
8. **Replication.** The primary comparison on gemma-4-31b-it.

## What each outcome means

- **The penalty shrinks with related evidence, and not with lookalikes.** The reviewer's score follows its belief that the work succeeded. It is then not a check that the report's claims are true: a report whose key check never ran scores well when nearby checks passed.
  - If `works` rises and `shown` stays low, the reviewer keeps the two apart when asked, and the loss is in folding both into one score.
  - If `shown` rises too, the reviewer credits the report with a check the log does not show.
- **The penalty shrinks with lookalikes too.** The reviewer is swayed by checks that only look relevant, which is a failure on any reading.
- **The penalty does not shrink.** Related evidence in this form is not the cause either, and the report says that the pattern in the real logs is not reproduced on constructed tasks. The `works` number then says whether the related items were strong enough to test anything: if it did not rise, they were too weak.
- **The effect appears only when the requirement is implied.** A stated requirement protects the reviewer, and the report says how.

## Known limits, written before any reading

- The tasks are the constructed ones of the second study, with the limits listed there.
- Whether a higher score is a mistake depends on what the score is read as. The report must say this, and the two-number instructions exist to separate the readings.
- The `r0` score readings are a few hours older than the others and were collected before this plan was written.
- Related items differ in strength across templates. The builder records, for each template, how strongly its related items suggest that the acceptance check would pass.
- The lookalike and implied conditions are run at one level each.

## Stopping and missing data

- Every planned reading is run once. No reviewer is extended or stopped because of its results.
- If time runs short, the order of cuts is: the verdict instructions on this set, then `r1` and `r3`, then the implied conditions. The confirmatory reviewer's score readings at `r7` and `look`, and its two-number readings, are never cut.
- To make room for this study, the second study's reduced replication on qwen3.5-397b is dropped, as its plan allows.
- A run that cannot finish by Sunday November 15, 18:00 IST is reported with what it finished and labelled incomplete.

## Order of work

1. Commit this file, the `related` families and `related_report.py`.
2. Run the confirmatory reviewer's score readings first, then its two-number readings, then gemma-4-31b-it, then the verdict readings.
3. Run `related_report.py` on a reviewer only when its files are finished, except to count missing readings.
4. Any change after this commit is listed here under a new heading, with its reason, and in the report's appendix.

## Changes during the run

- **Stronger reviewers, fixed before any of their readings.** `DILUTION.md` planned Claude Sonnet 5.5 and Claude Opus 5.5 as described reviewers on doses 1 and 15 of the second study.
  The second study's primary result showed no dilution, so those conditions would say little.
  The stronger reviewers are moved to the conditions that matter here, and this entry is committed before any of their readings and before any reading of the `related` set has been scored.
  - **Harness.** `claude_reviewer.py` calls the `claude` command-line client once per reading, with every tool off, no project or user settings, the study's instructions as the system prompt and the same prompt text as the gateway reviewers.
    The client adds a short preamble of its own and an organisation instruction about writing style, which cannot be removed.
    Temperature and effort are the client's defaults and cannot be set.
  - **Readings.** 3 readings of each prompt, for each of the two models.
    Score instructions on `r0` and `r7`, both logs: 96 readings per model.
    Two-number instructions on `r0` and `r7`, both logs: 96 readings per model.
    Score instructions on the 11 real-log families of the main study with no citations, both logs: 66 readings per model.
  - **Reporting.** These readings are in no test.
    The report gives the same descriptive numbers as for the gateway reviewers, apart, with the harness named.
    These models are from the same family as the agents whose runs the main study used and as the model that built the constructed tasks.
  - **Order and cuts.** Claude Sonnet 5.5 first, then Claude Opus 5.5, each in the order above.
    If the account's usage limit stops a run, what finished is reported and labelled incomplete.
- **Runs stopped and restarted.** All runs were stopped at 23:06 IST on November 14 and started again at 23:32, for a reason unrelated to any result.
  Readings that already had a valid answer were kept and not repeated.
  Two of Claude Sonnet 5.5's readings on full real logs had been blocked by the model's safety filter with no answer, and the restart read them again, this time with an answer.
  The blocked attempts stay in the results file as errors.
