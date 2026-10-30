Controls: 05706c6a. Retained metadata transcription; UNKNOWN is not an unresolved verdict. No superiority claim.

| Task | P1 | P1b | P1c | P2 | P3 | P3g |
|---|---|---|---|---|---|---|
| fastapi_14492 | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED |
| rich_3905 | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED |
| fastapi_5624 | RESOLVED | RESOLVED | UNRESOLVED | RESOLVED | RESOLVED | RESOLVED |
| rich_3454 | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED |
| rich_3934 | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNKNOWN | UNRESOLVED | UNRESOLVED |
| fastapi_15800 | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNKNOWN | UNRESOLVED | UNRESOLVED |
| rich_4075 | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED |
| fastapi_14419 | RESOLVED | UNRESOLVED | RESOLVED | UNKNOWN | UNRESOLVED | UNRESOLVED |
| rich_3471 | UNRESOLVED | UNKNOWN | UNRESOLVED | UNKNOWN | UNRESOLVED | UNRESOLVED |
| fastapi_5077 | RESOLVED | UNRESOLVED | UNRESOLVED | RESOLVED | RESOLVED | UNRESOLVED |
| rich_4079 | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED |
| fastapi_11194 | UNRESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED |
| rich_4076 | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED |
| fastapi_14786 | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED |
| rich_3067 | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED | RESOLVED |
| fastapi_15589 | UNRESOLVED | RESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED |

P3 dev-16v same-config replicate (maintainer-reported; attempt2 artifacts not
independently analyzed). The historical six-run table above retains P3 attempt1.
Attempt2 completed in 4935 s and is retained at
`C:\Work\Gemma4Localtest\local_eval_p3_dev16v_attempt2`.

| Measure | P3 attempt1 | P3 attempt2 |
|---|---:|---:|
| Resolved / verifiable | 8/16 | 6/16 |
| ContextWindowExceeded | 0 | 0 |
| Session timeouts | 4 | 6 |
| Mean task duration (approximate) | 244 s | 273 s |
| Mean-based projected runtime (approximate) | 8.0 h | 8.9 h |

Two outcome flips: `fastapi_5624` 1 -> 0 and `fastapi_11194` 1 -> 0
(the latter via session timeout). Attempt2 session timeouts: `rich_3934`,
`fastapi_14419`, `rich_3471`, `rich_4079`, `fastapi_11194`, `fastapi_15589`.

Observed noise floor for the maintainer's decision: **2 flips**. This is one
same-config replicate, not an estimated population bound or significance test.
P4 must satisfy **both >=11/16 resolved and bootstrap_upper95_hours <=11 h**.
The 8.9 h projection is mean-based and does not establish bootstrap gate success.
At this pre-registration stage no P4 result or adoption decision was available; the later decision is recorded below.

P4 dev-16v attempt1: **COMPLETED**, 4597 s, retained at
`C:\Work\Gemma4Localtest\local_eval_p4_dev16v`. Maintainer-reported results:
8/16, two session timeouts (P3 attempts: four and six), zero context errors,
mean task duration approximately 253 s, mean-based projection approximately
8.3 h, bootstrap upper95 approximately 8.7 h. Timeout task identities were not
supplied. Gains versus P3 attempt1: `fastapi_14419`, `rich_4079`; losses:
`fastapi_5624`, `fastapi_11194`. The maintainer reports `rich_4079` as its first
success in eight runs (unsolved in the seven earlier runs).

**Decision: retain P3.** P4 - P3 attempt1 = 0 <= observed flip floor 2;
8/16 fails the pre-registered >=11/16 score requirement. The reported bootstrap
8.7 h meets <=11 h, but both conditions are required. Four paired outcome flips
(two gains, two losses) are distinct from the zero net gain. No superiority claim.

Eight comparable dev-16v runs, confirmed by the maintainer: P1 (dev-30
restricted to dev-16v), P1b (attempt1+attempt2 merged as one run), P1c, P2,
P3 attempt1, P3g, P3 attempt2 and P4 attempt1. There is no ninth run.
UNKNOWN below preserves historical verdicts; it is not an unresolved outcome.
Solve frequency uses all eight runs and is pending where any verdict is UNKNOWN.
P3 attempt2/P4 columns are transcribed from the reported exhaustive flips.

| Task | P3 attempt2 | P4 attempt1 | Confirmed solved | Confirmed unresolved | Unknown | Solve frequency |
|---|---|---|---:|---:|---:|---|
| fastapi_14492 | RESOLVED | RESOLVED | 8 | 0 | 0 | 8/8 |
| rich_3905 | RESOLVED | RESOLVED | 8 | 0 | 0 | 8/8 |
| fastapi_5624 | UNRESOLVED | UNRESOLVED | 5 | 3 | 0 | 5/8 |
| rich_3454 | RESOLVED | RESOLVED | 8 | 0 | 0 | 8/8 |
| rich_3934 | UNRESOLVED | UNRESOLVED | 0 | 7 | 1 | Pending: 1 UNKNOWN |
| fastapi_15800 | UNRESOLVED | UNRESOLVED | 0 | 7 | 1 | Pending: 1 UNKNOWN |
| rich_4075 | UNRESOLVED | UNRESOLVED | 0 | 8 | 0 | 0/8 |
| fastapi_14419 | UNRESOLVED | RESOLVED | 3 | 4 | 1 | Pending: 1 UNKNOWN |
| rich_3471 | UNRESOLVED | UNRESOLVED | 0 | 6 | 2 | Pending: 2 UNKNOWN |
| fastapi_5077 | RESOLVED | RESOLVED | 5 | 3 | 0 | 5/8 |
| rich_4079 | UNRESOLVED | RESOLVED | 1 | 7 | 0 | 1/8 |
| fastapi_11194 | UNRESOLVED | UNRESOLVED | 5 | 3 | 0 | 5/8 |
| rich_4076 | UNRESOLVED | UNRESOLVED | 0 | 8 | 0 | 0/8 |
| fastapi_14786 | RESOLVED | RESOLVED | 8 | 0 | 0 | 8/8 |
| rich_3067 | RESOLVED | RESOLVED | 8 | 0 | 0 | 8/8 |
| fastapi_15589 | UNRESOLVED | UNRESOLVED | 1 | 7 | 0 | 1/8 |

## Tool argument rejection evidence and P5 preregistration

Historical baseline: maintainer-reported, not recomputed here. Eight comparable dev-16v runs
remain the cohort; P1b merged attempts count once. Rejected calls were previously
ordinary tool calls; TOOL_ARGUMENT_REJECTED now identifies the observation text
"mandatory input parameters are not present" separately from outcome failures.

| Run | Rejected / attempted edit+write |
|---|---:|
| P1c | 17/40 |
| P3 attempt1 | 25/48 |
| P3 attempt2 | 13/36 |
| P4 attempt1 | 30/59 |

P4 rich_3934 reportedly had 27 consecutive rejections before timeout. P3 attempt1
rich_4079 had 9/9 rejected calls and no patch. The exact identical-resend counts,
other-run all-tool rates and per-task breakdowns await maintainer analysis. P3 all-tool counts and patch-production baselines are now reported in the P5 attempt1 section below.
The trailing-backtick parser explanation and run_command 0/1135 are attributed
to the maintainer's Syurolh forum report (October 22); no causal experiment ran here.

P5 changes only P3's prompt and routes source edits through a quoted Python
heredoc in run_command. Each P5 run must have all-tool rejection rate <=5% and
nonempty-patch task share at least the mean of the two P3 shares. Report edit/write
rate separately (N/A with zero attempts), per-task run_command source-edit
completion markers, and final patch bytes. Marker counts are lower bounds;
unmarked edits require trace review, not inference from tool names.
Across two complete P5 runs, mean solved must be >=7, and each bootstrap upper95
projection must be <=11 hours. Report all per-task flips against both P3 runs
and between P5 runs. Missing evidence blocks adoption; lower patch production
fails even with zero edit/write attempts. Retain P3 until every gate passes and
subsequent submission qualification succeeds. See local_eval/README.md for commands.

## P5 dev-16v attempt1 — completed (historical run1 report)

Maintainer-reported; no traces, timing projections or evaluation recomputed here.
Retained at `C:\Work\Gemma4Localtest\local_eval_p5_dev16v_attempt1`.
The historical eight-run cohort above is preserved; this P5 run is additional.

| Metric | P3 attempt1 | P3 attempt2 | P5 attempt1 |
|---|---:|---:|---:|
| Solved / 16 | 8 | 6 | 9 |
| Tool-argument rejections / all tool calls | 25/357 | 13/386 | 0/367 |
| Nonempty-patch tasks / 16 | 11 | 7 | 11 |

P5 completed in 4448 s, with mean task time approximately 247 s and bootstrap
upper95 time-fit approximately 8.6 h. Four session timeouts, zero context errors.
No edit_file/write_file calls: edit/write rejection rate is N/A, not zero percent.
The maintainer corrected attempt1 to 17 source-edit heredocs among 67 quoted-EOF run_command calls; these are not
asserted to be completion-marker counts. Per-task edit counts and timeout task
identities were not supplied.

| Baseline | P5 gains | P5 losses |
|---|---|---|
| P3 attempt1 | fastapi_15589 | None |
| P3 attempt2 | fastapi_15589, fastapi_5624, fastapi_11194 | None |

Run1 gates (a), (b), (c), and time are met as reported: 0/367 rejections;
11/16 nonempty patches versus P3's mean 9/16; 17 source-edit heredocs (corrected from 35);
approximately 8.6 h <=11 h. The two-run mean gate was pending at this report; see the completed attempt2 decision below.
The provisional retain-P3 decision is superseded by the maintainer adoption decision below. This is development
evidence, not submission qualification or a statistical superiority claim.

## P5 attempt2 and submission-candidate decision

Maintainer-reported: attempt2 COMPLETED in 4654 s at
`C:\Work\Gemma4Localtest\local_eval_p5_dev16v_attempt2`. No analysis rerun here.

| Metric | P5 attempt1 | P5 attempt2 | Gate |
|---|---:|---:|---|
| Solved / 16 | 9 | 9 | Mean 9.0 >= P3 mean 7.0 |
| Tool-argument rejections | 0/367 | 0/388 | Both 0% <=5% |
| Edit/write calls | 0 | 0 | Edit/write rejection rate N/A |
| Nonempty patches | 11 | 12 | Both >= P3 mean 9 |
| Bootstrap upper95 hours | ~8.6 | ~9.0 | Both <=11 h |
| Session timeouts | 4 | 3 | Descriptive |
| Context errors | 0 | 0 | Descriptive |
| Mean task seconds | ~247 | ~260 | Descriptive |

Two flips versus attempt1: fastapi_14419 0->1 and fastapi_15589 1->0.
Eight tasks solved in both runs, including fastapi_5624 and fastapi_11194.
Attempt2 gains fastapi_14419 versus P3 attempt1 and additionally recovers
fastapi_5624 and fastapi_11194 versus P3 attempt2; no P3-solved task lost.

**Maintainer decision: two-run gate PASSED; P5 replaces P3 as submission candidate.**
The missing attempt2 metric is now supplied: 23 source-edit heredocs among 76
quoted-EOF run_command calls. Attempt1 is corrected from 35 to 17 among 67 calls;
the earlier rough text search double-counted repeated trace text.

Method QUOTED_EOF_SOURCE_EDIT_HEURISTIC_V1: parse tool-call objects, count each
run_command call whose arguments.command contains exact <<'EOF' once. The source-edit
subset excludes /tmp in text before the first << and requires any literal read_text,
write_text, replace( in the body after the opener line and before standalone EOF.
This is a heuristic lower bound, not proof of successful writes or marker counts.
The guard is unchanged and the required values are present; execution NOT RUN.
The maintainer will confirm analyzer outputs 67/17 and 76/23 before qualify_p5.

The maintainer also reports official Kaggle CPU compilation and local reconciliation
passed: P5_OFFICIAL_COMPILER_VALIDATED; BYTE_IDENTITY_VERIFIED; P5_PACKAGE_VALIDATED.
Receipt `e13f9b40a18f23ef2eaa2c4856342e182b567f3794fe6da9d8859e9bbe8db651`;
ZIP `6db4109a73cfea1c803c17e86f498406461141904dac58efe441f10cca1fe219`, 6501 B,
byte-identical to the evaluated experimental package. Full identities reference
previously supplied hashes; the official manifest hash was not supplied.
No submission executed or new public score claimed. Historical eight-run
frequencies remain the pre-P5 cohort, not a recomputed ten-run table.

## P6 dev-16v attempt1: negative ACI result

Maintainer-reported **COMPLETED**, 4840 s including reported startup 377 s;
retained externally (exact path not supplied). Solved **7/16**, versus P5 **9/16
in both runs**. Nonempty patches: **7**. No edit_file/write_file calls.

| Failure category | Tasks |
|---|---|
| time_budget, NO_PATCH (5) | fastapi_5624, rich_3934, fastapi_14419, rich_4076, fastapi_15589 |
| Tool-cap, empty submission (4) | fastapi_15800, rich_4075, rich_3471, rich_4079 |

The maintainer attributes the regression to creating forge_edit.py anew for
every task with a 63-line heredoc, consuming budget and context. The model
repeatedly used the helper before creating it, sometimes noticing only at
300-360 s: "I forgot to create the forge_edit.py helper". This is a reported
trace interpretation, not a measured causal decomposition or evidence that
ACI guardrails generally fail.

**Gate FAILED; P6 REJECTED; P5 retained. Attempt2 CANCELLED.** Seven solved is
below the mean target of 10; a second run would need 13/16 to reach mean 10.
Independently, attempt1's 7 patches fail the required >=11 in EACH run, so even
that second result could not rescue adoption. No two-run P6 mean is reported.
Unreported rejection rates, replacement/syntax counts and bootstrap upper95
remain unknown. No analysis or workload was executed for this record update.

## S1 dev-16v attempt1 and S2 preregistration

Maintainer-reported COMPLETED: 1599 s, startup 343 s, retained externally (path
not supplied). Solved 3/16: rich_3905, rich_3454, fastapi_14786. Eight empty-patch
submissions: fastapi_14492, fastapi_5624, rich_3934, rich_4075, fastapi_14419,
fastapi_11194, rich_3067, fastapi_15589. Five wrong patches; zero time_budget.
Mean 78 s/task and 8/28 tool calls. Two edit_file rejections (~1.6%, exact
denominator not supplied). Operational gate PASSED as reported; S1 is retained
as the E4B bonus fallback, not recorded as a completed Kaggle submission.

Failure modes: claims without edits in diff, stopping on missing test-only
inline_snapshot/dirty_equals dependencies, premature submission and non-unique
edit_file targets. Exact bootstrap bound and harness-error count not supplied;
no independent analysis executed.

S2 changes only S1's prompt. Preregistered: complete dev-16v, solved >=5/16,
empty patches <=3, projected <=10.5 h (existing bootstrap upper95 time-fit),
all required; otherwise keep S1. Existing operational controls still apply.

## S2 dev-16v attempt1: more patches, no solved-count gain

Maintainer-reported COMPLETED, 1927 s, startup 338 s; externally retained, path
not supplied. ZIP d5a6b30c matches the supplied S2 build SHA256. Solved 3/16:
fastapi_14492, rich_3905, fastapi_14786. Empty patches 2: rich_4075, rich_4076;
wrong patches 11. Mean 92 s/task, 11.4 calls; zero harness errors.
**Gate FAILED (3 < 5 solved); S1 retained per preregistration.** Bootstrap bound
not supplied; no timing pass inferred.

Empty submissions fell 8 -> 2 and wrong patches rose 5 -> 11, with solved count
unchanged. This supports the intended patch-production effect, not improved
correctness or an isolated causal claim. Gained fastapi_14492, lost rich_3454.
In rich_3454, sed -i with a * regex reportedly corrupted rich/highlighter.py,
producing a 115366-byte patch. The agent noticed damage and still submitted.

S3 changes only S2's prompt: exact-string edits, revert damaged edits, inspect
small intended-source diffs. Preregistered: solved >=5/16 AND empty <=3 AND every
task patch <=20000 bytes (20 KB) AND bootstrap upper95 <=10.5 h; all metrics known
on a complete dev-16v run, existing operational controls still apply. Otherwise
freeze S1 as E4B entry and stop E4B iteration. No execution performed here.
