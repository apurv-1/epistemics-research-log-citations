# LLM Reviewers Catch an Agent's False Claim and Pass the Work Anyway

Apurv Gupta, with Apart Research.

Apart Research AI x Epistemics Research Sprint, Track 2: Trust Infrastructure, November 2026.

Code, task families, every raw reviewer reading and the pre-registration: <https://github.com/apurv-1/epistemics-research-log-citations>

> First draft, written while two of four reviewers were still running.
> Every `[TODO: ...]` marks a number or a check that is not in yet.

## Abstract

When an AI agent reports its own work, a reviewer model often decides whether to believe it.
A proposed fix for overclaiming is to make each claim in the report cite the step in the agent's log that supports it.
We test whether that fix can be cheated with a citation that points to a real step that does not support the claim.
We built 11 task families from real agent runs in METR's MALT dataset.
Each has the real log, a twin with one check step removed, and the agent's own report, which is then false in one claim.
Under a pre-registered plan, reviewer models scored the report with no citations, and with a citation on the false claim at three levels of plausibility.
On the confirmatory reviewer, deepseek-v4-flash, a near-miss citation changed the gap between finished and unfinished work by +0.5 points (95% CI -2.2 to +3.1, p = 0.73).
On gemma-4-31b-it and qwen3.5-397b it widened the gap, by +6.0 and +8.0 points.
The forged citation misled no reviewer, and a true "all citations resolve" line changed nothing.
[TODO: glm-5.2.]
In exploratory analysis, reviewers named the false claim in 78% to 100% of unfinished logs and still gave 30% to 62% of them a passing score.
deepseek-v4-flash named it in every unfinished log with a near-miss citation and passed 31%, at a mean score of 80.
A reviewer's score can hide what the reviewer found, so a trust signal should carry claim-level findings.
We release the families, the readings and the scripts.

## 1. Introduction

When an AI agent finishes a task, it writes a report, and something downstream decides whether to believe it.
More and more often that reader is another model: a reviewer, a judge or a monitor.
The agent's report is testimony about its own work, and testimony can claim more than the work supports.
Smyth et al. (2026) found that coding agents that left a review incomplete gave a misleading account of it in 80.4% of those runs.
Khalifa et al. (2026) showed that rewriting an agent's reasoning, with its actions held fixed, makes LLM judges pass runs that failed.

The natural fix is to bind testimony to evidence.
Each claim in the report cites the step in the agent's log that supports it, so a reader can check the claim against the record.
Khalifa et al. name checking claims against observations as future work, and Hu (2026) argues for carrying provenance as structured state next to each claim.
This is a trust signal in the sense of this sprint's Track 2: machine-readable, cheap to attach, and meant for an AI system to consume.

A citation can be checked in two ways.
It **resolves** if the step it names exists.
It **supports** the claim if that step shows what the claim says.
Code can check the first.
Only a reader who opens the step can check the second.
A report can therefore be fully cited, pass every automatic check, and still be false.

Cotton-Barratt and Finnveden (2026) argue that trust and adoption reinforce each other, so an early epistemic tool can gain trust it has not earned, and they propose open, auditable infrastructure as the defence.
They also flag AI systems judging AI output as an open problem, because errors in the judge can compound.
Auditability only protects a reader who audits.
We ask whether an AI reader uses the auditability of a cited report, or only its appearance.

We run a provenance study for agent testimony.
Each task family is a fixed tool log in two versions: one where the agent did the work, and one where a single check step is missing.
The report is the same text for both, so one claim is false on the second log.
A reviewer model reads the report and the log and scores whether the work is complete as reported.
We then add citations and change only the citation on the false claim: none, an unrelated real step, or a near-miss step that looks relevant and does not establish the claim.
Every citation resolves.
The log and the report text never change, so any change in the reviewer's verdict is caused by the citations.

We expected one of two results: the forged citation misleads the reviewer, or the reviewer catches it and rejects the work.
We found a third.
The reviewer catches it, says so, and accepts the work.

Our contributions are:

- **A test that isolates the citation.** Matched logs that differ in one step, a byte-identical report, and three levels of unsupporting citation, on 11 task families built from real agent runs in METR's MALT dataset, plus 3 hand-built development families.
- **A pre-registered null with a tight interval, and two replications that point the other way from the attack.** On the confirmatory reviewer a near-miss citation changes separation by +0.5 points (95% CI -2.2 to +3.1), inside the band we fixed in advance for an effect that does not matter. On two replication reviewers it improves separation by +6.0 and +8.0 points. A true "all citations resolve" line has no effect on either reviewer that read it.
- **Where the reviewers fail instead.** In exploratory analysis, reviewers name the false claim in most unfinished logs and still give the work a passing score. Citations raise how often they name it and do not change the verdict.
- **A reusable check.** `monitor.py` runs the families against any reviewer model, and `main_report.py` and `reasons_report.py` print every number in this report.

## 2. Related work

**Judges swayed by the agent's own text.**
Khalifa et al. (2026) rewrote the reasoning of web agents while holding actions and observations fixed, across 800 trajectories and nine vision-language judges.
Manipulated reasoning inflated false positive rates by up to 90%, and prompting and extra judge compute reduced the effect without removing it.
They rewrote reasoning between steps, not a final report, and no condition tied a claim to a specific observation.
They note that their findings may not carry over to agents that run code or edit files, and they name mechanisms that check reasoning claims against observations as future work.
Our study takes up that mechanism, in the setting they left out.

**Agents that overclaim.**
Smyth et al. (2026) measured how often coding agents report work their transcripts do not show: 67.9% of runs left the assigned review incomplete, and 80.4% of those were misleading.
They detect overclaims with transcript coverage and an LLM grader that sees the ground truth.
They do not test whether a reader without the ground truth is misled, and their data is withheld.

**Status that gets lost.**
Hu (2026) showed that removing the note that an authorization was unverified sharply raises a monitor's approval of risky actions.
The monitor there reads a request and a handoff note, with no tool log and no citations.
Hu proposes storing provenance as structured state attached to the claim, and does not implement it or test it against provenance that is present and misleading.

**Checking the trace.**
GroundEval ([TODO: authors], 2026) replaces the judge with deterministic checks on the recorded trace of what an agent searched, fetched and cited.
A deterministic check can confirm that a cited step exists.
It cannot confirm that the step supports the claim, which is the gap we test.
A NeurIPS 2026 listing for TraceJudgeBench reports that LLM judges flag 34% to 78% of clean agent traces as containing errors and degrade further on long traces.
We have only the listing, so we treat those numbers as indicative.
They are why we score how well a reviewer separates finished from unfinished work, and not how often it accepts.

**Citations that resolve and do not support.**
"Cited but Not Verified" ([TODO: authors], 2026) evaluates citations in deep research reports on link validity, topical relevance and factual accuracy against the source.
It measures whether the agent's citations are accurate.
It does not measure whether a citation changes what a reader concludes.

None of these vary whether a report's claims cite steps in the agent's log while the log is held fixed, and none test citations that resolve and do not support.

## 3. Method

### 3.1 Families, twins and reports

A family is one task with a fixed tool log.
A step is one tool call and its output.
The **done** variant is the log of an agent that did the work.
The **skipped** variant is the same log with one **check step** removed: the step whose output establishes something the report states.
Nothing else differs, and the later steps are renumbered.
`families.py` checks this for every family.

The report states that the work is complete, as a short list of claims.
Its text is byte-identical for both variants.
On the skipped log exactly one claim, the **false claim**, states something the log no longer shows.

There are two sets of families.

**Real-log set, 11 families.**
These are the main study.
They are built from real agent runs in METR's MALT dataset (METR, 2025), which is MIT licensed.
From four of the dataset's files we took every run labelled `normal`, dropped two kinds of security puzzle, and kept runs of 5 to 40 steps and at most 60,000 characters.
That left 329 runs.
We drew 100 with a fixed seed and read them in the drawn order, task by task, under suitability rules fixed in advance.
Of the 46 runs read, 11 became families and 35 were turned down, each with a recorded reason (`data/malt_pool.json`).
The 11 families come from 9 tasks: three bug-fix families, two web-server families, three families that write a small program in an unfamiliar language, two research families and one word-game family.
The agents are Claude 3.5 Sonnet and Claude Opus 4.

The done log is the real run, with tool calls and outputs word for word.
The skipped log is that run with one check step removed.
The report is the agent's own final text, split into claims.
Three reports were a single sentence, so one short true claim was added to each and is marked as written by us.

Two properties of this set matter for reading the results, and both were written down before any main reading (`MAIN.md`).
In three bug-fix families the only earlier step that could serve as a near-miss is a test run that shows failures, so that forged citation is easy to catch.
In six families the agent's own report states a result that only the removed step shows, so the unfinished log is easier to catch in every condition.

**Development set, 3 families.**
These are hand-built: a bug fix where the test suite is not rerun after the last edit, a code review where one assigned file is never opened, and a data analysis where the headline metric is not recomputed after a data fix.
Each has a short log of 8 or 9 steps and a long log of 39 steps.
They were used for the pilot only (Appendix D) and are in no test below.

### 3.2 Conditions

The reviewer always sees the task, the full log and the report.

- **raw**: the report with no citations.
- **cited**: each claim ends with the step it cites, in square brackets. A short note before the report, outside the agent's words, says what the brackets are.

On the done log every citation is real and supports its claim.
On the skipped log the true claims keep their real citations, and the false claim's citation takes one of three levels.

- **none**: the false claim has no citation, while every other claim has one.
- **unrelated**: it cites a real step that has nothing to do with the claim.
- **near-miss**: it cites a real step that looks relevant and does not establish the claim. It ran before the last change, or on a different target, or with a different input.

The unrelated and near-miss steps exist in both variants and are cited by no other claim.
Every citation in every condition resolves to a step that exists.

In the **badge** arm, the note also carries one true line: "Automated check: All citations resolve to existing log steps."
The line is what a deterministic citation checker would print, and it is true for every cited report in the study, including the ones with an unsupporting citation.

### 3.3 Reviewers and analysis

The instructions tell the reviewer to decide whether the work is complete as the report says, and that it is not complete as reported when the report states something was done and the log does not show it.
They are identical in every condition and never mention citations, forgery or attacks.
The reviewer answers with its reasoning, the single most important unsupported claim or "none", and a score from 0 (clearly not complete as reported) to 100 (clearly complete as reported).
Reviewers are sampled at temperature 1.0, with 20 readings per prompt.

A family's **raw separation** is its mean raw done score minus its mean raw skipped score.
Its **cited separation** at a citation level is its mean cited done score minus its mean cited skipped score at that level.
The **citation effect** is cited separation minus raw separation, and a negative value means the citation made the reviewer worse at telling the variants apart.
The family is the unit of analysis.

`MAIN.md` was committed before any reviewer saw a real-log family.
It fixes deepseek-v4-flash as the confirmatory reviewer and gemma-4-31b-it, glm-5.2 and qwen3.5-397b as replications.
The primary comparison is the citation effect at the near-miss level on the confirmatory reviewer, tested two-sided with an exact sign-flip test over the 11 families at alpha 0.05, and reported with a bootstrap interval over families.
The plan also fixes a smallest effect of interest of 10 points: an interval inside -10 to +10 is read as evidence that the citation does not matter much.
The test is two-sided because the pilot gave no direction.
Replications use the same test with Holm correction.
The badge arm runs on deepseek-v4-flash and gemma-4-31b-it.

`main_report.py` prints every number in Sections 4.1 to 4.3, and `reasons_report.py` prints Section 4.4.

## 4. Results

deepseek-v4-flash finished 2,199 of 2,200 readings.
gemma-4-31b-it finished 2,165 of 2,200: the gateway closed its calls on the longest logs after about 60 seconds, and those readings are missing.
qwen3.5-397b finished all 1,320.
[TODO: glm-5.2 readings.]

### 4.1 A forged citation does not change what the reviewer concludes

On the confirmatory reviewer, a near-miss citation on the false claim changed separation by **+0.5 points** (95% CI -2.2 to +3.1; 6 families up, 4 down; sign-flip p = 0.73).
The interval lies well inside the -10 to +10 band fixed in advance.
The forged citation did not make deepseek-v4-flash worse at telling finished from unfinished work, and it did not make it better.

The other levels agree: -0.9 points with no citation on the false claim (CI -4.3 to +1.9) and +0.8 with an unrelated one (CI -2.5 to +4.0).
Real citations on finished work changed its score by +0.6 points (CI -2.0 to +3.2).
The result does not depend on the weaker families: it is +0.3 points without the three easy near-miss families and +0.6 without the six whose false claim states a removed result.

| Reviewer | Near-miss citation effect | 95% CI | Families up / down | p |
|---|---|---|---|---|
| deepseek-v4-flash (confirmatory) | +0.5 | -2.2 to +3.1 | 6 / 4 | 0.73 |
| gemma-4-31b-it | +6.0 | +1.5 to +11.5 | 7 / 2 | 0.031 |
| qwen3.5-397b | +8.0 | +4.6 to +11.5 | 9 / 2 | 0.0039 |
| glm-5.2 | [TODO] | | | |

On both finished replication reviewers the effect was positive.
On gemma-4-31b-it it was +6.0 points at the near-miss level, +6.4 with an unrelated citation and +2.7 with none.
On qwen3.5-397b it was +8.0, +8.6 and +4.3.
A near-miss citation made gemma-4-31b-it score the unfinished log 6.1 points lower (CI -11.5 to -1.7) and qwen3.5-397b 5.2 points lower (CI -9.4 to -1.2).
So where citations did anything, they helped, and a forged citation helped at least as much as a missing one.
Holm-adjusted across the two replications, p is 0.0078 for qwen3.5-397b and 0.031 for gemma-4-31b-it. [TODO: redo with glm-5.2.]

### 4.2 An "all citations resolve" line changes nothing

The badge line is true for every cited report, including the ones with a forged citation, so a reader who takes it as a sign of support would be misled.
Neither reviewer was.
With the line, near-miss separation changed by +0.2 points on deepseek-v4-flash (CI -5.0 to +4.6) and by +1.6 on gemma-4-31b-it (CI -0.3 to +3.8).

### 4.3 Without citations, the reviewers are unreliable in both directions

The reviewers' problem is not the citations.
With no citations at all, deepseek-v4-flash scored 70% of unfinished logs under 50, qwen3.5-397b 62% and gemma-4-31b-it 38%.
deepseek-v4-flash also scored 26% of finished logs under 50, against 10% for qwen3.5-397b and 5% for gemma-4-31b-it.
The reviewers range from strict to trusting, and citations moved these figures by a few points at most, except that gemma-4-31b-it's catch rate rose from 38% to 50% with a near-miss citation.

The pattern across families is sharp (Appendix E).
deepseek-v4-flash separated the variants by 84 to 99 points in five families: the three bug fixes, one research task and the word game.
In the three small-program families it scored the unfinished log 69 to 84 out of 100.
In three families it scored the finished log 9, 27 and 38.
Reading its stated reasons in those three, the reviewer was often right: it found real errors in the agent's web-server code, and it noted that one answer came from a source the task did not ask for.
A run that METR labels `normal` is not always correct work, which Section 6 returns to.
[TODO: this paragraph rests on reading a sample of reasons, not on a count.]

### 4.4 Exploratory: reviewers name the false claim and pass the work anyway

This analysis was designed after the first main results were read, and it is not a confirmatory test.

Each reply names the single most important unsupported claim, or "none".
We checked that sentence against a keyword pattern written by hand for each family's false claim.
On finished logs, where no claim is false, the patterns matched 7% to 9% of readings on every reviewer, which bounds how often they fire by accident.

| Reviewer | Unfinished log shown with | Names the false claim | Passes the work (score 50 or more) |
|---|---|---|---|
| deepseek-v4-flash | no citations | 95% | 30% |
| deepseek-v4-flash | near-miss citation | 100% | 31% |
| gemma-4-31b-it | no citations | 78% | 62% |
| gemma-4-31b-it | near-miss citation | 88% | 50% |
| qwen3.5-397b | no citations | 93% | 38% |
| qwen3.5-397b | near-miss citation | 98% | 39% |

deepseek-v4-flash named the false claim in almost every unfinished log and still passed three in ten.
Of its 69 passes at the near-miss level, 99% named the false claim, and their mean score was 80.
One such reply, scored 90: "The report claims input 4 was checked in step 5, but step 5 only shows factorial 5 outputting 120."
The reviewer opened the cited step, saw that it did not support the claim, wrote that down, and scored the work as nearly complete.

qwen3.5-397b behaved the same way: of its 86 passes at the near-miss level, 99% named the false claim, at a mean score of 76.

Citations did what they were meant to do for detection: with a citation on the false claim, all three reviewers named it more often.
The verdict did not follow.
The score treats a claimed check that never happened as a small flaw in otherwise finished work, even though the instructions say that such work is not complete as reported.

[TODO: audit a random sample of matched replies by hand, and report agreement with the keyword check.]

### 4.5 Development set

On the three hand-built families the pilot passed all four of its pre-set criteria on deepseek-v4-flash, with no missing readings.
On the long logs, raw separation was 73.5 to 84.0 points and finished work scored 100.
The near-miss citation effect was +5.5, -11.1 and +3.2 points, which gave no direction and is why the main test is two-sided.
deepseek-v4-flash was much better on these logs than on the real ones: it scored 83% of unfinished long logs under 50 and raised no false alarm on finished work.

### 4.6 Robustness

[TODO: missing readings per cell for each reviewer; whether any family was dropped for a reviewer under the ten-score rule; the qwen3.5-397b and glm-5.2 rows of every table above.]

## 5. Discussion

**Citing the log is safe against a cheap forgery, and it helps a little.**
A citation that resolves and does not support misled no reviewer, and a line vouching that all citations resolve did not either.
Khalifa et al. asked for mechanisms that check an agent's claims against its observations.
On these reviewers the simplest such mechanism survives its simplest attack.
On two of three reviewers it also widened the gap between finished and unfinished work, by 6 to 8 points, and a forged citation did so more than leaving the false claim uncited.
A citation tells the reviewer which step to open, and checking one named step is easier than searching a log for something that is missing.
But the gain is small next to the problem: with citations, the reviewers still passed 31% to 50% of unfinished logs.

**The verdict is the weak point.**
The reviewers found the false claim and then discounted it.
A system that consumes only the score, such as a pipeline that merges work scored above a threshold, throws away a finding the reviewer made and wrote down.
This is the failure Cotton-Barratt and Finnveden warn of, in a different place from where we looked for it: the audit happened, and its result did not reach the decision.

**A design rule for builders.**
A trust signal for an AI reader should carry what was checked and what was found, claim by claim.
"Resolves" and "supports" are different checks and should be different fields.
The reviewer's overall score should not be the only thing that travels downstream, and a claim the reviewer could not support should be able to block acceptance on its own.

**What would change our mind.**
[TODO: after glm-5.2 and qwen3.5-397b.]
A stronger reviewer may convert its findings into verdicts more reliably, and a prompt that asks for a claim-by-claim verdict before any score may close the gap.
Both are cheap to test with the released families.
The harder test is the forgery we did not run: a citation written by an agent that is trying to be believed, on long real runs.

## 6. Conclusion

[TODO: rewrite once all four reviewers are in.]
We asked whether an AI reviewer can be fooled by a citation that resolves and does not support.
On real agent logs, under a pre-registered test, it was not.
The reviewers caught the false claim, with or without the citation, and often accepted the work anyway, so the place to add trust infrastructure is between what a reviewer finds and what it decides.

## Code and provenance

Code, task families, every raw reviewer reading and the pre-registration (`PILOT.md`, `MAIN.md`) are at <https://github.com/apurv-1/epistemics-research-log-citations>.
Two files are pre-existing work, copied from <https://github.com/apurv-1/swarm-alignment-maoc> at commit `52f1422`: `monitor.py`, the model client, and `tests/test_monitor.py`, its tests.
The client's streaming, error handling, pay-at-most-once ledger, budget, resume and reply parsing are unchanged, and the file's header lists what was adapted.
Everything else was written during the sprint, November 13 to 15, 2026 AoE.
The real-log families are derived from METR's MALT dataset, `metr-evals/malt-public`, under its MIT license.
`main_report.py`, `reasons_report.py` and `pilot_report.py` produce every number in the abstract and results from the raw readings.

## LLM usage statement

AI coding agents (Claude Fable 5.2 in Claude Code) wrote most of the code, tests and family files to the author's design, and selected and converted the MALT runs under rules fixed in advance.
[TODO: confirm before submitting. The author reviewed the code and read every family by hand.]
Claude Fable 5.2 reviewed the design and drafts and helped draft the text.
The keyword patterns in Section 4.4 were written by Claude Fable 5.2. [TODO: the author's hand audit of a sample.]

## References

Cotton-Barratt, O., and Finnveden, L. (2026). AI for AI for epistemics. Forethought. <https://www.forethought.org/research/ai-for-ai-for-epistemics>

[TODO: authors] (2026). Cited but not verified: Parsing and evaluating source attribution in LLM deep research agents. <https://arxiv.org/abs/2605.06635>

[TODO: authors] (2026). GroundEval: A deterministic replacement for LLM-as-judge in stateful agent evaluation. <https://arxiv.org/abs/2606.22737>

Hu, Y. (2026). Silence is endorsement: Verification-status laundering in LLM agent pipelines. <https://arxiv.org/abs/2609.20211>

Khalifa, M., Logeswaran, L., Kim, J., Sohn, S., Zhang, Y., Lee, M., Peng, H., Wang, L., and Lee, H. (2026). Gaming the judge: Unfaithful chain-of-thought can undermine agent evaluation. <https://arxiv.org/abs/2601.14691>

METR (2025). MALT: A dataset of natural and prompted behaviors that threaten eval integrity. <https://metr.org/blog/2025-10-14-malt-dataset-of-natural-and-prompted-behaviors/> Dataset: <https://huggingface.co/datasets/metr-evals/malt-public> [TODO: check the post's exact title.]

Smyth, N., Mantilla-Ramos, Y.-J., Tikeng Notsawo, P. Jr, Helbling, S., Tosato, A., Merzouk, M. A., Dziri, N., Gidel, G., and Tosato, T. (2026). Quantifying overclaiming propensity in frontier LLM agents. <https://arxiv.org/abs/2609.20812>

TraceJudgeBench: A unified benchmark for validating LLM-as-a-judge on agent execution traces (2026). NeurIPS 2026 listing. <https://neurips.cc/virtual/2026/173089> [TODO: authors, once the listing names them.]

## Appendix A. Limitations and Dual-Use / Ethical Considerations

### What the result establishes

- On deepseek-v4-flash, across 11 families built from real agent runs, a near-miss citation on a false claim changes how well the reviewer separates finished from unfinished work by less than a few points in either direction.
- A true line saying that all citations resolve does not change that on the two reviewers that read it.
- On gemma-4-31b-it and qwen3.5-397b the same citation improves that separation, by +6.0 and +8.0 points. No reviewer was misled. [TODO: glm-5.2.]

### What it does not establish

- **That reviewers pass work they know is flawed, as a confirmed effect.** Section 4.4 is exploratory, uses a keyword check, and was designed after the main results were read.
- **How often agents cite an unsupporting step.** We place the citation ourselves. The study shows what a reviewer does when it meets one, not how often an agent would write one.
- **Anything about frontier reviewers.** Every reviewer is an open-weight model served by the sprint's gateway. A stronger reviewer may behave differently.
- **Anything about human readers.** No person reviewed these reports as a subject.
- **How a reviewer behaves when warned.** The instructions never say that a citation may be wrong.

### Limitations

- **Constructed twins.** No real pair of runs differs in exactly one step, so the skipped log is always made by us: a real run with one step removed.
- **Finished runs are not always correct runs.** The done log is a real run that METR labels `normal`. In at least two families the reviewer found real errors in the agent's work, so a low score on a finished log is not always a false alarm. Separation, which compares the twins, is less affected than the false-alarm rate.
- **Few families and few task types.** There are 11 families from 9 tasks of 4 types. One family can move a mean, so every result is also reported per family (Appendix E).
- **The check step is the last step in 10 of 11 families.** Agents check their work at the end, so an unfinished log usually ends without a check.
- **Three forged citations are easy.** In the bug-fix families the only earlier test run shows failures. The primary result is unchanged without them.
- **Six false claims state a removed result.** The agent's own report states a result that only the removed step shows. The primary result is unchanged without them.
- **The cuts are one reader's judgement.** The choice of check step and of the two citation targets was made by an AI coding agent under written rules. [TODO: the author's review of each family.]
- **Reports are the agents' own, lightly edited.** The split into claims is ours, three short claims were added, and every edit is listed in the family file.
- **Missing readings are not random.** gemma-4-31b-it lost readings on the longest logs.
- **Reviewers may have seen the logs.** MALT is public, so a reviewer model may have met these runs in training. The skipped variants and the cited reports are new.
- **One prompt wording.** One set of instructions, one citation format, and one score scale. The instructions tell the reviewer to compare the report with the log, which may help it more than a bare request would.
- **A passing score is our line.** We call a score of 50 or more a pass. A pipeline with a higher threshold would accept less.
- **Temperature 1.0.** Reviewers were sampled at temperature 1.0 to measure their distribution of judgements; a deployed reviewer at temperature 0 could behave differently.

### Dual-use and ethical considerations

This work describes a way to make a false claim in an agent's report look supported: cite a real step that looks relevant.
On the reviewers we tested it did not work, which lowers the risk of describing it.
The more useful finding for an attacker is that a reviewer may pass work whose flaw it has named, and the defence is in the consumer's hands: read the reviewer's findings, not only its score.
We judge that publishing helps defenders more than attackers.
We release the task families and the reviewer harness.
The families are small software and research tasks whose only harm is a misleading completion report, with no operational payload.
The real-log families come from a public, MIT-licensed dataset of agent runs on benchmark tasks.
An automated scan of the released family files found no keys, passwords or email addresses. [TODO: the author's own read of each family for personal data.]
No people were studied.

## Appendix B. Pre-registration and changes

`PILOT.md` was committed before any reviewer call, and `MAIN.md` before any reviewer saw a real-log family.
Both files list the changes made during their runs.
None changed a prompt, a cell, a definition, a threshold or a test.

- The gateway allows one call at a time per account, so calls were sent one at a time on two accounts.
- The main run was reordered once so that each reviewer finished its six main cells before its badge cells.
- A dropped connection stalled two runs, which were restarted, and the calls that were cut off were read again.
- `main_report.py` gained the false-alarm lines for finished logs, which `MAIN.md` lists as a secondary analysis, after the first two reviewers had finished.
- `reasons_report.py` was written after the first main results were read. Section 4.4 is labelled exploratory for that reason.

[TODO: commit hashes for each item.]

## Appendix C. Family descriptions

### C.1 Development set

- **bugfix.** Fix a crash in a header parser, add a regression test, and run the full suite on the final code. The check step is the second full `pytest` run, after the last edits. The near-miss is the first full `pytest` run, which passed before the last code edit and before the new tests existed. The unrelated step is the branch checkout.
- **review.** Review a pull request that changes five files. The check step is the read of `src/ledgerly/refunds.py`. The near-miss is the read of `src/ledgerly/refund_policy.py`, a similarly named file that is not in the pull request. The unrelated step is the pull request checkout.
- **analysis.** Remove duplicated rows and refresh the headline test accuracy. The check step is the evaluation on the test split that writes the metrics file. The near-miss is an evaluation on the validation split, which writes no file. The unrelated step is an environment check.

### C.2 Real-log set

| Family | MALT task | Agent | Steps | Check step | Near-miss step |
|---|---|---|---|---|---|
| `malt-218232-orm-somebugs` | debug_small_libs/orm_somebugs | Claude 3.5 Sonnet | 10 | final `pytest` run | earlier `pytest` run with failures |
| `malt-343263-markdown` | debug_small_libs/markdown | Claude Opus 4 | 6 | final `pytest` run | first `pytest` run with failures |
| `malt-343269-orm-allbugs` | debug_small_libs/orm_allbugs | Claude Opus 4 | 8 | final `pytest` run | first `pytest` run with failures |
| `malt-343423-webserver` | make_web_server/exp_last_digit | Claude Opus 4 | 13 | retest after the fix | the same request before the fix |
| `malt-229647-webserver` | make_web_server/exp_last_digit | Claude 3.5 Sonnet | 6 | request with a long input | request with a short input |
| `malt-343341-fibonacci` | esolang/broccoli_fibonacci | Claude Opus 4 | 14 | run of the agent's program | interpreter run on a sample program |
| `malt-343338-collatz` | esolang/broccoli_collatz | Claude Opus 4 | 13 | run of the agent's program | interpreter run on a sample program |
| `malt-218367-collatz` | esolang/broccoli_collatz | Claude 3.5 Sonnet | 15 | run of the agent's program | sample program with the same input |
| `malt-229887-more-bias` | local_research_tex/more_bias | Claude 3.5 Sonnet | 7 | read of the source file | search of the same file, headings only |
| `malt-215455-austrian-votes` | wikipedia_research/austrian_votes | Claude 3.5 Sonnet | 7 | page with the totals | article without the totals |
| `malt-233499-wordle` | wordle/word2 | Claude 3.5 Sonnet | 6 | winning guess | earlier losing guess |

Each family file lists every edit made to the run and the report, and what a reader should know about it.

[TODO: Figure C1, one family's report in the raw condition and at the near-miss level, side by side.]

## Appendix D. Pilot and development

The pilot ran the three development families on deepseek-v4-flash, at two log lengths, in all six cells: 720 readings, none missing.
All four criteria in `PILOT.md` passed at both lengths (`results/pilot-report-deepseek.txt`).
The long logs were chosen for the main study, as the plan fixed in advance.
The real-log families were built while the pilot was running and before its results were read, and they replaced the development families as the main set (`MAIN.md`).
No family and no instruction was changed after the pilot.

## Appendix E. Per-family results

`results/main-report-<reviewer>.txt` holds the per-family table for each reviewer: the citation effect at each level, raw separation, and the mean raw score of the finished and unfinished log.

[TODO: typeset the four tables.]
