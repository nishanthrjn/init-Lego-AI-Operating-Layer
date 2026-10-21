# P1 prior art and independently authored procedure

Date: 2026-10-21. Scope: FORGEAI-GEMMA4-P1-PROCEDURE-PROMPT-1.
Public configurations are prior art, not authority for ForgeAI production or
proof of effectiveness. No external prompt text or implementation was copied.
The P1 procedure was written from the task requirements and verified harness
contracts. Downloaded notebooks must remain outside this repository.

## Credited sources

| Author/source | Link | Licence and inspected evidence | Relevance |
| --- | --- | --- | --- |
| Dmitrii Gluzdov, *Gemma 4: Public Agent Ideas and Evidence*, version 7 | https://www.kaggle.com/code/dmitriigluzdov/gemma-4-public-agent-ideas-and-evidence | Stored page screenshot shows Apache-2.0 for the notebook; its credits distinguish original measurements/documentation as CC BY 4.0. No code/data copied. | Empirical caution, reported repeated-run variability, local timing and 12B timeout, provenance of the procedure family. |
| Hanh Tran (`honghanhhh`), *Gemma 4 Baseline / LB 0.24*, version 6 | https://www.kaggle.com/code/honghanhhh/gemma-4-baseline-lb-0-24 | Stored screenshot explicitly shows Apache-2.0. | Issue contract, preservation of unspecified behavior, related implementations, scratch hygiene and final working-tree inspection. The title's 0.24 is not a verified score of the inspected version; screenshot badge says 0.18 V3. |
| Igor Zharov / `flexonafft`, budget-aware prompt ancestor | https://www.kaggle.com/code/flexonafft/gemma-4-budget-aware-coding-agent-v2 | Apache-2.0 is attributed by Gluzdov's credits; upstream version/licence not independently opened here. | Credited upstream ancestor, not text or code reused by P1. |

The inspected page images are preserved at
`docs/CompetitionWebPages-Screenshots/kaggle_com_code_dmitriigluzdov_gemma_4_public_agent_ideas_and_evidence_20261021_013830.png`
and `.../kaggle_com_code_honghanhhh_gemma_4_baseline_lb_0_24_20261021_013846.png`.
Their embedded retrieval timestamps are 2026-10-20 23:38:46 UTC and 23:38:58 UTC.
This is a dated local artifact review, not a fresh verification of current rankings.
The public browser was unavailable during this slice; links above are visible in
the stored pages. Gluzdov also credits verracodeguacas, Matterhorn3838, Darlush
Afshar and jvnhonglei; no specific notebook URL or independent licence verification
for those indirect sources is asserted here.

## Ideas adopted, changed and rejected

- Adopted as design hypotheses: extract the issue's behavioral contract, limit
  search scope, attempt a justified edit early, preserve unaffected inputs,
  inspect parallel implementations where the same contract applies, reproduce
  the issue, and inspect status/diff before submitting. P1 uses original wording
  and its own 6/18/24-call and 90/240/300-second checkpoints.
- Adopted from official mechanics, not public prompt authority: keep reproduction
  scripts outside the patch, leave protected files unchanged, verify before
  submission, and account for remaining time. These are backed below.
- Rejected: guessing an edit solely to meet a deadline; forcing a nonempty patch;
  declaring all dependency failures harmless; universal claims that every file
  enters the patch; verification or repair after submit_patch; treating a public
  score badge as a controlled causal result.
- Neither a graph-tool ban nor graph-tool instruction is present. P1 exposes the
  same six M2 tools. Adding graph tools belongs to a separately authorized P2.
- Retained M2 sampling/model instead of copying public sampling, 8-minute budgets,
  multi-agent composition or 12B models. No inference about optimality is made.

## Evidence strength and hypotheses

Gluzdov's *What changes the score: measured comparisons*, *The submitted agent*
and *Practical guidance and limitations* report 58 public tasks, identical-file
outcomes spanning 7–13 tasks, and a 12B run with no score after the twelve-hour
limit. 1/58 is approximately 0.01724 score units. The span's half-width is three
tasks; it is not a calibrated confidence interval or a universal +/-3 noise law.
The 116-task total is a public planning estimate (58 plus an assumed equal private
split), not verified hidden task count. The report also discusses 120-task
planning; neither estimate is an organizer contract established by this slice.

Our supplied observations remain M2 score 0.05 and B2 SCORING; no B2 score is
invented. P1 changes prompt and budgets relative to B2, so it is a combined
procedure/budget candidate, NOT an isolated prompt-effect experiment. Matched
budgets, repeated controlled runs and independent task fixtures are needed to
attribute improvement. No model/evaluation run is authorized here.

## Harness authority and limitations

Primary local documentation: [HARNESS_README](docs/HARNESS_README.md), sections
5.3 (agent loop), 6.1 (execution/submission/status), 7.1 (budgets), 8.1
(patch extraction/fallback), 8.2 (verification), and 10 (practical guidance).
Implementation: pinned `docs/archive/swegemma-0.2.11-py3-none-any.whl`, SHA256
`9ad876581f3acde8ec3c369858f0834e2b9f41a3cffce3ca42f09cb090aea9d3`.
Inspected as ZIP text only; not installed or imported.

| Question | Verified in supplied implementation/documentation | Limits / UNKNOWN |
| --- | --- | --- |
| Edited but unsubmitted tree | `harness/agent_runner.py:1048–1103` captures an unsubmitted diff on the fallback path; `evaluate.py:316–377` proceeds to verification with a nonempty patch even when agent_error is present. README 8.1 describes fallback reaching scoring. | Extraction can fail. Hidden inference.py/metric.py parity and hard global-timeout behavior remain UNKNOWN. Do not rely on fallback as a completion strategy. |
| submit_patch termination | `tools/execution.py:76–116` captures diff and sets patch_submitted; `harness/agent_runner.py:859–864,920–922` exits on submission. README agent-loop section agrees. | Tool docstrings at execution.py:80–81 and 168–169 suggest multiple submissions; runner behavior is the governing observed behavior. Do not plan post-submit verification. |
| Untracked files | execution.py:86–89 and agent_runner.py:1057–1061 use git add -N followed by binary diff against _swegemma_baseline, falling back to HEAD. README 8.1 explains intent-to-add. | Git-ignored files are excluded; protected sections are stripped. Do not claim all new files are included. |
| Protected paths | `harness/verification.py:62–101`: Python test filename/directory patterns; conftest.py, pytest.ini, .pytest.ini, pyproject.toml, tox.ini, setup.cfg, sitecustomize.py, usercustomize.py, _swegemma_stubs.py, *.pth; plus task-specific protected paths. execution.py:103–110 and agent_runner.py:1065–1071 apply filtering. README 8.2 describes test-patch targets reset during verification. | Hidden task-specific protected paths are not available. The P1 prohibition on editing any test directory is deliberately more conservative than Python-only directory matching in source. |
| Budget values | `config.py:149–195` passes time/tool/turn values into EvaluationBudget and command timeout into HarnessLimits. build_submission_limits at :34–68 does not add a static ceiling to those four values. | Hidden scorer environment overrides: UNKNOWN. Local/compiler success does not prove hosted budget enforcement. |
| Dynamic timeout | execution.py:31–47 uses the configured timeout bounded by remaining time with a five-second floor. README 6.1 agrees. | This is common to M2/B2/P1, not a P1 treatment. Prompt checkpoints are advisory; soft overruns and long commands can consume the reserve. |
| Status/call accounting | execution.py:76,119 marks submit_patch/get_status as not counted tool calls; :126–140 reports counted calls and remaining seconds. | They still consume runtime/turn resources; P1 does not poll endlessly or promise they are cost-free. |

P1's six minutes is a smaller cap than the public eight-minute family, not a
guarantee of finishing the competition: 116 x 6 = 696 minutes = 11.6 hours,
leaving only 24 minutes BEFORE setup/startup/other overhead. 116 x 8 = 928 minutes
= 15.47 hours (often summarized as about 15.7; 118 x 8 is 15.73). The supplied
15.7 figure is approximate, not exact arithmetic for 116. A 120-task workload at
six minutes consumes all 12 hours before overhead. Parallelism, timing tails,
hidden task count and hosted overrides are UNKNOWN/UNMEASURED.

Before any budget increase, a separately authorized local harness run must measure
mean end-to-end task time including setup, tail times, timeouts and overhead on
representative fixtures. Mean alone cannot establish a hard runtime guarantee.
No such measurements have been made here. No novelty or performance gain is claimed.
