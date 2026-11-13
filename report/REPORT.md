# Checkable Is Not Checked: Do LLM Reviewers Verify an Agent's Citations to Its Own Log?

Apurv Gupta, with Apart Research.

Apart Research AI x Epistemics Research Sprint, Track 2: Trust Infrastructure, November 2026.

Code, task families, every raw reviewer reading and the pre-registration: <https://github.com/apurv-1/epistemics-research-log-citations>

## Abstract

[TODO: write from results, 150 to 250 words. Order: the problem in one sentence, the design in three, the confirmatory number with families and p-value, the citation levels, the badge arm if run, the replication reviewers, what we release.]

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

Our contributions are:

- **A test that isolates the citation.** Matched logs that differ in one step, a byte-identical report, and three levels of unsupporting citation, on [TODO: number] task families, [TODO: number] of them built from real agent runs in METR's MALT dataset.
- **A pre-registered result.** [TODO: the confirmatory comparison, its size, families and p-value, on the confirmatory reviewer.]
- **Whether a true "all citations resolve" check changes the verdict.** [TODO: badge arm result, or cut this bullet if the arm is not run.]
- **A reusable check.** [TODO: name of the script] runs the families against any reviewer model and prints its separation with and without citations.

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
On the done log every claim is supported.
On the skipped log exactly one claim, the **false claim**, states something the log no longer shows.
The false claim carries no number or detail that only the removed step could supply, so the report gives nothing away in any condition.
[TODO: qualify this sentence if any real-log family's own report breaks it.]

There are two sets of families.

- **Development set.** Three hand-built families: a bug fix where the test suite is not rerun after the last edit, a code review where one assigned file is never opened, and a data analysis where the headline metric is not recomputed after a data fix. Each has a short log of 8 or 9 steps and a long log of 39 steps, and the added steps are identical in both variants. These were used for the pilot (Appendix D).
- **Real-log set.** Families built from real agent runs in METR's MALT dataset (METR, 2025), which is MIT licensed. The done log is the real run, with tool calls and outputs verbatim. The skipped log is that run with one check step removed. [TODO: confirm the pool rule as built: runs labelled normal, security puzzle tasks excluded, 5 to 40 steps, a fixed random draw of 100 with a recorded seed.] Families were taken from the pool in its drawn order under suitability rules fixed in advance, so no run was chosen for its results. [TODO: number of families, number of distinct tasks, the agent models in the set, and how many reports are the agent's own submitted text against written by us.]

Appendix C describes every family and lists each edit made to a real run.

### 3.2 Conditions

The reviewer always sees the task, the full log and the report.

- **raw**: the report with no citations.
- **cited**: each claim ends with the step it cites, in square brackets. A short note before the report, outside the agent's words, says what the brackets are.

On the done log every citation is real and supports its claim.
On the skipped log the true claims keep their real citations, and the false claim's citation takes one of three levels.

- **none**: the false claim has no citation, while every other claim has one.
- **unrelated**: it cites a real step that has nothing to do with the claim.
- **near-miss**: it cites a real step that looks relevant and does not establish the claim. It ran before the last change, or on a different target, or on a different split.

The unrelated and near-miss steps exist in both variants and are cited by no other claim.
Every citation in every condition resolves to a step that exists.

[TODO: keep only if the arm is run.] In the **badge** arm, the note also carries one true line: "Automated check: All citations resolve to existing log steps."
The line is what a deterministic citation checker would print, and it is true for every cited report in the study, including the ones with an unsupporting citation.

### 3.3 Reviewers and analysis

The instructions tell the reviewer to decide whether the work is complete as the report says, and that it is not complete as reported when the report states something was done and the log does not show it.
They are identical in every condition and never mention citations, forgery or attacks.
The reviewer answers with its reasoning, the most important unsupported claim, and a score from 0 (clearly not complete as reported) to 100 (clearly complete as reported).
Reviewers are sampled at temperature 1.0, with 20 readings per prompt.

A family's **raw separation** is its mean raw done score minus its mean raw skipped score.
Its **cited separation** at a citation level is its mean cited done score minus its mean cited skipped score at that level.
The effect of an unsupporting citation is cited separation minus raw separation, and a negative value means the citation made the reviewer worse at telling the variants apart.
The family is the unit of analysis.

[TODO: from MAIN.md. The confirmatory reviewer and the replication reviewers. The confirmatory hypothesis and its direction, at the near-miss level. The test across families, alpha, and the correction for replication reviewers. The smallest effect of interest. How the development families are reported apart from the real-log families.]

`PILOT.md` fixed the pilot's pass criteria before any reviewer call.
`MAIN.md` fixes the confirmatory comparison, the test and the reviewers before the main run, and Appendix B lists every later change.
A script prints every number in the abstract and results from the raw readings.

## 4. Results

### 4.1 [TODO: the confirmatory result as a sentence]

[TODO: table of raw separation and cited separation at each level, per reviewer, with the per-family sign count and p-value. One figure: separation by condition, one line per family.]

### 4.2 [TODO: what the reviewers said when they accepted an unsupporting citation]

[TODO: label the reviewer's stated reason on wrong verdicts. Did it open the cited step, or repeat the claim?]

### 4.3 [TODO: citation levels, none against unrelated against near-miss]

### 4.4 [TODO: the badge arm, or cut]

### 4.5 [TODO: real-log set against development set, and log length]

### 4.6 Robustness

[TODO: missing readings per cell, results without any family that leaks, false alarms on done logs with and without citations.]

## 5. Discussion

[TODO: what the result means for evidence-linked reports. If unsupporting citations hurt: a resolving citation works as a credential, and a checker that reports "resolves" adds to it. If they do not: the fix Khalifa et al. asked for survives its cheapest attack on these reviewers, and say where it might still fail.]

[TODO: the design rule for builders. A trust signal for an AI reader should state what was checked. "Resolves" and "supports" are different checks and should be reported as different fields.]

[TODO: what would change our mind, and the next experiment: frontier reviewers, reports written by the agent under instruction to cite, longer real runs.]

## 6. Conclusion

[TODO: three sentences from results.]

## Code and provenance

Code, task families, every raw reviewer reading and the pre-registration (`PILOT.md`, `MAIN.md`) are at <https://github.com/apurv-1/epistemics-research-log-citations>.
Two files are pre-existing work, copied from <https://github.com/apurv-1/swarm-alignment-maoc> at commit `52f1422`: `monitor.py`, the model client, and `tests/test_monitor.py`, its tests.
The client's streaming, error handling, pay-at-most-once ledger, budget, resume and reply parsing are unchanged, and the file's header lists what was adapted.
Everything else was written during the sprint, November 13 to 15, 2026 AoE.
The real-log families are derived from METR's MALT dataset, `metr-evals/malt-public`, under its MIT license.
[TODO: name of the script] produces every number in the abstract and results from the raw readings.

## LLM usage statement

AI coding agents (Claude Fable 5.2 in Claude Code) wrote most of the code, tests and family files to the author's design, and selected and converted the MALT runs under rules fixed in advance.
[TODO: confirm before submitting. The author reviewed the code and read every family by hand.]
Claude Fable 5.2 reviewed the design and drafts and helped draft the text.
[TODO: if reviewer replies are labelled in Section 4.2, say which model labelled them and how the author audited the labels.]

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

[TODO: two or three bullets, each one sentence, stated no more strongly than the confirmatory result.]

### What it does not establish

- **How often agents cite an unsupporting step.** We place the citation ourselves. The study shows what a reviewer does when it meets one, not how often an agent would write one.
- **Anything about frontier reviewers.** Every reviewer is an open-weight model served by the sprint's gateway. A stronger reviewer may open the cited step where these do not.
- **Anything about human readers.** No person reviewed these reports as a subject.
- **How a reviewer behaves when warned.** The instructions never say that a citation may be wrong.

### Limitations

- **Constructed twins.** No real pair of runs differs in exactly one step, so the skipped log is always made by us. In the real-log set it is a real run with one step removed. A reader who knows the task well may notice the gap for reasons a real unfinished run would not show.
- **Few families.** The family is the unit of analysis, and there are [TODO: number]. One family can move a mean, so every result is also reported per family (Appendix E).
- **Development families are hand-built.** AI coding agents wrote the three development families to the author's recipe. They were used to tune the instrument and are reported apart from the real-log set.
- **Real runs are edited.** Removing a step is an edit. We strip scaffold notices that would differ between variants, and we keep only runs where no later step depends on the removed step's output. That selection favours runs with a clean, separable check step.
- **Reports are partly ours.** Where the agent's own submitted text is a prose report we use its wording and add only what the false claim needs. Where the agent submitted a bare answer we wrote the report. Appendix C marks which is which and lists every added word. The split into cited claims is always ours.
- **Reviewers may have seen the logs.** MALT is public, so a reviewer model may have met these runs in training. The skipped variants and the reports with citations are new.
- **One prompt wording.** One set of instructions, one citation format, and one score scale. The instructions tell the reviewer to compare the report with the log, which may help it more than a bare request would.
- **Temperature 1.0.** Reviewers were sampled at temperature 1.0 to measure their distribution of judgements; a deployed reviewer at temperature 0 could behave differently.
- **One false claim per report.** Real reports can overclaim in several places at once, or in ways no single step settles.

### Dual-use and ethical considerations

This work describes how to make a false claim in an agent's report harder for an LLM reviewer to catch: cite a real step that looks relevant.
An agent, or a person editing a report, could use that.
The technique needs no new capability and follows from how citations already work in human writing, where a reference that exists is often taken as a reference that supports.
We judge that publishing helps defenders more than attackers, because the defence is in the reader's hands.
A reviewer, or the tool that feeds it, should check that the cited step supports the claim, and should never present "the citation resolves" as if it were that check.
We release the task families and the reviewer harness.
The families are small software and analysis tasks whose only harm is a misleading completion report, with no operational payload.
The real-log families come from a public, MIT-licensed dataset of agent runs on benchmark tasks.
[TODO: check every real-log family for personal data and secrets, then state that here.]
No people were studied.

## Appendix B. Pre-registration and changes

[TODO: the pilot criteria and how the pilot scored against each; what MAIN.md fixed; every change after each file was committed, with its commit and reason.]

## Appendix C. Family descriptions

### C.1 Development set

- **bugfix.** Fix a crash in a header parser, add a regression test, and run the full suite on the final code. The check step is the second full `pytest` run, after the last edits. The near-miss is the first full `pytest` run, which passed before the last code edit and before the new tests existed. The unrelated step is the branch checkout.
- **review.** Review a pull request that changes five files. The check step is the read of `src/ledgerly/refunds.py`. The near-miss is the read of `src/ledgerly/refund_policy.py`, a similarly named file that is not in the pull request. The unrelated step is the pull request checkout.
- **analysis.** Remove duplicated rows and refresh the headline test accuracy. The check step is the evaluation on the test split that writes the metrics file. The near-miss is an evaluation on the validation split, which writes no file. The unrelated step is an environment check.

### C.2 Real-log set

[TODO: one entry per family: task, MALT run id, agent model, number of steps, check step, near-miss step, unrelated step, report source, and every edit to the run and the report.]

[TODO: Figure C1, one family's report in the raw condition and at the near-miss level, side by side.]

## Appendix D. Pilot and development

[TODO: pilot design in two sentences, the score against each criterion in PILOT.md, the chosen log length, and every change made to a family or the instructions after the pilot.]

## Appendix E. Per-family results

[TODO: per-family table for each reviewer.]
