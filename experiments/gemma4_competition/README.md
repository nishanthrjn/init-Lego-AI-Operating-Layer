# Gemma 4 competition: independent continuation

## FORGEAI-GEMMA4-P3-REPLICATE-AND-P4-TIME-BUDGET-1

Status: **NOT RUN — Awaiting user execution**. Offline authoring only;
no package build, tests, GPU runs, leaderboard submissions or commits performed.
These instructions supersede the proposed P4/replicate sequence below for this slice.

P4 is P3 with only `evaluation.max_time_minutes: 6` changed to `7`.
`agent.yaml`, `configs/sampling.yaml`, and `prompts/system.md` are raw-byte copies.
The packager checks all four pinned file hashes, the exact changed-file set and
the exact one-line replacement. Other budgets remain **180 / 28 / 80**;
model, prompt, tools, sampling and 8,192 output cap are unchanged. P3's existing
experimental package and all qualification pins are preserved.

For 116 serial tasks, the P4 agent-cap worst case is `116*7/60 = 13.5333 h`
before startup, verification and other overhead. It is not worst-case time-safe.
Using P3's approximate 244-second mean and illustrative 370-second startup:
`(116*244 + 370)/3600 = 7.965 h`. Proportional task-time scaling gives
`(116*244*(7/6) + 370)/3600 = 9.275 h` for P4; scaling the rounded eight-hour
total instead gives 9.33 h. Both P4 figures are planning hypotheses, not measured
results or a bootstrap bound. Measured full task wall times plus startup govern
acceptance; the seven-minute cap does not cap verification/setup time.

### Manual preparation and validation

Working directory: `D:\Work\Projects\AI-Applications\ForgeAI-Gemma4`.
Prerequisites: existing locked uv environment with Python 3.12+, dependencies
already installed; no extra environment variables. The test discovery command
uses local fixtures; the optional external-metadata test skips if absent.
The build output must be a fresh directory outside any repository.

```powershell
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p "test_*.py"
if ($LASTEXITCODE -ne 0) { throw 'Local evaluation controls failed' }
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/experimental.py p4 --output 'D:\Downloads\gemma-p4-experiment'
if ($LASTEXITCODE -ne 0) { throw 'P4 experimental packaging failed' }
```

Expected: unittest `OK` (document any skips), then `submission.zip.bin` and
`manifest.json`, with printed ZIP and manifest SHA256, state
`EXPERIMENTAL_UNQUALIFIED`, candidate `p4`, and `submission_authorized: false`.
No P4 hashes are invented before the build. Do not rebuild P3 for the replicate.
Paste local results before proceeding to the separately authorized GPU milestone.

Maintainer feedback: P4 packaging succeeded, ZIP SHA256
`c0828be94981f3066dfad75ba71df554e029e8f50c9bc26cd1b07a2935c96cdb`,
5,100 bytes, manifest SHA256
`b9079ec2f4b077b75aab31f053cb0bb86a2fea21724e06870a3177a5025ee667`.
The supplied test run used CPython 3.14.5 and reported 98 tests with two errors:
historical-controls and derived-subset hash mismatches. Git inspection showed
LF index bytes checked out as CRLF for both fixtures. Explicit LF attributes now
protect them, source-pins.json and official-cells.json; their working copies were
restored to LF without changing historical pins or relaxing hash checks. Existing
fixture/hash tests remain unchanged and cover these failures. Rerun the test
command above; do not rebuild the successful package or advance to GPU execution
while validation is pending. Fix verification: **NOT RUN — Awaiting user execution**.

### Two prepared GPU configurations — execution not authorized here

Use `local_eval/local_eval.ipynb` in separate fresh official starter sessions,
**L4x4, Internet Off**, with the same official competition data, wheelhouse,
model version and frozen dev-16v selection as P3 attempt1. Attach the updated
entire local_eval tooling directory. Load the selected JSON as `CONFIG` in the
configuration cell in place of the example dictionary; keep the existing guards
and launch cell. Correct mount paths to attached inputs, never substitute bytes.

| Configuration | Package and output |
|---|---|
| [P3 attempt2](local_eval/p3-dev-16v-attempt2.config.json) | Reuse retained P3 experimental ZIP `19b4e772…` and experimental manifest `1a1cc504…`; output `/kaggle/working/forgeai-local-eval-p3-dev-16v-attempt2` |
| [P4 attempt1](local_eval/p4-dev-16v-attempt1.config.json) | Attach new P4 build; replace both hash placeholders with build output and both package mount paths; output `/kaggle/working/forgeai-local-eval-p4-dev-16v-attempt1` |

Both configs retain the 7,200-second total watchdog, model version 2,
`EXPERIMENTAL_UNQUALIFIED`, frozen subset hash
`5a91f0513a3cdddea3eb7a2a3f5208ebdd40a5ab41821f29f6a31a4f07585056`, and
empty resume fields. This is a fresh full replicate, not a continuation.
P3 package/manifest hashes are copied from retained attempt1 config; the qualified
manifest is a different file and must not replace the experimental manifest.

Templates deliberately have approval booleans false. Only after separate GPU
authorization, set `official_environment_authorized`, `gpu_authorized`,
`internet_off_confirmed`, and `experimental_authorized` true, and set authorization
to `AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL p3 ON dev-16v` or
`AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL p4 ON dev-16v`, respectively.
Keep `package_reconciled` and `confirmation_only` false. No environment variables
are required. Retain config, full outputs, failures and partial attempts externally.
Expected successful runs contain 16 distinct completed task results; no score
increase is promised. Watchdog stops/unknown outcomes cannot satisfy the gate.

### Replicate analysis and selection rule

After downloading the two runs, use the actual external folders in these commands.
The example attempt2/P4 locations below are proposed destinations, not observed files.

```powershell
$p3a = 'D:\Downloads\local_eval_p3\local_eval_p3_dev16v\forgeai-local-eval-p3-dev-16v-attempt1'
$p3b = 'D:\Downloads\forgeai-local-eval-p3-dev-16v-attempt2'
$p4 = 'D:\Downloads\forgeai-local-eval-p4-dev-16v-attempt1'
$controls = 'experiments/gemma4_competition/local_eval/evidence/controls-05706c6a.json'
$controlsHash = '05706c6a948a67bfaf991ed0282d11308aac79865a614a68c6c582fe01f67033'
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py summary $p3a --compare $p3b --same-config --controls $controls --controls-sha256 $controlsHash
if ($LASTEXITCODE -ne 0) { throw 'Replicate comparison failed' }
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/compare_runs.py --run "P3a=$p3a" --run "P3b=$p3b" --run "P4=$p4" --same-config P3a=P3b --controls $controls --controls-sha256 $controlsHash --output 'D:\Downloads\p3-p4-replicate-comparison.md'
if ($LASTEXITCODE -ne 0) { throw 'Comparison table failed' }
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py summary $p4 --compare $p3a --controls $controls --controls-sha256 $controlsHash
if ($LASTEXITCODE -ne 0) { throw 'P4 summary failed' }
```

Expected: same-config report lists all verifiable tasks, both outcomes, flip flags,
agreement rate and `flip_count`. Package/config/runtime mismatches, duplicate IDs,
unknown outcomes, incomplete or resumed runs fail rather than implying zero noise.
The measured noise floor **F** is all P3 attempt1-vs-attempt2 per-task flips,
including both directions, not the absolute difference in solved totals. It is an
empirical estimate from one pair, not a population bound or significance claim.

**P4 replaces P3 for submission selection only when** all runs are complete on
the same 16 VERIFIABLE tasks, **S4 - S3a > F**, and P4's measured
`time_fit.bootstrap_upper95_hours <= 11` with `time_fit.gate == "PASS"`.
Use the preselected P3 attempt1 baseline (reported 8/16); do not choose the weaker
P3 draw after seeing results. Equality with the flip count fails; equality at
11 hours passes. Missing evidence means INCONCLUSIVE: retain P3.
The existing deterministic 10,000-draw bootstrap samples 116 task wall times plus
fixed startup and uses its one-sided 95th percentile. Small n, shared repositories
and dev-set tuning limit generalization. Qualification, frozen held-out confirmation
and actual submission remain separate gates; an experimental win does not authorize
submission or replacement of P3 receipt pins.

For later identical-file leaderboard resubmissions, keep `candidate: "p3"` and
append a new run in [submissions.json](results/submissions.json) with
`replicate_of: {"notebook_name": "p3_selfcontained", "notebook_version": "1"}`.
Require identical ZIP SHA256 to that earlier record; preserve each draw's actual
notebook version, submission ID/time and score (null until observed). The pair
of notebook name/version identifies the earlier record even when submission ID
is unknown. This is the ledger's documented field schema, not a new executable
submission validator. No hypothetical submission records or scores are added.

Tests authored: P4 byte/scope controls including a re-pinned invalid budget;
replicate flips despite equal totals, full agreement, Markdown output and failure
boundaries. **Verification: NOT RUN — Awaiting user execution.** Paste results
before further debugging or implementation.

Maintainer review snapshot: **2026-10-26**, branch **br-ForgeAI-Gemma4**, HEAD
`6cf6ce87206ce31a13fcc95b7995183a09561ad8` before this documentary edit.
The initially open product branch was clean at the same commit; the checkout
was switched to the existing competition branch. No branch history was changed.
Product work is independent: no merges, shared Core/Ports changes or product
release gates for competition needs. Reusable improvements require a written
cherry-pick proposal with ownership, tests and risks; execution is separate.

## Current state and entry points

One root Gemma 4 31B LlmAgent, official tools, no LoRA/subagents/ForgeAI imports.
Qualified packages: M2, B2, P1 and P3. Public scores (maintainer-reported):
**0.05 / 0.12 / 0.10 / 0.15**. Preserve P1's failed dataset-based attempt as a
separate historical record. P3: receipt `02a7f680`, ZIP `19b4e772`, 5,100 bytes;
qualification pins are committed in `6cf6ce8`. External install evidence records
Python 3.12.13, five scoped wheels and four official environment deviations.

| Workflow | Current entry point | Interpretation |
|---|---|---|
| Evidence | [paper index](results/paper-evidence.json), [submissions](results/submissions.json), [six-run table](results/dev-16v-comparison.md) | Source hashes and evidence limits; derived analysis still pending where marked |
| Candidate design | [candidates](candidates/README.md) | Historical slices below current instructions; do not rerun old qualification automatically |
| Qualification | [compiler workflow](kaggle_compiler/README.md), `p3_compiler_only.ipynb`, root P3 validator | Local receipt → CPU compile → reconcile → staged consistency; fresh candidate needs its own pins |
| Submission | [submission-only](submission_only/README.md), `generate_self_contained.py` | Reconciled pins only; CPU/Internet Off, no datasets, rerun-safe; separate submission approval |
| Evaluation | [local evaluation](local_eval/README.md), `local_eval.ipynb` | Gold-free tooling, official GPU path, frozen controls; raw outputs external |

Local development scores P1/P1b/P1c/P2/P3/P3g are **8/8/7/8/8/7 of 16**.
Controls `05706c6a`: 24/50 verifiable, reproduction reported identical; dev-16v
is a tuning set, not a held-out claim. P3 has zero observed context crashes
and approximately eight-hour mean projection. P2 had three context crashes.
Graph tools were used in only 3/32 P2+P3g task-runs: this does not test their
potential benefit under reliable adoption. CPU localization file recall@10 is
L .31, T1 .32, T2 .35, fusion .44. The served 32,768 context with a 16,384 output
reservation leaves nominally 16,384 input tokens; P3 reserves 8,192. See pinned
`local_eval/official-cells.json`, cell 8, and the paper index. Do not claim
statistical improvement from public scores with reported +/-3-task variability.

## Command cheat sheet (maintainer only; not executed)

From repository root, use the locked environment. Start with documentary review;
do not rerun historical scope validators for this new documentation slice.

```powershell
git branch --show-current  # must be br-ForgeAI-Gemma4
git diff -- experiments/gemma4_competition/README.md experiments/gemma4_competition/results/submissions.json experiments/gemma4_competition/results/paper-evidence.json
Get-FileHash experiments/gemma4_competition/results/submissions.json -Algorithm SHA256
# Must equal the public_scores_and_noise claim's SHA256 in paper-evidence.json.

# Optional future analysis: existing results only, no model.
$p3Run = 'D:\Downloads\local_eval_p3\local_eval_p3_dev16v\forgeai-local-eval-p3-dev-16v-attempt1'
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py summary $p3Run --controls experiments/gemma4_competition/local_eval/evidence/controls-05706c6a.json --controls-sha256 05706c6a948a67bfaf991ed0282d11308aac79865a614a68c6c582fe01f67033
if ($LASTEXITCODE -ne 0) { throw 'P3 summary failed' }
```

For a new candidate, obtain approval for its isolated delta, static controls and
experimental package, evaluate on dev-16v, then confirm a frozen winner using
only VERIFIABLE confirm-20 tasks. Require the bootstrap 95% upper bound for
116 tasks plus startup to stay below 11 hours. Qualification then follows its
own local/CPU/reconcile path; never repoint P3 pins at another package.
Use `submission_only/generate_self_contained.py --candidate NAME --manifest FILE
--package FILE --output FRESH_EXTERNAL_IPYNB` only after reconciliation. Review
the printed hashes and authorization before any separately approved Kaggle run.

## External evidence inventory

Paths below were observed present by filesystem inspection, not revalidated.
They are required only for the corresponding reproduction workflow, not product
development. Preserve hashes when relocating; change path arguments, not evidence.

| Purpose | External path |
|---|---|
| P3 receipt | `D:\Downloads\p3-qualification\bundle-02a7f680\local-receipt.json` |
| P3 compiler outputs | `D:\Downloads\p3-qualification\kaggle-results\gemma4-p3-compiler` |
| P1 development | `D:\Downloads\local-eval-p1-dev30\forgeai-local-eval-p1-dev30-attempt1` |
| P1b merged view | `D:\Downloads\local_eval_p1_dev30\p1b\forgeai-local-eval-p1b-dev-16v-attempt2` |
| P1b ancestor/config | `D:\Downloads\local-eval-p1b-dev16v\forgeai-local-eval-p1b-dev-16v-attempt1`; sibling `local-eval-config.json` |
| P1c | `D:\Downloads\local_eval_p1_dev30\p1c\forgeai-local-eval-p1c-dev-16v-attempt1` |
| P2 | `D:\Downloads\local_eval_p2_dev16v\forgeai-local-eval-p2-dev-16v-attempt1` |
| P3 / P3g | `D:\Downloads\local_eval_p3\local_eval_p3_dev16v\forgeai-local-eval-p3-dev-16v-attempt1`; `local_eval_p3g_dev16v\forgeai-local-eval-p3g-dev-16v-attempt1` under the same parent |
| P1 smoke | `D:\Downloads\local-eval-p1-smoke5\forgeai-local-eval-p1-smoke5-attempt1` |
| B2 qualification | `D:\Downloads\gemma-b2-transfer-parent-eouf5647\bundle\local-receipt.json`; `D:\Downloads\gemma4-b2-compiler-d7195f13\gemma4-b2-compiler` |
| Infrastructure / selection metadata | `D:\Downloads\competition-infra`; `D:\Downloads\gemma4-dev-metadata\public_dev_task_metadata.jsonl` |
| Experimental packages | `D:\Downloads\gemma-p1b-experiment`, `gemma-p1c-experiment`, `gemma-p2-experiment`, `gemma-p3-experiment`, `gemma-p3g-experiment` under Downloads |
| Retained diagnostics | `D:\Downloads\p1-dev30-trace-review.json`; `D:\Downloads\p1b-resume-preparation` |

Historical example paths `D:\Downloads\forgeai-local-eval-p1-smoke5-attempt1`,
`dev-16v-comparison.md`, `gemma-location-review`, and `p3-six-run-review-1` are
absent. The first has the nested smoke path above; the others are proposed output
destinations, not missing mandatory inputs. `run-a`, `run-b`, `YOUR-*` are
placeholders. Temporary receipt paths are not durable; use preserved copies.
Raw traces, downloaded notebooks, binaries and full task data stay external.
Commit only reviewed safe metadata/hash records. Never place gold data in GPU
tooling inputs. The 41 preserved official wheels remain under `docs/archive`.

## Proposed remaining plan — no execution authorized

Deadlines checked 2026-10-26: paper **Nov 12**, entry/team merge **Nov 25**, final
submission **Dec 2**, all **23:59 UTC**. Official rules endpoints returned no
readable body; dates are corroborated by official [main timeline/prizes](https://www.kaggle.com/competitions/gemma-4-developer-agent/overview/prizes)
and [paper overview](https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/overview/description).
Recheck before submission. This plan does not authorize a team merge or Git merge.

Quota estimates are planning assumptions, not measured allocations: L4x4 charges
2x session hours per the official main page. P3 dev-16v estimate is
`(16*244 + 370)/3600 = 1.19 h`, about **2.4 quota-hours**. Setup/install/idle time
can increase this; reserve 1.5–2 h/session (3–4 quota-hours). Account balance and
scoring-job charging are UNKNOWN; queue time is not GPU runtime.

| Window | Proposed action and decision gate | L4x4 quota reservation |
|---|---|---|
| Oct 27–Nov 1 | Two exact-package P3 dev-16v replicates, distinct attempt IDs; retain errors/timings and paired outcomes. Optionally two identical public submissions only with approval and available daily slots. | 6–8 quota-hours for local runs; scorer cost unknown |
| Nov 2–6 | P4 feasibility: only max_time_minutes 6→7, preserve P3 prompt/model/tools/sampling and other limits. Build only after review. Smoke then dev-16v, with stop if bootstrap upper-bound projection exceeds 11 h or errors recur. | Smoke 1–2 plus dev 3–5 quota-hours |
| Nov 7–10 | Freeze best candidate; evaluate on eight VERIFIABLE confirm-20 tasks once, no tuning against outcomes. Freeze paper artifacts and limitations. | 2–3 quota-hours |
| By Nov 11 | Finalize reproducible paper/writeup, citations, noise and weak graph adoption as limitations; no novelty or improvement claim without supporting evidence. Maintainer submits before Nov 12 deadline. | CPU/editor only |
| Nov 13–20 | Optional E4B feasibility: first reconcile updated official model registry/serving pins; then smoke-5 and, only if viable, dev-16v. No LoRA or subagents. Separate package and compiler qualification. | Reserve 1–2 + 3–5 quota-hours; UNMEASURED, do not assume speedup |
| Nov 21–25 | Check entry/team eligibility; replicate finalist only if uncertainty affects selection, retain P3 fallback. | 3–5 quota-hours discretionary |
| Nov 26–Dec 1 | Freeze hashes, qualify finalists and prepare self-contained versions; allow scoring turnaround before Dec 2. Maintainer selects final two explicitly. | CPU preparation; scorer cost unknown |

Core local plan reserves **12–18 quota-hours**, optional E4B **4–7**, plus
**3–5** discretionary: total **19–30**, excluding scorer usage and failures.
Do not schedule against an assumed weekly quota; confirm account capacity first.
P4's seven-minute cap gives `116*7/60 = 13.53 h` before setup: it is NOT worst-case
time-safe. Only measured runtime distributions can justify it; proportional
scaling of P3's eight-hour mean to 9.33 h is a hypothesis, not acceptance.

The newer official [prize page](https://www.kaggle.com/competitions/gemma-4-developer-agent/overview/prizes)
confirms a $10,000 E2B/E4B bonus requiring an eligible package among the final two.
The [staff model announcement](https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/748287)
confirms `gemma-4-e4b-it-qat-w4a16-ct`; the older cached 31B-only overview is stale.
Public eligibility does not establish compatibility with our pinned wheel bytes.

Final-two criteria: qualified immutable packages; reliable scoring completion;
11-hour bootstrap gate; replicated local evidence and held-out confirmation;
public scores interpreted with noise, not highest single draw. Prefer complementary
task outcomes if evidenced. Keep P3 as fallback. Include E4B only if eligible,
time-safe and worth sacrificing a general-track finalist slot; the bonus is not
automatic. No product-branch dependency and no reusable-change proposal needed
for this documentary slice. **Verification NOT RUN; await maintainer review.**

## FORGEAI-GEMMA4-P5-SUBMISSION-QUALIFICATION-PREP-1

Prepared, **NOT RUN — Awaiting user execution**. P5 attempt2 is pending;
submission stays blocked. CPU qualification may be prepared independently of the
development decision. No compiler, packaging, install, notebook, test, model or
submission was executed during authoring. No commit was made.

The existing candidates/p5 files are reused without changes. The shared adapter
checks all four member hashes and the deterministic experimental ZIP identity:

| Member | SHA256 |
|---|---|
| agent.yaml | 83a97b8a3e9a8d71efa692423ace1d0187ba65ca84655c94679b03b3eab4c3c6 |
| eval_config.yaml | 2c8a983a1926aadfeca826bc90936ebc00329f6440e44a41369d01eed909d1a8 |
| configs/sampling.yaml | 571a934e89911734927533f1d36cbcc7b8d493592febe63b217e911cf7ed4926 |
| prompts/system.md | 020704784e5e0b95fb73095fea14fd7d8670cbe18e164f6d4a52cf1adcbaa7d9 |

ZIP: `6db4109a73cfea1c803c17e86f498406461141904dac58efe441f10cca1fe219`,
6501 bytes. The experimental manifest is not an official qualification manifest.
P5 uses the P3 adapter, validator orchestration and submission preparation, backed
by the existing M2 compiler/install/reconciliation implementation. No compiler or
package algorithm is duplicated. Historical P3 packages and receipts remain
historical evidence; this changed adapter requires a fresh P5 receipt.

### 1. Maintainer offline checks and fresh transfer bundle

Prerequisites: branch br-ForgeAI-Gemma4, existing locked uv environment and exact
previously recovered official wheel bytes. Do not rerun recovery or install
packages. No additional environment variables. Working directory:
`C:\Work\ForgeAI-Gemma4`. All output paths below must be fresh; increment the
qualification directory suffix if a previous attempt exists, preserving evidence.

```powershell
Set-Location 'C:\Work\ForgeAI-Gemma4'
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/tests -p 'test_p3_qualification.py'
if ($LASTEXITCODE -ne 0) { throw 'Shared P3 regression tests failed; paste output and stop' }
uv run --locked --offline --no-sync python -B .\validate_forgeai_gemma4_p5_submission_qualification_1.py --local-only --output 'C:\Work\Gemma4Localtest\p5-qualification-1\bundle'
if ($LASTEXITCODE -ne 0) { throw 'P5 local qualification failed; paste output and stop' }
```

The local-only validator also runs M2 controls, test_p5_qualification.py and all
submission_only/test_*.py controls, then rechecks scope and exports the bundle.
Expected final label: `P5_LOCAL_SCOPE_AND_STATIC_PASS; PORTABLE COMPILATION REQUIRED`.
Expected receipt: `C:\Work\Gemma4Localtest\p5-qualification-1\bundle\local-receipt.json`.
This is not submission qualification. Paste results before debugging or changes.
Missing wheels, changed candidate bytes, wrong branch, unrelated index/worktree
changes, failed tests or existing outputs must stop the sequence.

### 2. Maintainer Kaggle CPU compiler-only sequence

Attach the entire fresh bundle directory (preserve its internal paths) and the
official `metric/gemma-4-developer-agent-wheelhouse` dataset. Use the same official
Python 3.12 Linux environment as the P3 workflow, Accelerator None, Internet Off,
fresh session. Import `kaggle_compiler/p5_compiler_only.ipynb`. Adjust BUNDLE to
its actual mount ending in /bundle. OUTPUT and LOG default respectively to
`/kaggle/working/gemma4-p5-compiler` and `/kaggle/working/gemma4-p5-compiler.log`.

After reviewing the notebook, set AUTHORIZATION exactly:
`AUTHORIZE FORGEAI GEMMA4 P5 KAGGLE CPU SCOPED INSTALL AND COMPILER ONLY`.
Run only these code cells, in order:

1. `inputs-and-approval`: receipt verification and environment checks.
2. `five-wheel-install`: the existing scoped, pinned five-wheel installation.
3. `offline-compile`: isolated offline compilation and deterministic packaging.
4. Final download ZIP cell (`9647230f`): packages the chosen receipt's results
   with exclusive creation; never select the first unrelated receipt on a mount.

Do not run official starter serving/evaluation cells. On any failure, retain the
log and installation evidence and stop. A rerun requires a fresh/reset session;
no overwrite or remedial package installation is authorized by this sequence.

Download the compiler log and complete output directory: install-evidence.json,
compiler-output.json, manifest.json, submission.zip. Extract the download so the
result DIRECTORY is exactly
`C:\Work\Gemma4Localtest\p5-qualification-1\compiler-download\gemma4-p5-compiler`.
Expected package state is PORTABLE_COMPILE_AND_PACKAGE_PASS and the frozen P5 ZIP
hash/size above. Portable success alone does not permit submission.

### 3. Receipt-matched local reconciliation

```powershell
Set-Location 'C:\Work\ForgeAI-Gemma4'
$p5Receipt = 'C:\Work\Gemma4Localtest\p5-qualification-1\bundle\local-receipt.json'
$p5Results = 'C:\Work\Gemma4Localtest\p5-qualification-1\compiler-download\gemma4-p5-compiler'
uv run --locked --offline --no-sync python -B .\validate_forgeai_gemma4_p5_submission_qualification_1.py --receipt $p5Receipt --reconcile $p5Results
if ($LASTEXITCODE -ne 0) { throw 'P5 reconciliation failed; paste output and stop' }
```

Expected: `P5_OFFICIAL_COMPILER_VALIDATED; BYTE_IDENTITY_VERIFIED` and
`P5_PACKAGE_VALIDATED; NO MODEL QUALITY OR SUBMISSION AUTHORIZATION`.
CANDIDATE_PINS.p5 remains placeholder until the separate guarded preparation step.
Never copy the experimental manifest hash into these pins. Any source edit covered
by the receipt requires a fresh bundle and CPU compilation; do not patch evidence.

### 4. Wait for attempt2 and record the two-run decision

Do not mark a pass in advance. After maintainer review, dev-16v-comparison.json
must contain `p5_adoption_decision: {"status": "PASSED"}` and both p5_attempt1
and p5_attempt2 records. The latter must use the existing attempt1 field names:
`candidate`, `subset`, `attempt`, `state`, `verifiable`, `retained_path`, `resolved`,
`all_tool_attempted`, `all_tool_rejected`, `nonempty_patch_tasks`,
`bootstrap_upper95_hours_approx`, `run_command_heredoc_edits_observed`.

The guard independently requires two COMPLETED P5/dev-16v records of 16 tasks,
attempt numbers 1 and 2, distinct retained paths, mean solved >=7, each run's
all-tool rejection fraction <=0.05 with nonzero denominator, each patch count
>= the mean of P3's recorded 11 and 7 (9/16), each bootstrap upper95 <=11 h,
and observed source edits in both runs. Baselines come from
`tool_argument_rejection_evidence.patch_production_baseline` (tasks_per_run=16).
Null, missing, nonfinite, boolean or out-of-range metric values cannot pass.
A bare PASSED label cannot override failed metrics. Rounded timing values near
11 h need sufficient precision from the maintainer; do not round a failure down.
Per-task flips and source-edit counts remain part of the evidence review.

The evidence file is deliberately outside compiler receipt inputs: recording
attempt2 does not change the candidate or invalidate a prepared CPU receipt.
The guarded submission pins bind its SHA256, and the shared notebook generator
rechecks that decision and hash. Evidence changed after pinning requires renewed
preparation to a fresh external notebook path. No decision is changed by this tool.

### 5. Guarded pin materialization and external self-contained notebook

Only after steps 3 and 4 succeed:

```powershell
Set-Location 'C:\Work\ForgeAI-Gemma4'
$p5Receipt = 'C:\Work\Gemma4Localtest\p5-qualification-1\bundle\local-receipt.json'
$p5Results = 'C:\Work\Gemma4Localtest\p5-qualification-1\compiler-download\gemma4-p5-compiler'
$p5Notebook = 'C:\Work\Gemma4Localtest\p5-qualification-1\p5-self-contained.ipynb'
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/submission_only/qualify_p5.py --receipt $p5Receipt --results $p5Results --notebook $p5Notebook
if ($LASTEXITCODE -ne 0) { throw 'P5 preparation blocked or failed; paste output and stop' }
```

Currently expected: refusal because attempt2 and PASSED decision are absent,
before reconciliation or writes. After all prerequisites pass, the tool reconciles
again, materializes only P5's CANDIDATE_PINS in first_submission.ipynb, and creates
the external notebook exclusively. Expected final label:
`P5_SUBMISSION_PREPARATION_READY; PRE_COMMIT_CHECK_REQUIRED; NO_SUBMISSION_EXECUTED`.
No generated self-contained notebook belongs in the repository. Its payload is
exactly the reconciled ZIP; AUTHORIZATION remains empty pending operator action.

### 6. Maintainer review and staged consistency (no commit)

Review and stage only the qualification slice and any separately reviewed result
records needed for the decision. The following command stages the authored slice,
not unrelated files. No git commit command is part of this handoff.

```powershell
git add -- validate_forgeai_gemma4_p3_submission_qualification_1.py validate_forgeai_gemma4_p5_submission_qualification_1.py experiments/gemma4_competition/portable_p3.py experiments/gemma4_competition/portable_p5.py experiments/gemma4_competition/tests/test_p5_qualification.py experiments/gemma4_competition/kaggle_compiler/p5_compiler_only.ipynb experiments/gemma4_competition/submission_only/qualify_p3.py experiments/gemma4_competition/submission_only/qualify_p5.py experiments/gemma4_competition/submission_only/generate_self_contained.py experiments/gemma4_competition/submission_only/first_submission.ipynb experiments/gemma4_competition/submission_only/test_p5_submission.py experiments/gemma4_competition/README.md
if ($LASTEXITCODE -ne 0) { throw 'Staging failed; stop' }
# Stage separately reviewed decision/result records explicitly before the check.
uv run --locked --offline --no-sync python -B .\validate_forgeai_gemma4_p5_submission_qualification_1.py --pre-commit --receipt $p5Receipt --reconcile $p5Results
if ($LASTEXITCODE -ne 0) { throw 'P5 staged consistency failed; paste output and stop' }
```

Expected: `P5_PRE_COMMIT_STAGED_CONSISTENCY_PASSED`. Do not change receipt-bound
sources between CPU compilation and this check. A successful qualification does
not submit anything. Review the external self-contained notebook; any execution,
Save Version and Kaggle submission remain explicit maintainer actions. P3 stays
the fallback if the two-run decision fails or remains unknown.

### P5 heredoc-count correction and manual confirmation

QUOTED_EOF_SOURCE_EDIT_HEURISTIC_V1 is implemented in local_eval/tool_rejections.py.
It counts actual agent run_command tool-call objects containing literal <<'EOF',
then counts the subset whose prefix before the first << contains no /tmp and whose
body contains any literal read_text, write_text, replace(. The body starts after
the opener line and ends at standalone EOF. Each call counts once; repeated actual
calls count separately. Echoed command text in observations does not add calls.
This deliberately narrow syntax heuristic does not prove execution or successful
source mutation; read_bytes/write_bytes without replace( and other quoting styles
are outside it. Existing completion-marker counts remain a separate field.
Missing trace coverage yields null aggregate heredoc counts, not zero.

Maintainer-computed expectations: attempt1 67 heredoc calls / 17 source-edit
heredocs; attempt2 76 / 23. Attempt1's earlier 35 was a rough text-search count
that double-counted repeated trace text. Corrected records remain
MAINTAINER_COMPUTED / ANALYZER_CONFIRMATION_PENDING until confirmed by execution.
The analyzer emits per-task counts and trace hashes through the existing summary.

From C:\Work\ForgeAI-Gemma4 in the existing uv environment, no extra environment
variables, execute manually (none of these commands ran during authoring):

```powershell
Set-Location 'C:\Work\ForgeAI-Gemma4'
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p 'test_tool_rejections.py'
if ($LASTEXITCODE -ne 0) { throw 'Heredoc regression tests failed; paste output and stop' }
foreach ($p5Attempt in @(1, 2)) {
    $p5RunRoot = Read-Host "Actual attempt$p5Attempt run root containing run.json and official/traces"
    uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py summary $p5RunRoot --controls experiments/gemma4_competition/local_eval/evidence/controls-05706c6a.json --controls-sha256 05706c6a948a67bfaf991ed0282d11308aac79865a614a68c6c582fe01f67033
    if ($LASTEXITCODE -ne 0) { throw 'P5 summary failed; paste output and stop' }
}
```

Inspect descriptive_observations_not_control_qualified.tool_argument_rejections:
run_command_heredoc_calls must match 67 and 76; run_command_heredoc_edits_observed
must match 17 and 23, with heredoc_trace_coverage_complete true. Per-task metrics
are in per_task[].tool_argument_rejections. Do not tune the heuristic to force
agreement: paste any discrepancy and its provenance before qualify_p5.

The two new analysis paths were added explicitly to P5's qualification scope.
This changes the receipt-bound root validator. Receipt e13f9b40 and its reported
compiler/reconciliation passes remain historical evidence; they cannot qualify
this updated checkout. After count confirmation, repeat the documented local-only,
CPU compiler and reconciliation sequence with a fresh bundle/output suffix before
qualify_p5. Candidate bytes and the frozen 6501-byte ZIP remain unchanged. No gate
was weakened, no pins materialized, no submission executed and no commit made.

## P7a exploratory public measurement: protocol amendment

Recorded before any P7a public score, per explicit maintainer declaration.
P7a FAILED local adoption (11+7)/2=9.0<10.5 and remains NOT ADOPTED.
P5 stays frozen. Exactly ONE exploratory public-LB submission of the unchanged
P7a ZIP68f68585...0c34 (7359 B), experimental manifest2b982fc8...f7f7 is authorized
only after the CPU compilation, reconciliation and preparation steps below.
The record is `results/submissions.json#/p7a_exploratory_authorization`, purpose
EXPLORATORY_LB_MEASUREMENT; it is not a submission or a score record yet.

Preregistered interpretation: replace P5 as frozen31B entry only if the single
P7a public score>=0.17; otherwise keep P5. P5 mean0.14/spread0.02 and P7a local
11-vs7 variability motivate measurement. Task-count conversion is approximate;
this decision threshold is not a significance claim. Final selection rules stay
unchanged. No repeat/retry public submission is authorized by this amendment.

The strict local confirmation guard remains unchanged. A separate exploratory
guard verifies the exact amendment, package, unused one-submission allowance,
absence of a recorded P7a submission/score and preserved failed local decision.
Qualification pins say development_gate=FAILED, local_adoption=NOT_ADOPTED and
qualification_purpose=EXPLORATORY_LB_MEASUREMENT; they never fabricate a local pass.
The receipt now binds both submissions.json and dev-16v-comparison.json, the guard
and generator sources. These files must remain frozen through compilation,
reconciliation and preparation. Any edit requires a fresh bundle and compile.
The scope baseline is committed P8 slice0fe7dd32152a9e3fdcee6f5db6905aa6eefa0613.
Existing P7a receipts predate this amendment and cannot be reused.

Prerequisites: br-ForgeAI-Gemma4, existing locked offline environment with cached
packaging==26.3 and preserved official wheels. Do not rerun wheel recovery.
All following commands are for the maintainer; none were executed by the agent.
Run controls first and paste results before proceeding:

```powershell
Set-Location 'C:\Work\ForgeAI-Gemma4'
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/tests -p 'test_p7a_qualification.py'
if ($LASTEXITCODE -ne 0) { throw 'Qualification tests failed; stop' }
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/submission_only -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'Submission tests failed; stop' }
```

Expected OK, including exploratory rejection on consumed/revoked authority,
changed hashes, known scores and stale evidence. Validation is pending.

### Fresh local-only transfer bundle

The validator runs offline tests when invoked. The packaging overlay below is
the previously used cached packaging==26.3 prerequisite; --offline refuses a
cache miss rather than changing project dependencies. Do not rerun wheel recovery.
Use the preserved official compiler wheels; stop on any missing/mismatched pin.

```powershell
$p7aBundle = 'C:\Work\Gemma4Localtest\p7a-qualification-' + [guid]::NewGuid().ToString('N') + '\bundle'
uv run --locked --offline --no-sync --with 'packaging==26.3' python -B .\validate_forgeai_gemma4_p7a_submission_qualification_1.py --local-only --output $p7aBundle
if ($LASTEXITCODE -ne 0) { throw 'P7a local qualification failed; paste output and stop' }
$p7aReceipt = Join-Path $p7aBundle 'local-receipt.json'
$p7aReceiptSha = (Get-FileHash -LiteralPath $p7aReceipt -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "Bundle: $p7aBundle"
Write-Host "Receipt SHA256: $p7aReceiptSha"
```

Expected P7A_LOCAL_SCOPE_AND_STATIC_PASS; PORTABLE COMPILATION REQUIRED. Preserve
that exact bundle/receipt and full SHA. Do not edit receipt-bound files after
export; any such change requires a new bundle, CPU compile and reconciliation.

### Kaggle CPU compiler-only sequence

Use a fresh copy of the official starter for its Python3.12 Linux image, replace
its content with kaggle_compiler/p7a_compiler_only.ipynb; Accelerator None,
Internet Off. Attach the exact fresh bundle as a private input and official pinned
wheelhouse. Set BUNDLE to the actual mounted bundle path and AUTHORIZATION to:
AUTHORIZE FORGEAI GEMMA4 P7A KAGGLE CPU SCOPED INSTALL AND COMPILER ONLY.
Run ONLY notebook code cells in this order: inputs-and-approval,
five-wheel-install, offline-compile, then the final export cell9647230f.
Do not run starter installation, model serving, evaluation or submission cells.
Use a fresh session/output each attempt. Download the receipt-labelled export
ZIP and retain the complete gemma4-p7a-compiler directory: install-evidence.json,
compiler-output.json, manifest.json, submission.zip, plus gemma4-p7a-compiler.log.
Compare the export cell's full receipt hash to $p7aReceiptSha. Stop on mismatch
or failed evidence; no successful compilation is claimed here.

### Receipt-matched reconciliation and self-contained notebook

Extract downloaded results to a fresh external root (use the compiler directory,
not its parent). Keep the original receipt, not a different bundle's receipt:

```powershell
$p7aDownload = Join-Path 'C:\Users\gayat\Downloads' ('gemma4-p7a-compiler-' + $p7aReceiptSha.Substring(0,8) + '.zip')
$p7aExtract = 'C:\Work\Gemma4Localtest\p7a-compiler-' + [guid]::NewGuid().ToString('N')
Expand-Archive -LiteralPath $p7aDownload -DestinationPath $p7aExtract -ErrorAction Stop
$p7aResults = Join-Path $p7aExtract 'gemma4-p7a-compiler'
uv run --locked --offline --no-sync --with 'packaging==26.3' python -B .\validate_forgeai_gemma4_p7a_submission_qualification_1.py --receipt $p7aReceipt --reconcile $p7aResults
if ($LASTEXITCODE -ne 0) { throw 'P7a reconciliation failed; stop' }
$p7aNotebook = 'C:\Work\Gemma4Localtest\p7a_exploratory_' + [guid]::NewGuid().ToString('N') + '.ipynb'
uv run --locked --offline --no-sync --with 'packaging==26.3' python -B experiments/gemma4_competition/submission_only/qualify_p7a.py --receipt $p7aReceipt --results $p7aResults --notebook $p7aNotebook
if ($LASTEXITCODE -ne 0) { throw 'P7a submission preparation failed; stop' }
```

Expected P7A_OFFICIAL_COMPILER_VALIDATED; BYTE_IDENTITY_VERIFIED;
P7A_PACKAGE_VALIDATED, then P7A_SUBMISSION_PREPARATION_READY.
qualify_p7a reuses qualify_p3 and generate_self_contained: it checks eligibility,
reconciles, updates ONLY the P7a pin entry and writes a fresh external notebook
embedding the reconciled bytes. Existing notebook destinations refuse overwrite.
The resulting CPU-only notebook needs no datasets and has empty AUTHORIZATION.
No submission action is executed or authorized automatically.

Review and stage only this qualification slice and its reviewed result updates
before the pre-commit check. Do not commit as part of these instructions:

```powershell
$p7aFiles = @(
 'validate_forgeai_gemma4_p7a_submission_qualification_1.py',
 'experiments/gemma4_competition/portable_p7a.py',
 'experiments/gemma4_competition/tests/test_p7a_qualification.py',
 'experiments/gemma4_competition/kaggle_compiler/p7a_compiler_only.ipynb',
 'experiments/gemma4_competition/submission_only/qualify_p7a.py',
 'experiments/gemma4_competition/submission_only/test_p7a_submission.py',
 'experiments/gemma4_competition/submission_only/generate_self_contained.py',
 'experiments/gemma4_competition/submission_only/first_submission.ipynb',
 'experiments/gemma4_competition/README.md',
 'experiments/gemma4_competition/results/dev-16v-comparison.json',
 'experiments/gemma4_competition/results/dev-16v-comparison.md',
 'experiments/gemma4_competition/results/paper-evidence.json',
 'experiments/gemma4_competition/results/submissions.json'
)
git add -- @p7aFiles
if ($LASTEXITCODE -ne 0) { throw 'Staging failed; stop' }
uv run --locked --offline --no-sync --with 'packaging==26.3' python -B .\validate_forgeai_gemma4_p7a_submission_qualification_1.py --pre-commit --receipt $p7aReceipt --reconcile $p7aResults
if ($LASTEXITCODE -ne 0) { throw 'P7a pre-commit check failed; stop' }
```

Expected P7A_PRE_COMMIT_STAGED_CONSISTENCY_PASSED. Freeze receipt-bound and scope
files through submission; later edits belong to a separate slice. Compilation
and local qualification establish packaging/identity, not hidden quality or the
public>=0.20 objective. The maintainer has authorized exactly one exploratory measurement after these checks; no submission action is performed by these scripts.

After the pre-commit PASS, import the generated external notebook on Kaggle:
CPU/Accelerator None, Internet Off, no datasets. Set its final-cell AUTHORIZATION
to the exact phrase printed in its pins; Save & Run All. Expected CREATED (or
ALREADY_PRESENT_IDENTICAL for an identical existing output), ZIP68f68585...0c34,
7359 B. Submit that saved version exactly once as the exploratory measurement.
Do not mark P7a adopted before the score. After submitting, record the actual
scriptVersionId/notebook version/receipt/time, set submissions_used=1 and
execution_status=SCORING, and append the actual run with purpose
EXPLORATORY_LB_MEASUREMENT. This consumes the authorization and blocks further
local preparation. On result, apply >=0.17; otherwise retain P5. Changes to these
receipt-bound records after submission are expected and invalidate reuse.
The offline notebook cannot enforce an account-wide Kaggle submission count;
the maintainer must enforce the single-submission limit. No automatic submission,
commit, test, install or compilation was executed for this amendment.


## Joint S1 + P10 qualification — one committed baseline

This sequence supersedes the earlier standalone S1 baseline and write-to-repository
handoff. P10's final repo timing upper95 is9.462469815737775 h (PASS).
The explicit amendment changes only eligibility run identity to attempt2;
maintainer10.40 h remains cross-check only. Original protocol text is preserved.
P10 attempt1 is deferred until after BOTH submissions. S1 uses its recorded
operational gate (including its explicitly attributed maintainer bootstrap).

Both validators use FORGEAI_GEMMA4_QUALIFICATION_BASELINE, set ONCE to the commit
containing this entire reviewed change. A future commit hash cannot be embedded
in its own source. The shared guard requires exact HEAD equality, clean index
and working tree, no untracked files, and receipt baseline/git_head equality.
Reviewed allowlist: qualification_pair.py:SCOPE. Never substitute an arbitrary
old commit or change the environment variable between candidates.

S1 ZIP6f38e73cbd441b9c55a5c04e25d2350fdf1deb3fccbd8b1631fcbee7af4ca36a,
P10 ZIP89a84bf709b52858b3a3ce39f33d713501dec1fe00e0fb04164f271158f333d6;
both6501 B. S1 E4B model is preserved. P10 remains NOT ADOPTED pending one
exploratory public measurement; adopt only at public>=0.17, otherwise retain P5.

Prerequisites: branch br-ForgeAI-Gemma4, existing locked offline environment,
cached packaging26.3 and preserved official pinned wheels. No package recovery
or root dependency edits. All paths below are external except reviewed source.
Use the same PowerShell session, or restore the EXACT saved baseline/path values.
No commands below have been executed by the agent.

1. Run tests; stop and paste results before proceeding.

~~~powershell
Set-Location 'C:\Work\ForgeAI-Gemma4'
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'local_eval tests failed; stop' }
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/tests -p 'test_s1_qualification.py'
if ($LASTEXITCODE -ne 0) { throw 'S1 qualification tests failed; stop' }
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/tests -p 'test_p10_qualification.py'
if ($LASTEXITCODE -ne 0) { throw 'P10 qualification tests failed; stop' }
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/tests -p 'test_qualification_pair.py'
if ($LASTEXITCODE -ne 0) { throw 'Common baseline tests failed; stop' }
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/submission_only -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'Submission tests failed; stop' }
~~~

Expected all suites OK; test fixtures do not require a real baseline commit.
Tests cover guards, package identity, six-vs-eight-minute receipt refusal,
metric thresholds, consumed authorizations and both external qualifications
without repository writes. Verification: NOT RUN — Awaiting user execution.

2. After tests pass, review and commit exactly this slice. The commit includes
the final record and both pipelines. Freeze repository files from this point
through both submissions; even a new commit with identical files is refused.

~~~powershell
$pairFiles = @(
 'validate_forgeai_gemma4_s1_submission_qualification_1.py',
 'validate_forgeai_gemma4_p10_submission_qualification_1.py',
 'experiments/gemma4_competition/qualification_pair.py',
 'experiments/gemma4_competition/portable_p3.py',
 'experiments/gemma4_competition/portable_s1.py',
 'experiments/gemma4_competition/portable_p10.py',
 'experiments/gemma4_competition/kaggle_compiler/p10_compiler_only.ipynb',
 'experiments/gemma4_competition/tests/test_p10_qualification.py',
 'experiments/gemma4_competition/tests/test_qualification_pair.py',
 'experiments/gemma4_competition/submission_only/qualify_p3.py',
 'experiments/gemma4_competition/submission_only/qualify_p10.py',
 'experiments/gemma4_competition/submission_only/generate_self_contained.py',
 'experiments/gemma4_competition/submission_only/test_p10_submission.py',
 'experiments/gemma4_competition/submission_only/test_joint_qualification.py',
 'experiments/gemma4_competition/results/submissions.json',
 'experiments/gemma4_competition/results/dev-16v-comparison.json',
 'experiments/gemma4_competition/results/dev-16v-comparison.md',
 'experiments/gemma4_competition/results/paper-evidence.json',
 'experiments/gemma4_competition/README.md'
)
git add -- @pairFiles
if ($LASTEXITCODE -ne 0) { throw 'Staging failed; stop' }
git diff --cached --stat
git diff --cached -- @pairFiles
# Review the staged content before issuing the following commit.
git commit -m 'Record P10 repo timing pass and prepare joint S1 P10 qualification'
if ($LASTEXITCODE -ne 0) { throw 'Commit failed; stop' }
$env:FORGEAI_GEMMA4_QUALIFICATION_BASELINE = (git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot capture common commit; stop' }
Write-Host "Common baseline: $env:FORGEAI_GEMMA4_QUALIFICATION_BASELINE"
~~~

Expected one commit containing this record and preparation. Do not recommit
qualification outputs; the workflow below writes none into the repository.

3. Create S1 bundle, then P10 bundle. Preserve the external path map.

~~~powershell
$pairRoot = 'C:\Work\Gemma4Localtest\s1-p10-qualification-' + [guid]::NewGuid().ToString('N')
New-Item -ItemType Directory -Path $pairRoot -ErrorAction Stop | Out-Null
$pair = [ordered]@{}
foreach ($candidate in @('s1', 'p10')) {
    $entry = [ordered]@{
        Bundle = Join-Path $pairRoot "$candidate-bundle"
        Receipt = Join-Path $pairRoot "$candidate-bundle\local-receipt.json"
        Extract = Join-Path $pairRoot "$candidate-compiler-download"
        Pins = Join-Path $pairRoot "$candidate-qualified-pins.json"
        Notebook = Join-Path $pairRoot "$candidate-selfcontained.ipynb"
    }
    $validator = ".\validate_forgeai_gemma4_${candidate}_submission_qualification_1.py"
    uv run --locked --offline --no-sync --with 'packaging==26.3' python -B $validator --local-only --output $entry.Bundle
    if ($LASTEXITCODE -ne 0) { throw "$candidate local-only failed; stop" }
    $entry['ReceiptSha256'] = (Get-FileHash -LiteralPath $entry.Receipt -Algorithm SHA256).Hash.ToLowerInvariant()
    $pair[$candidate] = $entry
}
$sessionFile = Join-Path $pairRoot 'session.json'
@{baseline=$env:FORGEAI_GEMMA4_QUALIFICATION_BASELINE; candidates=$pair} |
    ConvertTo-Json -Depth 8 | Out-File -LiteralPath $sessionFile -Encoding utf8
Write-Host "Preserve session: $sessionFile"
$pair | ConvertTo-Json -Depth 8
~~~

Expected S1_LOCAL_SCOPE_AND_STATIC_PASS and P10_LOCAL_SCOPE_AND_STATIC_PASS;
both PORTABLE COMPILATION REQUIRED. Validators run offline controls but no
model/GPU workload. Both receipts have the same baseline/git_head and their
own candidate-specific receipt hash. Any dirty tree, missing wheel, changed
candidate bytes or failed operational guard stops before bundle creation.

4. Compile each on Kaggle in a separate fresh CPU session. Accelerator None,
Internet Off, official Python3.12 Linux image, pinned official wheelhouse at
/kaggle/input/datasets/metric/gemma-4-developer-agent-wheelhouse.
Use kaggle_compiler/s1_compiler_only.ipynb and p10_compiler_only.ipynb respectively.
Attach the corresponding bundle; set BUNDLE to its mounted folder (the folder
containing local-receipt.json). Do not attach the other candidate as the bundle.
Set AUTHORIZATION to the candidate's exact phrase:
- AUTHORIZE FORGEAI GEMMA4 S1 KAGGLE CPU SCOPED INSTALL AND COMPILER ONLY
- AUTHORIZE FORGEAI GEMMA4 P10 KAGGLE CPU SCOPED INSTALL AND COMPILER ONLY

Execute code cells in order: inputs-and-approval, five-wheel-install,
offline-compile, 9647230f (export). Expected PORTABLE_COMPILE_AND_PACKAGE_PASS
with the matching6501-byte ZIP and local receipt hash. No starter model,
evaluation or submission cells. Download both gemma4-<candidate>-compiler-
<receipt-first8>.zip archives to Downloads, including log and complete result
directory (install-evidence.json, compiler-output.json, manifest.json,
submission.zip). A failed installation/compiler is a stop, not qualification.

5. Reconcile BOTH before qualifying either.

~~~powershell
foreach ($candidate in @('s1', 'p10')) {
    $entry = $pair[$candidate]
    $download = Join-Path 'C:\Users\gayat\Downloads' ("gemma4-$candidate-compiler-" + $entry.ReceiptSha256.Substring(0,8) + '.zip')
    Expand-Archive -LiteralPath $download -DestinationPath $entry.Extract -ErrorAction Stop
    $entry['Results'] = Join-Path $entry.Extract "gemma4-$candidate-compiler"
    $validator = ".\validate_forgeai_gemma4_${candidate}_submission_qualification_1.py"
    uv run --locked --offline --no-sync --with 'packaging==26.3' python -B $validator --receipt $entry.Receipt --reconcile $entry.Results
    if ($LASTEXITCODE -ne 0) { throw "$candidate reconcile failed; stop" }
}
~~~

Expected each candidate's OFFICIAL_COMPILER_VALIDATED, BYTE_IDENTITY_VERIFIED,
PACKAGE_VALIDATED messages. Receipt substitution, missing evidence, different
ZIP or changed source stops. Reconciliation writes no repository files.

6. Qualify BOTH to external pins only; do not use legacy --notebook.

~~~powershell
foreach ($candidate in @('s1', 'p10')) {
    $entry = $pair[$candidate]
    $qualifier = "experiments/gemma4_competition/submission_only/qualify_$candidate.py"
    uv run --locked --offline --no-sync --with 'packaging==26.3' python -B $qualifier --receipt $entry.Receipt --results $entry.Results --pins-output $entry.Pins
    if ($LASTEXITCODE -ne 0) { throw "$candidate qualification failed; stop" }
}
~~~

Expected S1_EXTERNAL_PINS_READY then P10_EXTERNAL_PINS_READY;
NO_REPOSITORY_WRITES; NO_SUBMISSION_EXECUTED. The shared implementation validates
the future notebook in memory but writes only each external pins JSON, no notebook
or repository CANDIDATE_PINS. Legacy qualify_s1 --notebook would write
first_submission.ipynb and is NOT part of this joint flow. P10 requires pins mode.

7. Run BOTH pre-commit checks against the same already-committed clean baseline.

~~~powershell
foreach ($candidate in @('s1', 'p10')) {
    $entry = $pair[$candidate]
    $validator = ".\validate_forgeai_gemma4_${candidate}_submission_qualification_1.py"
    uv run --locked --offline --no-sync --with 'packaging==26.3' python -B $validator --pre-commit --receipt $entry.Receipt --reconcile $entry.Results
    if ($LASTEXITCODE -ne 0) { throw "$candidate pre-commit check failed; stop" }
}
~~~

Expected S1_PRE_COMMIT_STAGED_CONSISTENCY_PASSED then
P10_PRE_COMMIT_STAGED_CONSISTENCY_PASSED. The historical flag name is retained:
there are no staged output changes to commit; index/worktree both equal baseline.

8. Generate BOTH external self-contained notebooks from the qualified pins.

~~~powershell
foreach ($candidate in @('s1', 'p10')) {
    $entry = $pair[$candidate]
    uv run --locked --offline --no-sync python -B experiments/gemma4_competition/submission_only/generate_self_contained.py --candidate $candidate --pins-file $entry.Pins --manifest (Join-Path $entry.Results 'manifest.json') --package (Join-Path $entry.Results 'submission.zip') --output $entry.Notebook
    if ($LASTEXITCODE -ne 0) { throw "$candidate notebook generation failed; stop" }
    Write-Host "$candidate notebook: $($entry.Notebook)"
}
~~~

Expected each JSON output identifies candidate, external notebook, receipt/ZIP
pins and correct purpose/model. Generation checks the current evidence and
common commit; wrong-candidate pins or changed evidence are rejected.
On Kaggle use separate CPU/Internet Off sessions with no datasets, enter each
notebook's exact generated AUTHORIZATION, then Save & Run All. Expected CREATED,
with the same evaluated6501-byte ZIP. Actual submissions remain manual.
P10 allowance is one measurement, adopted only at public>=0.17; S1 purpose is
E4B_BONUS_ENTRY. Preserve both complete evidence sets externally.
No repo edits/commits between bundles, compilation, qualification, generation
or submissions. Record both submissions and deferred P10 attempt1 together
in a later slice after both submissions; that new commit intentionally ends
this baseline's qualification lifecycle.
