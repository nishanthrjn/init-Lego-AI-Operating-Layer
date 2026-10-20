# FORGEAI-GEMMA4-M3-BUDGET-VARIANT-B2-1

Status: authored, NOT RUN — AWAITING MAINTAINER EXECUTION.
Date: 2026-10-20. B2 is not qualified or submitted.

## Candidate and limits

B2 differs from the closed M2 package only in eval_config.yaml:

| Key | M2 | B2 | Static inspection finding |
| --- | ---: | ---: | --- |
| timeout_seconds | 60 | 90 | Configured value preserved; runtime remaining-time bound applies (documented). |
| max_tool_calls | 10 | 40 | Passed unchanged into EvaluationBudget. |
| max_time_minutes | 1 | 4 | Passed unchanged into EvaluationBudget. |
| max_turns | 50 | 100 | Passed unchanged into EvaluationBudget. |

Sources: supplied pinned `swegemma-0.2.11-py3-none-any.whl`,
`swegemma/config.py:build_submission_limits` and `EvalConfig.__post_init__`,
`swegemma/budget.py:EvaluationBudget/HarnessLimits`;
[HARNESS_README sections 6.1 and 7.1](../docs/HARNESS_README.md).
`build_submission_limits` governs submission structure and generation, not a
static ceiling for these four evaluation values. No static rejection or silent
normalization was found in the inspected configuration path.

`swegemma/tools/execution.py:34–47` and README 6.1 document
`min(timeout_seconds, max(5, int(remaining_time_seconds)))`.
Effective command timeouts can be shorter near the end of each task in both M2
and B2. This is a harness property, not a B2 difference. The maintainer explicitly
accepted it. **Hidden scorer environment overrides: UNKNOWN.**
README 7.1 names SWE_TIMEOUT_SECONDS, SWE_MAX_TOOL_CALLS, SWE_MAX_TIME_MINUTES,
SWE_MAX_TURNS / SWE_MAX_LOOP_ITERATIONS; actual hosted values are unverified.

The other three files are copied as raw bytes from baseline/: agent.yaml,
prompts/system.md, configs/sampling.yaml. Static controls require exact equality
and the exact four B2 keys/values; changed prompts, extra keys or budgets fail.
The model remains gemma-4-31b-it-qat-w4a16-ct. No M2 file or evidence is edited.

## Validation reuse and M2 preservation

Changing portable_m2.py would invalidate its old receipt. Therefore portable_b2.py
loads a private instance of that unchanged source and binds B2 configuration,
candidate path, receipt input paths and worker dispatch. It does not mutate the
ordinary imported M2 module. No compiler, installer, deviation classifier, ZIP
builder or evidence-reconciliation algorithm is copied.

The thin root B2 validator reuses the M2 gate's export/reconcile functions with
the B2 instance. It owns B2's scope and success labels. Receipts explicitly bind
candidate=b2 and the budgets as well as every transfer input's raw bytes. The
same scoped install, full wheel inventory, recorded deviation rule, compiler
imports, negative controls, deterministic ZIP and reconciliation checks apply.
Official compilation checks agent configuration; it is not execution of hidden
Stage 1 or proof of effective hosted budget values.

The original M2 validator, portable source, compiler notebook, tests, candidate
and evidence remain byte-identical. The old M2 receipt still reconciles against
those same input bytes. Its historical whole-repository scope phase is not a
validator for this new slice and will reject new B2 files / the additional LF
rule. Use the B2 validator, which also runs the existing M2 policy tests and
checks the entire original input manifest remains equal to committed M2 evidence.
Do not broaden or rerun the historical scope gate to qualify B2.

## Experiment record and interpretation

[submissions.json](../results/submissions.json) provides a field schema and
separate records. M2's first_submission Version 1 was submitted on 2026-10-20,
status SCORING, as reported by the maintainer. Exact UTC time, submission ID and
score were not supplied; retain null/PENDING rather than inventing them.
Update from observed evidence later; preserve the prior observation in notes.
B2 is NOT_SUBMITTED and its package/receipt hashes remain null.

M2 versus B2 is a budget-only ablation. All four budget keys change together;
it cannot identify which individual budget causes any score difference.
Model sampling, scheduler/image changes and leaderboard variability also limit
causal conclusions. Throughput and hidden-task concurrency are UNMEASURED.
The maintainer's approximate resolution of one public-leaderboard task is
1.7 percentage points; it is not independently verified as a fixed task count.
Small score changes should be treated as noise/inconclusive, not established
improvement. One pair of runs cannot estimate statistical significance.

The 12-hour cap is 720 minutes and includes setup, unlike the per-task agent
clock (overview Issue Scoring, README 7.1). B2's serial zero-overhead ceiling is
720/4=180 tasks. With an illustrative, UNMEASURED 120-minute aggregate overhead,
600/4=150. For N tasks serially, estimate W+N*(S+4), where startup W and per-task
setup S are unknown. Four tensor-parallel GPUs do not imply four concurrent tasks.
Do not promise full task coverage or a better score.

## Maintainer sequence

All commands below are for the maintainer, from the repository root. No commands
were executed by the author.

1. Local-only preparation in the existing locked environment:

   ```powershell
   uv run --locked --offline --no-sync python .\validate_forgeai_gemma4_b2_candidate_1.py --local-only
   if ($LASTEXITCODE -ne 0) { throw 'B2 local preparation failed' }
   ```

   Expected: existing M2 controls, B2 controls and submission selection tests pass,
   followed by B2_LOCAL_SCOPE_AND_STATIC_PASS, a new transfer directory and receipt
   SHA256. No installs, compiler, models or network. Preserve the M2 receipts.

2. After local success, separately approve a B2 compiler-only session. Create a
   fresh copy of the official starter for the observed Python 3.12.13 Linux image;
   set Accelerator None and Internet Off. Factory reset if previously used.
   Do not run starter installation, vLLM, model or evaluator cells.
   Use only the cells in `kaggle_compiler/b2_compiler_only.ipynb`. Attach the new
   receipt-bound bundle and official wheelhouse at the documented dataset path.
   Set BUNDLE to its actual mount and enter:

   `AUTHORIZE FORGEAI GEMMA4 B2 KAGGLE CPU SCOPED INSTALL AND COMPILER ONLY`

   The B2 wrapper delegates the same exact five-wheel install and 41-wheel
   inventory checks. No added dependency repair is authorized. Allowed install
   states are SCOPED_INSTALL_PASS or SCOPED_INSTALL_PASS_WITH_OFFICIAL_DEVIATIONS.
   Any new unhandled failure remains ENVIRONMENT_BLOCKED; preserve it and stop.

3. Expected portable success: PORTABLE_COMPILE_AND_PACKAGE_PASS only. Download
   `/kaggle/working/gemma4-b2-compiler/` and its sibling log. Keep files outside
   the repository until evidence is reviewed. Kaggle input auto-extraction of
   ZIP files does not matter for source bundles, but later submission input
   must use the `.zip.bin` convention.

4. Reconcile against the new B2 receipt FILE and downloaded results DIRECTORY:

   ```powershell
   $b2Receipt = Read-Host 'Absolute path to NEW B2 local-receipt.json FILE'
   $b2Results = Read-Host 'Absolute path to downloaded gemma4-b2-compiler DIRECTORY'
   uv run --locked --offline --no-sync python .\validate_forgeai_gemma4_b2_candidate_1.py --receipt $b2Receipt --reconcile $b2Results
   if ($LASTEXITCODE -ne 0) { throw 'B2 reconciliation failed' }
   ```

   Expected: B2_OFFICIAL_COMPILER_VALIDATED and B2_PACKAGE_VALIDATED.
   M2 and B2 receipts/results cannot be mixed.

5. Review/stage this slice, then run the separate consistency phase:

   ```powershell
   uv run --locked --offline --no-sync python .\validate_forgeai_gemma4_b2_candidate_1.py --pre-commit --receipt $b2Receipt --reconcile $b2Results
   if ($LASTEXITCODE -ne 0) { throw 'B2 pre-commit consistency failed' }
   ```

   Expected: B2_PRE_COMMIT_STAGED_CONSISTENCY_PASSED. It does not stage or commit.

6. Only after those gates and an understood first M2 scoring result, fill the B2
   entry of CANDIDATE_PINS in submission_only/first_submission.ipynb from the
   retained B2 manifest and receipt. Hash the raw manifest file; use its exact
   zip_sha256, zip_size and local_receipt_sha256. Set authorization to:

   `AUTHORIZE FORGEAI GEMMA4 SUBMISSION OF B2 PACKAGE <first eight receipt hex characters>`

   Set reconciled and m2_result_understood to true only with that evidence.
   These operator assertions do not query Kaggle or replace evidence review.
   B2 placeholders fail before file I/O. This submission notebook is not in B2's
   transfer receipt, so filling pins after reconciliation does not change B2's
   validated package. M2's pins/authorization/default helper behavior remain.
   Update the submission record without inventing a score.

7. Re-run submission controls after filling pins, and pre-commit consistency
   after staging those reviewed changes:

   ```powershell
   uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/submission_only -p "test_*.py"
   if ($LASTEXITCODE -ne 0) { throw 'Submission candidate controls failed' }
   ```

   Tests deliberately exercise a placeholder B2 regardless of subsequently filled
   production pins. Upload byte-identical manifest.json and submission.zip.bin
   privately, select CANDIDATE="b2", set explicit input paths and exact B2 approval.
   Keep Accelerator None / Internet Off. The notebook copies only to
   /kaggle/working/submission.zip and prints B2_PACKAGE_COPIED_UNCHANGED plus hash.

**B2 must not be submitted until both:** (a) M3/M2's result is known and is not an
unexplained error; (b) B2 has reconciled official compiler/package PASS. Scoring
or error state is not permission to retry. Actual Kaggle submission is separate
from compiler/copy approval and is never performed by these tools.

Suggested commit: `feat(gemma4): prepare isolated B2 budget ablation candidate`.
