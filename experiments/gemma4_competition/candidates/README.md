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

## FORGEAI-GEMMA4-VALIDATOR-DIAGNOSTICS-AND-B2-SCOPE-1

Status: authored; maintainer validation pending. No tests or validators run by
this change's author.

The historical B2 gate compares the whole tree against b319b8c. A clean tree
still failed after c7417a8 added unrelated screenshots/notebook files and edited
the receipt-bound M2 compiler notebook. Committing B2 itself was not the problem.
The old top-level exception handler hid that scope failure behind `ValueError`.

Use `validate_forgeai_gemma4_validator_diagnostics_1.py` for diagnostic
reconciliation of the qualified M2 and B2 receipts. This deliberately wraps both
original validators rather than editing their receipt-bound bytes. Direct calls
to the historical entry points keep their historical scope and diagnostics.
The wrapper emits [PHASE] labels and exact plain ValueError messages with a
nonzero exit code. Other exception types print their class only; no traceback,
file contents or environment values are printed.

The original B2 slice is exactly:
- parent: b319b8c76615a1705623fddbeb73d52b51605cdd;
- slice: c636bac7c3dd7ff23f41f104f26f7c3b77c44fae.

The wrapper requires this ancestry and exact historical file set, and refuses
later committed edits to B2 slice implementation files. Unrelated later commits
are not attributed to B2. Uncommitted changes are restricted to this diagnostic
entry point, its new focused test file and this append-only README extension.
The historical slice allowlist is not widened. This checks current candidate
bytes too; it does not qualify today's changed compiler notebook or other code.

The two accepted historical receipt SHA256s are pinned explicitly:
- M2: ca6a05b46844c86369c7aaef3d989b542c5f3c5f63fcc91c7fce5997742893d9;
- B2: d7195f13fc0f4da056e003317d72c6d46f5b5acb0521742515721684d01f383f.

All bundle inputs must still match their receipt's exact raw bytes and sizes.
Only after authentication is the preserved validator loaded for reconciliation;
its compiler, install-deviation, ZIP and evidence checks remain unchanged. No
models, installs, compiler runs, tests or notebook execution occur in this
reconciliation wrapper. Local tests remain a separate maintainer command. A new
receipt requires a separately reviewed pin; this tool cannot qualify a new build.
Do not copy today's modified source over a historical bundle or regenerate a
receipt to make a mismatch pass.

### Evidence storage policy

Keep all newly preserved transfer bundles and downloaded results outside the
repository, for example under C:\Work\Gemma4Localtest\b2-staging or a maintainer-selected
external evidence root. `--receipt` identifies the actual local-receipt.json FILE
inside its complete preserved bundle; `--reconcile` identifies the results
DIRECTORY containing manifest.json, compiler-output.json, install-evidence.json
and submission.zip. The wrapper rejects evidence arguments inside the repository.
Only reviewed manifest/receipt/hash records should be committed in future evidence
slices; do not commit entire bundles, wheel copies or downloaded result directories.
Existing historical committed evidence is grandfathered and remains untouched.
Records added in a separate committed evidence slice do not expand B2's scope.
An extra untracked file inside the repository remains an error with its named path.

### Maintainer commands

Working directory: repository root. Use the existing locked environment; no new
package installation or environment variables are needed. Keep the original
external receipt and results. First run the new offline controls:

```powershell
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/tests -p test_validator_diagnostics.py
if ($LASTEXITCODE -ne 0) { throw 'Validator diagnostic controls failed' }
```

Then reconcile B2 from the current checkout, with the same external files that
previously passed (use assignments, not path strings as Read-Host prompts):

```powershell
$b2Receipt = 'C:\Work\Gemma4Localtest\gemma-b2-transfer-parent-eouf5647\bundle\local-receipt.json'
$b2Results = 'C:\Work\Gemma4Localtest\gemma4-b2-compiler-d7195f13\gemma4-b2-compiler'
uv run --locked --offline --no-sync python -B .\validate_forgeai_gemma4_validator_diagnostics_1.py --candidate b2 --receipt $b2Receipt --reconcile $b2Results
if ($LASTEXITCODE -ne 0) { throw 'B2 diagnostic reconciliation failed' }
```

For the preserved M2 bundle/results, use the same command with `--candidate m2`
and its own receipt/results paths. Do not substitute the B2 receipt.
Expected: the historical candidate's compiler/package reconciliation labels,
then HISTORICAL_PACKAGE_RECONCILED; CURRENT_CHECKOUT_COMPILER_NOT_QUALIFIED.
A failure names the phase and exact contract message; nothing is resubmitted.
This is historical evidence reconciliation, not a fresh full-suite run, a new
pre-commit claim, model quality qualification or Kaggle submission authorization.

The diagnostic loader uses a temporary copy containing only authenticated receipt
inputs and the unchanged receipt. Unpinned package initializers or cached bytecode
from a saved bundle are not executed. This creates temporary local files only;
it does not modify the preserved inputs/results or execute compiler/model code.

## FORGEAI-GEMMA4-P1-PROCEDURE-PROMPT-1

Status: authored; VERIFICATION NOT RUN — AWAITING MAINTAINER EXECUTION.
The existing M2/B2 candidates, evidence, compiler notebooks and evaluator sources
are unchanged. B2 is SCORING according to the supplied maintainer observation;
no B2 score is invented. M2's observed score remains 0.05.

P1 is `candidates/p1/`: the same model (`gemma-4-31b-it-qat-w4a16-ct`), root agent,
six tools and sampling as M2, with a new independently authored
[prompt](p1/prompts/system.md) and evaluation values 180 / 28 / 6 / 80
(timeout seconds / counted tool calls / task minutes / turns). It differs from B2
in exactly prompts/system.md and eval_config.yaml. No graph-tool instruction or
ban appears in the prompt; graph tools are not declared, just as in M2. P2 is
separate future work. The four-file ZIP has no copied public prompt or code.

[PRIOR-ART.md](../PRIOR-ART.md) records authors, URLs, licences, harness citations,
source conflicts and UNKNOWNs. In particular, the public wheel implements
unsubmitted-patch fallback, but hidden scorer parity/hard-global-timeout fallback
is UNKNOWN. submit_patch captures the patch and the runner exits; all checks must
precede it. Unignored untracked files may enter the diff; protected test/config
sections are stripped. P1 conservatively prohibits all test/config edits and
uses /tmp for reproduction scripts.

The P1 prompt makes checkpoints at 90 seconds/6 calls, 240 seconds/18 calls,
and 300 seconds/24 calls (whichever threshold is reached first). The final minute
and four counted calls are a planned reserve, not a runtime guarantee. The
180-second command ceiling can consume half the task budget; short targeted
checks are essential. Dynamic remaining-time bounding applies as in M2/B2.
Hidden scorer environment overrides remain UNKNOWN.

Budget arithmetic: 116 x 6 = 696 minutes = 11.6 hours BEFORE setup, leaving
24 minutes of the 12-hour cap. At 120 tasks there is no remaining overhead margin.
The 116 count is a public estimate, not a verified hidden task count; throughput,
concurrency and setup cost remain UNMEASURED. This is a reduced-cap candidate,
not a certified time-safe configuration. Before ANY increase, a separately
approved local harness measurement must cover mean end-to-end task time, setup,
timeouts and tails. Mean alone cannot guarantee compliance with a hard cap.
Changing both prompt and budgets also prevents attributing P1-vs-B2 differences
solely to the prompt. One noisy public score is insufficient evidence of gain.

### Reused implementation and preservation

`portable_p1.py` configures a private instance of unchanged portable_m2.py. It
uses the same compiler, exact five-wheel scoped install, official-environment
deviation policy, negative compiler controls, child isolation, deterministic ZIP
and receipt reconciliation. The approved prompt has a fixed SHA256 in the P1
composition; its copied candidate bytes cannot silently redefine the expected
prompt. P1 receipts require candidate=p1, exact budgets and the prompt hash.

The new thin `validate_forgeai_gemma4_p1_procedure_prompt_1.py` owns P1's local
scope, phase labels and diagnostics, delegating export/reconcile algorithms.
Its parent is bffc014cadea36c87770986a3a06afe17d503edd. Only this P1 slice may
change relative to that parent; an unrelated later change must not be silently
admitted. The M2/B2 historical validators are not the P1 scope gate.

The transfer includes shared source/contract pins, original candidates and the
new P1 files. It replaces the transfer's old M2 compiler notebook with the P1
compiler notebook, excluding later download/export helpers. All transferred
files are raw-byte receipt-bound. Preserve LF candidate bytes and copy bundle
bytes unchanged across machines; do not recreate a receipt-bound bundle through
an autocrlf checkout. Keep bundles, results and downloaded public notebooks OUTSIDE
the repository. Filling submission pins later is independent of the transfer
receipt; the submission-only notebook is intentionally not a transfer input.

### Maintainer commands and gates

From the repository root, in the existing locked project environment with the
preserved official wheels already present (no install/download by this slice):

```powershell
uv run --locked --offline --no-sync python -B .\validate_forgeai_gemma4_p1_procedure_prompt_1.py --local-only
if ($LASTEXITCODE -ne 0) { throw 'P1 local preparation failed' }
```

Expected: existing 28 M2 controls, 10 new P1 controls and 13 submission controls
pass, followed by P1_LOCAL_SCOPE_AND_STATIC_PASS and a fresh external bundle and
receipt SHA256. Existing B2 historical scope tests are not rerun against today's
modified compiler notebooks. No tests have been executed by the coding agent.

After local success, separately approve compiler-only execution. Copy the
official starter for its observed Python 3.12.13 Linux environment, set Accelerator
None / Internet Off, and use ONLY `kaggle_compiler/p1_compiler_only.ipynb` cells.
Attach the new P1 bundle and the official wheelhouse dataset. Set BUNDLE to its
actual mount and use a fresh output/session. Do not run starter serving/evaluator
cells. The exact combined approval is:

`AUTHORIZE FORGEAI GEMMA4 P1 KAGGLE CPU SCOPED INSTALL AND COMPILER ONLY`

Only the existing five pinned wheels are installed in that future disposable
session. Additional dependency repair, inference and evaluation are not authorized.
A blocked environment stops; retain failure evidence. Download all files in
`/kaggle/working/gemma4-p1-compiler/` plus the sibling log OUTSIDE this repository.
Portable success alone does not qualify P1. Then:

```powershell
$p1Receipt = Read-Host 'Absolute path to NEW P1 local-receipt.json FILE'
$p1Results = Read-Host 'Absolute path to downloaded gemma4-p1-compiler DIRECTORY'
uv run --locked --offline --no-sync python -B .\validate_forgeai_gemma4_p1_procedure_prompt_1.py --receipt $p1Receipt --reconcile $p1Results
if ($LASTEXITCODE -ne 0) { throw 'P1 reconciliation failed' }
# After maintainer review and staging of this P1 slice:
uv run --locked --offline --no-sync python -B .\validate_forgeai_gemma4_p1_procedure_prompt_1.py --pre-commit --receipt $p1Receipt --reconcile $p1Results
if ($LASTEXITCODE -ne 0) { throw 'P1 pre-commit consistency failed' }
```

Expected: P1_OFFICIAL_COMPILER_VALIDATED, P1_PACKAGE_VALIDATED and
P1_PRE_COMMIT_STAGED_CONSISTENCY_PASSED. No model-quality or Kaggle acceptance claim.

Only after qualification, fill P1's null manifest/ZIP/size/receipt pins from its
own evidence in submission_only/first_submission.ipynb. Set reconciled=true and
use `AUTHORIZE FORGEAI GEMMA4 SUBMISSION OF P1 PACKAGE <receipt prefix>`.
M2/B2 pins, default CANDIDATE=m2 and their existing tests remain intact. P1 cannot
reuse either candidate's identity. Blank pins are deliberately non-executable.
After filling, rerun the P1 and submission tests and stage/recheck the reviewed
submission change. Use the byte-identical `.zip.bin` upload convention, private
inputs, Accelerator None / Internet Off. Actual model execution or submission
requires a separate maintainer decision; this task authorizes neither.

```powershell
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/tests -p test_p1_candidate.py
if ($LASTEXITCODE -ne 0) { throw 'P1 controls failed' }
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/submission_only -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'Submission controls failed' }
```

Proposed commit: `feat(gemma4): prepare P1 procedure prompt and bounded budget candidate`.
# FORGEAI-GEMMA4-P1B-P1C-CANDIDATES-1

Maintainer decision: **P1b is the base; P1c is not adopted.** Reported completed
dev-16v results under controls 05706c6a: P1 8/16 (dev-30 projection), P1b 8/16
(merged attempts), P1c 7/16. Full reported task groups and qualifications are in
`../results/dev-16v-comparison.json`. Five tasks always solved, five variable,
six never solved. This decision does not claim a significant improvement. P1
public result remains 0.10 for p1_selfcontained v1; submissions.json preserves
both that success and the preceding failed submission attempt.

Offline per-task table generator (any number of uniquely labelled runs; outputs
external; inherited attempt provenance retained):

```powershell
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'Run comparison controls failed' }
$p1Run = 'C:\Work\Gemma4Localtest\local-eval-p1-dev30\forgeai-local-eval-p1-dev30-attempt1'
$p1bRun = Read-Host 'Absolute path to COMPLETED merged P1b run folder'
$p1cRun = Read-Host 'Absolute path to COMPLETED P1c run folder'
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/compare_runs.py --run "P1=$p1Run" --run "P1b=$p1bRun" --run "P1c=$p1cRun" --controls experiments/gemma4_competition/local_eval/evidence/controls-05706c6a.json --controls-sha256 05706c6a948a67bfaf991ed0282d11308aac79865a614a68c6c582fe01f67033 --output 'C:\Work\Gemma4Localtest\dev-16v-comparison.md'
if ($LASTEXITCODE -ne 0) { throw 'Run comparison failed' }
```

The table shows the task union, allowing dev-30 and dev-16v to be compared without
treating excluded or unplanned tasks as failures. Controls and official inventory/
runtime identities must match. Missing/incomplete/environment-error outcomes are
not converted to failures. Variable-task outcomes are read from retained evidence,
never inferred from reported aggregate totals. No analysis was executed here.

Status: authored, NOT RUN. P1 baseline remains 8/16 VERIFIABLE dev-30, not a
leaderboard prediction. P1b changes only prompts/system.md from P1; P1c changes
only configs/sampling.yaml from P1b (thinking_budget 2048, max_output_tokens 8192).
Budget remains timeout 180s / 28 calls / 6 minutes / 80 turns. Model, six tools,
temperature, top_p and include_thoughts remain unchanged. Static raw-byte pins
are in ../local_eval/experimental-pins.json; do not regenerate on mismatch.

## Corrected submission-loop finding

Earlier P1 `prompts/system.md` §6 says the runner terminates after successful
submission; the earlier HARNESS_README §6.1 / submit_patch interpretation informed
that wording. **Contradicting retained runtime evidence:** P1 dev-30
`official/traces/trace_rich_4070.json`, `trace_rich_3454.json`, and
`trace_requests_7315.json` show respectively 32, 9 and 20 submissions. Maintainer
reports status ok for all rich_4070 calls, identical patch_size 1807. Our previous
inspection of rich_3454 trace steps 42–43 also showed consecutive ok responses.
Thus success did not terminate these episodes. Do not generalize this observation
to unseen scorer implementations. Historical P1 prompt/evidence is preserved;
P1b explicitly instructs the model to stop itself after ok.

Maintainer trace observations: write_file rejected /tmp/repro.py as outside the
workspace (rich_3471/rich_4075); use run_command for /tmp. Model-plus-overhead gaps
of 30–121s are not measured thinking time. P1c's smaller thinking/output limits
are an experimental hypothesis, not a proven latency fix. The forced edit deadline
may increase wrong patches. The prompt's "unedited workspace always scores zero"
is a requested procedure heuristic for screened tasks, not a universal harness
fact (historical EMPTY controls include passing tasks).

## Experimental builds and local comparisons only

From repository root, AFTER offline tests pass, maintainer may build into fresh
external directories using the existing deterministic zip_bytes/inspect_zip:

```powershell
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'P1b/P1c static controls failed' }
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/experimental.py p1b --output 'C:\Work\Gemma4Localtest\gemma-p1b-experiment'
if ($LASTEXITCODE -ne 0) { throw 'P1b experimental packaging failed' }
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/experimental.py p1c --output 'C:\Work\Gemma4Localtest\gemma-p1c-experiment'
if ($LASTEXITCODE -ne 0) { throw 'P1c experimental packaging failed' }
```

Keep the printed ZIP and manifest SHA256 independently. Upload each pair
submission.zip.bin + manifest.json as its own private Kaggle input. Upload updated
complete local_eval tooling (including experimental.py, experimental-pins.json,
dev-16v.json and evidence/). Use local_eval.ipynb, L4x4, Internet Off and the same
official data/wheelhouse/31B model inputs; no other installs. Run separately, not
concurrently, with matched environment and full task set:

- candidate: p1b or p1c; subset: dev-16v; subset_file: TOOLS / dev-16v.json.
- subset_sha256: 5a91f0513a3cdddea3eb7a2a3f5208ebdd40a5ab41821f29f6a31a4f07585056.
- package_mode: EXPERIMENTAL_UNQUALIFIED; experimental_authorized: true;
  package_reconciled: false; receipt_sha256: empty (no fabricated receipt).
- package/manifest: that candidate's mounted files; zip_sha256 and manifest_sha256:
  exact printed hashes. Both required; archive members are also matched to static pins.
- authorization: AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL p1b ON dev-16v (or p1c).
- gpu_authorized, internet_off_confirmed, official_environment_authorized: true
  only after maintainer approval; fresh output containing dev-16v and candidate name;
  wall_seconds: 14400 (4h total guard, not measured runtime).

Official directory validation remains; official evaluator performs agent compilation
and loading. Exceptions stop the run; returned unexpected load/runtime errors stop
with EXPERIMENTAL_LOAD_OR_RUNTIME_FAILURE after retaining the task result. Normal
budget exhaustion remains a task result. No retry/fallback. A failed load never
qualifies the package. GPU quota may be consumed before a load error is discovered.

EXPERIMENTAL_UNQUALIFIED manifests are rejected by the existing reconciled-package
verifier and never authorize submission. Submission pin registries are unchanged.
Real submissions still require the full official compile/reconcile/pin process.
Keep packages and outputs outside Git. Do not tune on confirm-20.

## Time-fit change

New analysis uses 10,000 seeded (20261022) empirical bootstrap totals: each samples
116 observed task durations with replacement, then adds measured startup once.
The one-sided 95th percentile must be <=11h; incomplete evidence cannot pass.
The sample p95 multiplied by 116 remains informational, not a strict worst case.
This is a predictive resampling bound conditional on empirical times, NOT a
distribution-free confidence guarantee. Small n, shared repositories, selection
of only verifiable tasks, unmeasured hidden-task mix/concurrency and startup
variability can invalidate coverage. Installation/setup outside recorded startup
may add overhead. Historical reports remain unchanged; new reports name the method.

Verification NOT RUN; STOP for maintainer test results before GPU execution.

