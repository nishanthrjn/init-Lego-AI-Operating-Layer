# FORGEAI-GEMMA4-M3-LOCAL-EVAL-HARNESS-1

## FORGEAI-GEMMA4-LOCAL-EVAL-FIDELITY-1

Status: authored, NOT RUN. Historical CPU controls are preserved byte-for-byte in
`evidence/controls-05706c6a.json`, SHA256
`05706c6a948a67bfaf991ed0282d11308aac79865a614a68c6c582fe01f67033`.
No Git commit was performed. These classes describe the observed subprocess
environment, not intrinsic task quality or organizer verification parity.

| Subset | VERIFIABLE | ENV_BROKEN | UNSOUND |
|---|---:|---:|---:|
| dev-30 | 16 | 2 | 12 |
| confirm-20 | 8 | 5 | 7 |

Applied to the previously retained P1 smoke observations, only fastapi_14492 is
VERIFIABLE: 1/1, repo-macro 1.0 over FastAPI alone. Exclusions: three UNSOUND
(requests_6644, rich_3130, httpx_3672) and one ENV_BROKEN (fastapi_12942).
The requests pass is excluded. This is a manual evidence join, not a newly run
analysis or new model-quality claim. Confirmation controls must not guide tuning.

### Static fidelity findings

- HARNESS_README §§4.1–4.2, 8.2 describes setup and separate verification;
  starter cell 10 selects subprocess, not Docker.
- Pinned swegemma 0.2.11 `harness/verification.py:384–424` invokes editable setup,
  test-dependency setup (fast-path default), and workspace test configuration.
  Our controls invoke that same verifier. `container_setup.py:506–530` explicitly
  skips both install functions for SubprocessManager; `531–556` invokes setup.py
  only after that return. This is an official backend difference, not a locally
  omitted verifier call.
- `sandbox/subprocess.py:389–399, 418–498` exposes host site-packages and sets
  PYTHONPATH to the workspace root. `adk_eval_core/sandbox/subprocess_sandbox.py`
  provides subprocess command execution; the swegemma manager chooses these paths.
- Exported `sandbox/setup.py:290–320` adds workspace and child directories to
  workspace_paths.pth; `352–361` calls editable installation before fast-path.
  Its SHA256 remains in dependency-source-pins.json. Blindly invoking that script
  would add an install and would not match the official subprocess path.

Thus src-layout imports from installed copies are a supported hypothesis, NOT
an observed origin. No import-path override or installation is added. Exact Docker
parity cannot be established under the current no-install/no-Docker constraints.
The diagnostic records actual sandbox module.__file__ before teardown.

Requests ~100s durations alone do not prove network access/timeouts. Whether the
particular failing tests require network is UNKNOWN without their diagnostics;
no reference tests were read to reconstruct failures. Rich/FastAPI gold failure
causes likewise remain UNKNOWN. Organizer gold-pass curation was supplied by the
maintainer; these local failures do not invalidate that claim or condemn tasks.

### Future CPU diagnostics and retained-patch re-verification

Use the existing CPU notebook settings/inputs and authorization gates below.
Attach historical controls as metadata. Do not run this during development.
Create an external JSON configuration using the same CPU controls fields
(`authorization`, CPU/Internet confirmations, official_environment_authorized,
wheelhouse, data), plus:

```json
{
  "operation": "DIAGNOSTIC",
  "fidelity_authorization": "AUTHORIZE FORGEAI GEMMA4 CPU FIDELITY DIAGNOSTIC",
  "controls": "/kaggle/input/YOUR-CONTROLS/controls.json",
  "fidelity_output": "/kaggle/working/fidelity-diagnostic"
}
```

Merge these keys with the existing config, not a standalone replacement. In the
CPU notebook worker launch, replace `controls.py` with `fidelity.py` and pass this
config path. Official cell 2 runs once; no cell 8, candidate, model, or GPU.
Only historical UNSOUND/ENV_BROKEN tasks run GOLD. Each receives the existing
900s watchdog; the sequence has an 11h verification guard. Fresh output required.

For retained agent patches use operation REVERIFY and authorization
`AUTHORIZE FORGEAI GEMMA4 CPU FIDELITY REVERIFY`. Attach the previous run privately;
add `previous_run` (its mounted root) and `patches`, an explicit task-ID mapping:

```json
{"patches": {"fastapi_14492": {"path": "relative/path/to/retained-agent.patch", "sha256": "EXACT_RAW_PATCH_SHA256"}}}
```

Choose actual retained patch paths; no guessed filenames, gold fallback, model
invocation or changed historical records. Patch bytes and containment are checked
before installation. Re-verification uses the current unchanged official verifier;
it does NOT claim the fidelity problem is fixed. New per-task results are separate.

Diagnostics retain module origin and a conservative projection of the last 60
gold-output lines: error types only, with arbitrary text/source redacted. Reference
and test patch lines are explicitly suppressed. This sacrifices detailed assertion
messages to avoid retaining gold; no raw output is written. Origin probing is an
additional observation before teardown and may affect diagnostic timings.
No diagnostic files may be committed. Preserve provenance/environment/results
externally; do not download temporary sandbox contents.

Manual offline checks (repository root, existing uv environment):

```powershell
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'Local evaluation fidelity controls failed' }
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py summary 'D:\Downloads\local-eval-p1-smoke5\forgeai-local-eval-p1-smoke5-attempt1' --controls experiments/gemma4_competition/local_eval/evidence/controls-05706c6a.json --controls-sha256 05706c6a948a67bfaf991ed0282d11308aac79865a614a68c6c582fe01f67033
if ($LASTEXITCODE -ne 0) { throw 'Historical smoke analysis failed' }
```

Expected: tests pass; one eligible resolved smoke task, three UNSOUND and one
ENV_BROKEN excluded. STOP for maintainer results before any Kaggle execution.

## FORGEAI-GEMMA4-LOCAL-EVAL-CONTROLS-1

Status: authored; **NOT RUN — awaiting maintainer execution**. This section
supersedes the dependency-repair proposal and unqualified scorable-rate reporting
below. Maintainer decision: no additional installs or repairs; exclude tasks that
cannot be verified in the official environment. Candidates and historical attempts
remain unchanged. No controls results or controls.json are fabricated in Git.

### CPU control contract

`controls.ipynb` / `controls.py` run GOLD and EMPTY once each for all 30 development
and 20 disjoint confirmation IDs, in frozen order. GOLD supplies `Task.patch` as
`agent_patch`; EMPTY supplies an empty string. Both call official
`swegemma.harness.verification.verify_task` directly, not an agent/Evaluator loop.
Every call gets a new subprocess manager and fresh official verification workspace.
There are no model, serving, compilation, training or submission calls.
FORGEAI-GEMMA4-LOCAL-EVAL-CONTROLS-ENVIRONMENT-1 adds only the unchanged official
starter cell 2 installation, executed once in the controls process before verification.
The shared `runtime.install_official_environment` verifies `official-cells.json`
against the pinned starter and cell hashes. It never executes cell 8. The official
cell may install serving distributions, but no serving process or model is started.
No task-specific dependency repair or other installation is permitted.

Pinned source contracts:

- `swegemma/models/task.py:116–129`: `Task.patch` is gold; `test_patch` is verifier
  input. Read only inside the future Kaggle worker, never by the coding agent.
- `swegemma/evaluate.py:271–273, 359–377`: public snapshot resolver and verifier
  call signature reused; no secret-hydration fallback is used.
- `swegemma/harness/verification.py:345–358, 384–427, 435–462, 628–719`: fresh
  verification setup, protected-path filtering, patch application, official pytest
  and JUnit predicates, finally/cleanup. GOLD uses the same protected-file filtering
  as candidates; a filtered gold patch is not silently repaired.
- `swegemma/config.py:88–119`: subprocess EvalConfig, 300s command and verification
  limits; `models=None` is unused because no agent call is made.
- Starter cell 10 and HARNESS_README §§4, 8.2: the existing public subprocess
  verification path. Dependency-install skips remain unchanged. No Docker parity
  is claimed; only official starter cell 2 provisions the common environment.

Each GOLD/EMPTY worker is limited to 900s including imports/setup/teardown;
the whole run is limited to 11h plus cleanup grace. No retries/resume or task
replacement. Incomplete attempts remain INCOMPLETE and cannot qualify a task list.
CPU time is UNMEASURED; 100 verification calls with 300s pytest limits alone could
consume 8h20m, excluding setup. The total guard may stop the run before all 50 pairs.

Reference patches exist only in worker memory and temporary official verifier
scratch under `/tmp`, which is removed after the worker. Official verifier needs
temporary patch files to apply GOLD. They are never copied to retained outputs.
Worker stdout/stderr go to the null device; exceptions are reduced to bounded
categories, and no official result/trace writer is called. No task/test/issue text
is included in the output. A quota kill can prevent cleanup: do not download `/tmp`
or arbitrary session files, and end the disposable session. Process ancestry
cleanup has the same non-cgroup limitation documented for the agent harness.

`controls.json` contains fixed provenance hashes, runtime versions, backend,
verification timeout and task rows: ID, repo, class, GOLD/EMPTY boolean/category/
duration. The final raw-file SHA256 is printed as `CONTROLS_SHA256`; retain it
independently and provide it when analyzing. Only this reviewed metadata evidence
file may later be committed, not patches, tasks.jsonl, logs or executed notebooks.

| Control observations | Class |
|---|---|
| GOLD passes; EMPTY fails with a test or own-API verdict | VERIFIABLE |
| GOLD has a third-party import environment error; EMPTY does not pass | ENV_BROKEN |
| EMPTY passes, or GOLD otherwise fails | UNSOUND |
| GOLD passes but EMPTY times out/has environment or execution error | UNSOUND (cannot establish a meaningful failing baseline) |

Timeouts, missing public specs and control execution errors are bounded categories,
not invented missing-dependency diagnoses. Control metadata for confirm-20 is an
environment/soundness screen only; it does not authorize candidate tuning on that
holdout. The reference patch is never exposed to an agent.

### Maintainer steps

1. Run offline fixture controls from repository root in the existing uv environment:

   ```powershell
   uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p 'test_*.py'
   if ($LASTEXITCODE -ne 0) { throw 'Local evaluation CPU control tests failed' }
   ```

   Existing descriptive-statistics tests remain, now explicitly testing raw
   observations. New tests cover gold/empty classification, third-party vs own-API
   errors, exclusions, pin/schema/task coverage, no approval effects and no gold
   in projected output. STOP and paste results before notebook execution.

2. Open the official starter in Kaggle and click **Copy & Edit**. Before running
   any cell, open notebook settings and select **Accelerator: None**, **Internet: Off**.
   Use **Add Input** to attach the competition public data, official wheelhouse
   (`/kaggle/input/datasets/metric/gemma-4-developer-agent-wheelhouse`), and your
   updated complete `local_eval/` tooling dataset, including `official-cells.json`
   and `source-pins.json`. Remove any model/candidate inputs inherited from the starter.
   Replace the starter cells with the cells from `controls.ipynb`; do not Run All
   with starter cells still present. The controls worker, not a manually executed
   starter cell, performs the pinned cell 2 installation. Never run cells 8/10.
   If the official installation or pinned metadata/source checks fail, preserve
   `environment.json` and stop; do not add installs or substitute dependencies.

3. Set TOOLS to the attached tooling directory, both CPU/Internet confirmations
   to true, and `OFFICIAL_ENVIRONMENT_AUTHORIZED = True` after reviewing the
   official cell 2 effects. Set AUTHORIZATION to:

   ```text
   AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL CONTROLS ON dev-30+confirm-20 CPU
   ```

   Execute the controls cells only. Outputs are fresh `/kaggle/working/controls.json`
   and `/kaggle/working/environment.json`; existing evidence causes refusal before
   installation. The latter records starter/cell hashes, pre/post package versions,
   installation duration and state, as in GPU runs. Its cell-hash map identifies
   the pinned starter sources; it does not indicate cell 8 execution.
   Download both files, retain the printed controls digest, and review them.
   Keep environment evidence outside Git; only reviewed controls metadata may be committed.
   No automatic commits or submissions.

4. Analyze the retained smoke run with completed controls and its independently
   retained SHA256 (replace both placeholders):

   ```powershell
   $controlsFile = 'D:\Downloads\YOUR-CONTROLS\controls.json'
   $controlsSha = 'PASTE_PRINTED_CONTROLS_SHA256'
   uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py summary 'D:\Downloads\local-eval-p1-smoke5\forgeai-local-eval-p1-smoke5-attempt1' --controls $controlsFile --controls-sha256 $controlsSha
   if ($LASTEXITCODE -ne 0) { throw 'Control-qualified summary failed' }
   ```

All 50 task IDs, raw control hash, subset/data/source pins, runtime versions,
backend, timeout and bounded metadata schema must match. These pins are not a
claim that every unpinned CPU/GPU host package is identical. Environment changes
require new controls; do not merge outputs across different provisioning baselines.
Only VERIFIABLE tasks enter agent pass rates, repo-macro and paired sign tests.
Excluded counts are reported per class; repositories with no eligible tasks are
explicitly omitted from macro averaging. Runs with unknown eligible outcomes do
not get a complete pass rate. All observed task times remain in time projections
to avoid artificially improving throughput by dropping slow excluded tasks.

### Corrected retained smoke interpretation (static log review, not a run)

| Task | Retained verifier evidence | Descriptive classification |
|---|---|---|
| requests_6644 | Previously supplied resolved=true | Passed observation |
| fastapi_14492 | Previously supplied resolved=true | Passed observation |
| rich_3130 | Previously supplied verification failed | Unresolved observation |
| httpx_3672 | `AttributeError: module 'httpx' has no attribute 'Stream'` | UNRESOLVED_INCOMPLETE_API; agent-side API failure, not a third-party dependency failure |
| fastapi_12942 | `ModuleNotFoundError: No module named 'dirty_equals'` | HARNESS_ENVIRONMENT_ERROR |

The two logs were read from the external retained `official/test_outputs/`
directory; no historical file was rewritten. The derived HTTPX row removes the
generic VERIFICATION_ERROR_OR_INCOMPLETE flag while preserving its false official
verdict. FastAPI retains official_resolved=false but resolved=null. Ambiguous
errors remain unknown; no raw traceback, missing attribute name or patch is placed
in controls.json. The failing module named in an import exception drives ownership,
not the mere presence of repository frames earlier in the traceback.

Corrected descriptive totals: 2 passes, 2 unresolved, 1 environment error; all five
submitted, zero recorded call-budget stops. Previous supplied projections remain
7.238h mean / 9.444h p95, INCONCLUSIVE. **No control-qualified rate is available yet.**
Without --controls, summary emits CONTROLS_REQUIRED, all five UNASSESSED, and null
agent pass/macro rates; raw observations are under
`descriptive_observations_not_control_qualified`. The earlier 2/4=50% describes raw
non-environment observations only and is not a control-qualified result. Do not
fabricate VERIFIABLE classifications before running GOLD/EMPTY.

## Dependency investigation: FORGEAI-GEMMA4-LOCAL-EVAL-DEPENDENCY-FIX-1

Status: classification/summary implemented; **provisioning correction blocked by
missing dependency evidence after public setup inspection**. No tests or workloads
run by the coding agent.

### Export inspection, 2026-10-22

The maintainer supplied four text files under external
`D:\Downloads\competition-infra`. Exact raw-byte SHA256 and sizes are recorded in
`dependency-source-pins.json`; source files remain outside Git. Provenance is the
maintainer-reported CPU/Internet-Off export of the public competition input;
dataset version and exact export timestamp were not supplied.

- `sandbox/setup.py:290–320, 355–361`: fast path adds workspace paths and configures
  test discovery; it does not install missing test wheels. It assumes pre-baked
  dependencies (or the harness's Docker wheel injection).
- `sandbox/setup.py:114–119, 363–390`: slow path collects declared dependencies and
  installs only names present in `/wheels`. Missing names are silently omitted;
  pip runs with `check=False`. Merely invoking it does not prove readiness.
- `sandbox/setup.py:193–213, 352–353`: editable install precedes either path and
  has a fallback that omits `--no-index`; do not execute this on the serving host
  or presume it provides a safe subprocess provisioning bridge.
- `wheels-listing.txt`: no `dirty_equals`/`dirty-equals` distribution filename is
  present. A filename listing cannot rule out vendored code inside other archives,
  but establishes no independently installable wheel for this missing module.
- `docker/` export contains only `imp.py` (compatibility shim) and `telnetlib.py`;
  no Dockerfile, image digest or package installation recipe is available.

Therefore the request's `dirty_equals wheels found: <paste ...>` is an unfilled
placeholder, not evidence that the wheel exists. Wiring the supplied fast-path
script into subprocess verification would not fix the observed missing module.
The current starter-compatible evaluator remains unchanged; no official-source
patch, host installation, dependency stub or backend switch is introduced.

Smallest next evidence: the organizer's participant-accessible dependency artifact
or documented provisioning recipe that supplies `dirty_equals` (and its required
dependencies) for the public subprocess evaluator. If this is not distributed,
request organizer clarification for fastapi_12942 public verification. Do not seek
hidden evaluator data or download a substitute dependency without separate scope.
Do not spend another GPU evaluation on this unresolved environment condition.

Maintainer reports P1 smoke-5 completed with 2/5 official resolved, startup 411.5s,
mean task wall 221s. Mean projection `(411.5 + 116*221)/3600 = 7.235h` is descriptive,
not a PASS: p95 is not supplied and fastapi_12942 collection failed with missing
`dirty_equals`. Preserve that attempt; do not rerun or rewrite it automatically.

Static source findings (the pinned wheel bytes, not installed code):

| Source | Finding |
|---|---|
| HARNESS_README §§4.1–4.2, 8.2 | Docker uses swebench-sandbox:latest; agent and verification have separate lifecycles; documented setup stages wheels and installs test dependencies. |
| Starter notebook cell 10 (zero-based) | Explicit subprocess backend and `wheels_dir=DATA_DIR / 'wheels'`; our EvalConfig already matches these provisioning fields. |
| swegemma 0.2.11 `harness/container_setup.py:506–530` | Both editable package installation and test-dependency installation explicitly return for SubprocessManager/SubprocessSandbox. This is a material backend distinction from the general README setup description. |
| Same file, `21–55`, `61–86`, `318–343`, `393–413`, `531–572` | Docker path resolves public sandbox/setup.py, discovers wheels, injects cached packages and invokes official setup.py with --fast-path and repo. Wheel staging alone is not dependency installation. |
| swegemma `sandbox/subprocess.py:33–41, 328–399` | Per-task virtualenv uses system_site_packages and exposes host site-packages; this does not ensure repository test dependencies exist. |
| adk-eval-core 0.1.0 `sandbox/subprocess_sandbox.py:38–54, 57–100` | Sanitized command environment and bounded process execution, not repository dependency provisioning. |
| swegemma `results.py:39–88`; README §9.2 | Official verification output is retained under test_outputs/<instance_id>.log. |

Confirmed code gap: using the official starter's subprocess configuration skips
the Docker dependency installer. Exact cause of this run's missing module still
needs runtime/setup evidence. No ad hoc dirty_equals installation, wheel unpacking,
class-name bypass, official-package monkeypatch or Docker switch is implemented.
The public setup and wheel-listing inspection above narrows the remaining evidence
to the missing official dependency/provisioning recipe. Do not provide tasks.jsonl,
reference patches or hidden data. Running setup.py on the host has not been shown
safe or equivalent to Docker verification.

New task rows classify explicit ModuleNotFoundError plus pytest collection/conftest
loading evidence as `HARNESS_ENVIRONMENT_ERROR`, with `resolved=null` and
`official_resolved=false`. Ordinary assertion failures remain unresolved. This is
an operational environment classification, not proof of ultimate causality:
candidate-created imports can also cause collection failures and require review.
No error is converted to a pass. Analysis separates environment errors from
resolved/unresolved, reports scorable denominators explicitly, and leaves the
full-subset pass rate and time-fit gate inconclusive when outcomes are unknown.

Analyze a downloaded folder without modifying it (existing uv environment,
repository root; substitute the actual external path):

```powershell
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py summary 'D:\Downloads\YOUR-P1-SMOKE5-OUTPUT'
if ($LASTEXITCODE -ne 0) { throw 'Local evaluation summary failed' }
```

The JSON report includes a per-task table (`per_task`), overall and repo-macro
rates, scorable rates/denominators, stop reasons, tool-call-limit hits, tool usage,
known token totals/unknown counts and mean/p95 time projections. Retained official
verification logs are consulted to derive environment classifications for old
rows in memory; historical tasks.jsonl and official results remain unchanged.
Without the retained log an old unresolved row cannot be reclassified from a
task ID or this README. Excluded repositories are explicit in scorable macro rates.

Manual controls (includes four new classification/summary tests):

```powershell
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p test_local_eval.py
if ($LASTEXITCODE -ne 0) { throw 'Local evaluation dependency diagnostic controls failed' }
```

STOP for results and setup artifacts before any further GPU evaluation.

## Environment update: FORGEAI-GEMMA4-LOCAL-EVAL-ENVIRONMENT-1

The notebook runs the official starter's installation
and serving source unchanged inside the existing watchdog worker, then the harness.
No extra installation is added. Existing authorization, package identity, subset,
holdout, runtime-source and wall-clock gates remain.

Official source: `docs/getting-started-gemma-4-developer-agent.ipynb`:

| Zero-based notebook cell | Code-cell ordinal | Purpose | SHA256 of joined UTF-8 source |
|---|---|---|---|
| 2 | First | Official wheelhouse installation | `c3032e216b0a393aec76180338e56f3ae5d7d995b5de9913f78b79a1fa1105af` |
| 8 | Fourth | Official VllmServer and model registry | `05c129500663d3b377f0ffec84ff7145a942e5414717f1a7733108c619c71b9a` |

`official-cells.json` preserves that source exactly. The worker authenticates both
sources and executes them in one namespace, using `exec(compile(...))`. This keeps
official source unchanged while preserving process-level timeout and cleanup and
avoiding stale notebook imports after package replacement. Do not run a second
copy manually in the notebook kernel. A bridge supplies `AGENT_DIR` (the verified
candidate) and `re`, normally set by starter cell 4. We do not run cell 4, which
copies/mutates sample agents and selects 12B. Cell 8 discovers the actual candidate
model and supplies the exact `models` and `adapters` objects used by evaluation.
The previous handwritten VllmServer configuration has been removed. Official
sample evaluation cell 10 and packaging cell 12 are not executed.

### Click-by-click maintainer setup

1. Open the official **Getting Started: Gemma 4 Developer Agent** notebook from
   the competition **Code** tab. Click **Copy & Edit**. Do not Run All.
2. In the copy choose **File > Import Notebook** and import this repository's
   `local_eval.ipynb`, replacing the example cells. If the UI lacks import, replace
   the copied cells with the local_eval cells in order. Remove original runnable
   demo/evaluation/submission cells before execution. Official cell source remains
   in the attached tooling, executed unchanged by the gated worker.
3. Set **Notebook options / Settings > Accelerator: GPU L4 x4** and **Internet: Off**.
   Use a fresh disposable session with no secrets. GPU quota includes idle time.
4. In **Input > Add Input / Add Data**, attach these five inputs:
   - Competition: **Gemma 4 Developer Agent**, public data at
     `/kaggle/input/competitions/gemma-4-developer-agent`.
   - Official dataset: **metric/gemma-4-developer-agent-wheelhouse**, at
     `/kaggle/input/datasets/metric/gemma-4-developer-agent-wheelhouse`.
   - Model: **Google Gemma 4 > other > gemma-4-31b-it-qat-w4a16-ct > version 2**,
     at `/kaggle/input/models/google/gemma-4/other/gemma-4-31b-it-qat-w4a16-ct/2`.
     Select 31B, not the starter's 12B example. A different mount/version stops.
   - Private harness tooling dataset: the whole current `local_eval/` directory,
     including `official-cells.json`, `source-pins.json`, modules and frozen subsets.
     Set `TOOLS` to its actual mounted path.
   - Private reconciled candidate package dataset: unchanged `manifest.json` and
     `submission.zip.bin`. Use `.bin` to prevent upload auto-extraction. Fill the
     trusted manifest/receipt pins from reconciliation, not a replacement manifest.
5. Review all configuration and choose smoke-5 first. Set a fresh output path,
   the exact candidate/subset authorization, existing approval flags, and the new
   **official_environment_authorized=true**. This explicitly approves the official
   whole-wheelhouse installation and cutlass `.pth` cleanup in this session only.
6. Run the configuration cell, then the launch cell. The watchdog starts before
   installation. Worker order: unchanged cell 2, installed-version/source checks,
   candidate and four-L4 checks, unchanged cell 8, frozen-subset evaluation.
   The official install cell lacks `--no-index`; the worker retains `PIP_NO_INDEX=1`
   and Kaggle Internet Off is mandatory. No other pip commands are authorized.
7. On failure, preserve evidence and stop; do not repair dependencies ad hoc or
   relax source pins. Do not rerun completed tasks automatically.
8. Download the complete output directory and stop the Kaggle session. Analyze
   externally with the existing commands. Never commit outputs or downloaded traces.

New `environment.json` records starter hash, cell hashes, pre/post-install package
versions, post-server versions, installation duration and server startup duration.
`run.json` also records the cell hashes and installation duration. A failed install
retains STARTED evidence and `worker.log`; it never fabricates a successful state.
Package/source checks occur after the official install. The GPU environment remains
unverified until maintainer execution; prior CPU compiler qualification is distinct.

The watchdog includes installation in its total limit. The established 116-task
projection remains measured server startup plus task wall times; installation is
reported separately, so it is not an all-inclusive session-time projection.
Quota/throughput remain UNMEASURED; hidden scorer parity/concurrency remain UNKNOWN.

Existing tests are retained. Added controls compare exact source to starter cells,
reject altered source, and check explicit install approval/evidence plumbing.
Run the existing unittest command and STOP for review before GPU execution.

Status: IMPLEMENTED, MAINTAINER VALIDATION PENDING. No tests, notebooks, models,
installations, evaluations, submissions or commits were executed by the coding
agent. Metadata was read and the approved frozen ID lists were authored as data.
This is public-development tooling, isolated from ForgeAI production, candidate
packages, historical evidence, pilot admissions and frozen KiSSKI evaluations.

## Frozen selection and research boundary

The maintainer supplied the external metadata-only file
`D:\Downloads\gemma4-dev-metadata\public_dev_task_metadata.jsonl`.
Its raw SHA256 is
`8c84d46169b5ca97437151a341792754c4672eafdaba5187abe3e74e3606f7e7`.
It contains 129 rows with only `instance_id`, `repo`, `base_commit`, `created_at`:
67 FastAPI, 48 Rich, 13 Requests, **1 HTTPX**. No bug/feature labels exist;
none are inferred from issue text, filenames, patches, or tests. The coding agent
did not read the official tasks.jsonl or any reference/test payload.

The approved allocation supersedes the infeasible equal-repository request:

| Subset | FastAPI | Requests | Rich | HTTPX | Purpose |
|---|---:|---:|---:|---:|---|
| `smoke-5` | 2 | 1 | 1 | 1 | Runtime/instrumentation smoke; nested in dev-30 |
| `dev-30` | 12 | 6 | 11 | 1 | Development and matched candidate comparisons |
| `confirm-20` | 8 | 4 | 8 | 0 | Disjoint held-out confirmation of a winner only |

Dev-30 gives broad FastAPI/Rich coverage while retaining six Requests tasks and
the only HTTPX task. It is intentionally not proportional to the population;
report both overall task-weighted and equal-repository macro pass rates. HTTPX
results are **anecdotal, n=1**. Confirm-20 excludes HTTPX because none remain;
its macro average covers three repositories, not four. Before choosing confirm-20,
freeze the winning candidate and the development comparison report hash. Set
`confirmation_only=true` and `winner_evidence_sha256` to that reviewed report's
SHA256. These fields record maintainer approval; they do not algorithmically prove
a winner. Never tune from confirmation results, select alternative holdouts after
seeing outcomes, or merge smoke tasks as additional independent dev observations.

`subsets.json` commits only chosen IDs, repository names, null/explicit labels,
seed/schema/inventory count and metadata source hash. `subsets.sha256` pins its
raw LF bytes:
`627f17c74f81450a5ff1787175a30ab9af7ebd9588697ef9e1bbe29367920316`.
Seed `20261021` ranks repository order and IDs by SHA256 of `seed:value`.
Selection alternates explicit bug/feature strata when supplied; here all labels
are null. Confirm selection takes the next ranked IDs after dev selections.
Smoke uses the approved quotas from the same ranked lists. No RNG-version drift,
resampling, replacement, or duplicated HTTPX task is used. The remaining
post-dev pools have 55/7/37 FastAPI/Requests/Rich tasks; confirm consumes 8/4/8.

The metadata source stays outside Git. The selection CLI rejects unexpected
columns (including patches, issue text, tests and solutions). It writes a new
file exclusively, never overwriting the committed freeze. The official tasks file
is resolved **only inside Kaggle by the official task loader/evaluator**. Selected
IDs and repos must match. The whole official task-file hash is retained in the run
record so paired comparisons reject a changed runtime dataset, without exporting
its contents. No reference patches are supplied by this tooling to model prompts.
Official public verification data goes only through the existing evaluator path.
Missing public verification data blocks execution; hidden bundles are not sought.

## Reused source contracts and limits

Source pin authority is the supplied wheel/document bytes recorded in
`source-pins.json`, including all Python members of the three harness wheels.
After the authorized official installation, runtime preflight checks installed
versions and those member bytes without further repair. The selected official wheel files are also
hash-checked in the attached wheelhouse. The new Python modules use standard
library code on the laptop; official dependencies are imported only by the
explicitly authorized GPU worker.

| Contract | Inspected authoritative location | Reuse / limitation |
|---|---|---|
| Dataset path and loading | [starter](../docs/getting-started-gemma-4-developer-agent.ipynb), code cell index 4 (zero-based notebook cells) | Official `load_tasks`, `tasks.jsonl`, snapshots/graphs/embeddings/wheels inputs |
| Serving and four permitted quantized models | starter cell 8; [HARNESS_README](../docs/HARNESS_README.md) §§3.1–3.3 | `discover_declared_models`, `discover_adapters`, `VllmConfig`, `VllmServer`, `create_model_registry`; loopback, TP=4, 32768 context, 0.90 memory, Gemma4 tool/reasoning parsers, model-specific 12B override |
| Official local evaluation | starter cell 10; README §§4, 7.1, 9.1 | `EvalConfig`, `Evaluator.evaluate_task`, subprocess backend, original candidate budgets, 300s default verification timeout, same cache/compaction settings; sequential calls |
| Verification | swegemma 0.2.11 `evaluate.py:221–391`; `harness/verification.py:618–719`; README §8.2 | Keep official resolved flag and verification behavior. Measure enclosing call, including setup and finally/teardown. No custom patch acceptance or test-score predicate |
| Timing and counters | `context.py:184–199, 388–445`; adk-eval-core 0.1.0 `tracing/trace.py:23–78, 373–431` | Agent active time, model-call count, trace tool requests by name and tokens when usage exists |
| Incremental evidence | `results.py:39–88`; README §9.2 | Official patch/test-output artifacts plus our append/flush/fsync task JSONL. Do not replace or merge original attempts |
| Protected files and fallback | README §§8.1–8.2; `tools/execution.py:76–116` | Official filtering and fallback unchanged; filtered final patches cannot prove test files were never touched |
| Runtime package preparation | starter cell 2 | Exact pinned cell executed inside the watchdog after explicit environment approval. It replaces wheelhouse packages and removes cutlass `.pth` hooks in the disposable session |

Local dependency pins: adk-submission 0.2.13, adk-eval-core 0.1.0, swegemma 0.2.11,
google-adk 1.36.1, google-genai 2.11.0, vLLM 0.19.1, transformers 5.13.1.
The broad serving environment is distinct from the previous CPU compiler-only
five-wheel install; that CPU qualification does not qualify GPU serving.
Any missing distribution, source mismatch or import failure is ENVIRONMENT_BLOCKED
or HARNESS_ERROR, not a coding-model failure. No additional package download,
installation, compatibility exception, candidate adjustment, or model fallback.

**UNKNOWN:** private scorer concurrency, hidden task count, hidden environment
overrides, full scorer/bootstrap parity, and leaderboard equivalence. Sequential
execution is a controlled local experimental choice, not a verified hidden-scorer
fact. The 116-task projection is the requested planning assumption.

The official subprocess backend uses local workspaces/venvs and path translation;
it is **not an OS security boundary** (`sandbox/subprocess.py:421–500`). We preserve
the starter's path and do not add privileged Docker or claim isolation from all
attached files. Use only a disposable public-dev session with no secrets or private
datasets. Credentials are removed from worker environment names; the local API
uses the non-secret placeholder `EMPTY`. No hidden tests are attached. The runner
refuses an ancestor `secret` directory to avoid official secret-hydration fallback
(`evaluate.py:81–177`). Internet Off is a mandatory Kaggle UI setting confirmed
by the operator; environment flags alone do not enforce network isolation.

## Recorded evidence and interpretation

`run.json`: candidate, package/manifest/receipt/subset/source hashes, task order and
repos, source/package/Python versions, candidate budgets, model input, UTC epoch,
server startup seconds and wall guard. `tasks.jsonl`: task ID/repo, official resolved
flag, enclosing wall time, active agent time, model turns, tool-name request counts
(including graph tools if declared), budget-counted calls, observed token totals,
submit requested/succeeded, captured patch bytes and changed files, stop reason,
last tool-error presence/name and harness-error category. `events.jsonl` records
task starts. Official traces, patch and verification logs remain in `official/`.

`seconds_per_model_turn = agent_seconds / model_turns` includes tool/reasoning
overhead; it is **not model-serving latency**. Tool requests are not guaranteed
successful mutations. Token totals are null when no usage metadata was observed.
Successful explicit edit_file/write_file responses can establish positive protected
test/config-file touches. Otherwise test-file touches remain UNKNOWN, never false.
Stray-file intent and wrong-location diagnosis remain UNKNOWN:
the public trace/final patch does not reliably expose every transient shell effect,
and no reference-patch comparison is permitted. Do not label a patch “wrong
location” merely because tests fail. Review external traces manually if needed;
never feed verifier/reference output back into the agent loop. `tests_fail` requires
official verification failure evidence; non-test infrastructure errors are distinct.
Stop categories use explicit harness messages; if cleared/unrecorded, use unknown,
not a guessed threshold. Last-tool error detail is retained only in the external
trace; aggregate JSONL never echoes tool arguments, code, prompts, or environment values.

The parent watchdog bounds the entire worker including imports, server startup,
setup and evaluation (after the parent's read-only input/package preflight).
It sends TERM then KILL to the worker process group with at most 10s cleanup grace.
Because adk-eval-core `sandbox/subprocess_sandbox.py:81` starts command sessions
separately, the parent also samples `/proc` descendant PID/start-tick identities
every second and terminates those tracked children, including detached sessions.
Normal completion also cleans up those processes. This is not a cgroup/security
containment guarantee: a process orphaned between samples may evade ancestry
tracking; the first smoke must verify serving cleanup, and the operator must end
the disposable Kaggle session after retaining results. No process arguments or
environment values are read by the watchdog.
A quota/kernel kill can prevent final cleanup or completion.json; preserve all
completed JSONL lines. An unterminated final line is excluded as a torn write.
A started task without a completed row is incomplete, never a fabricated failure.
There is no task retry/resume loop. Official model-invocation retry behavior, if
present in the harness, is unchanged. Review the official execution path before
comparing it to other runtimes.

Analysis reports task-weighted and repo-macro pass rates, per-repo counts,
nonexclusive no-edit/no-submit/budget-exhausted/tests-fail/harness-error counts,
unknown telemetry, and tool usage. Partial runs show lower bounds and no completed
pass-rate claim. Paired comparisons require matching subset/data/runtime pins and
complete known outcomes with no harness errors. They list B wins/losses/ties and
the exact two-sided sign test over discordant pairs. Small samples, shared-repo
dependence, stochastic runs and development-set tuning prevent causal claims from
a single p-value. P1 changes both prompt and budget versus B2; it is not a pure
prompt ablation. Keep confirm-20 out of all tuning decisions.

## Time-fit gate and GPU cost

Both projections include measured server startup:

`mean_hours = (startup_seconds + 116 * mean(task_wall_seconds)) / 3600`

`p95_hours = (startup_seconds + 116 * nearest_rank_p95(task_wall_seconds)) / 3600`

Either estimate **above 11h => FAIL**. Both at/below 11h with a complete error-free
run => PASS; missing startup, partial tasks, harness errors or incomplete process
completion => INCONCLUSIVE. This is a required development gate before every future
submission, not a submission authorization or a bound on leaderboard runtime.
Sample p95 is not a statistical confidence limit. Mean/p95 extrapolation across
non-proportional strata, especially one HTTPX task, has substantial uncertainty.

Agent-only envelopes (verification/setup/startup add time):

| Candidate | smoke-5 | dev-30 | confirm-20 |
|---|---:|---:|---:|
| M2, 1 min/task | 5 min | 30 min | 20 min |
| B2, 4 min/task | 20 min | 120 min | 80 min |
| P1, 6 min/task | 30 min | 180 min | 120 min |

Serving startup has a 20-minute timeout; verification normally has a 5-minute
per-command timeout. Thus P1 smoke planning is 30 min agent + up to 25 min of one
verification command/task + 20 min startup = 75 min **before setup/other commands**,
not a guaranteed runtime ceiling. Notebook smoke guard defaults to 2h, configurable
up to 11h; consider 8h for dev-30 only after measured smoke. These are administrative
limits, not expected measured durations. Actual runtime and throughput: UNMEASURED.
Maintainer reports L4x4 consumes GPU quota at 2x wall time; quota accounting is
not independently verified here. Estimate `2 * allocated_session_hours`, including
setup/idle; first smoke measurements must replace estimates. Stop the GPU session
after retaining evidence. For P1, 116 * 6 min = 11.6h **before** startup/verification,
so budget saturation would fail the 11h projection gate. Do not increase budgets
without measured task wall times and explicit authorization.

## Maintainer validation and operation

From repository root, existing uv environment; no GPU, extra installs or environment
variables needed for the standard-library tests:

```powershell
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/local_eval -p test_local_eval.py
if ($LASTEXITCODE -ne 0) { throw 'Local evaluation offline controls failed' }
```

The test suite checks subset pinning/allocations/disjointness/no sensitive columns,
optional exact regeneration against the external metadata, package and manifest
tampering, traversal, JSONL schemas/torn lines, projections, macro averages, paired
sign tests and inert authorization/notebook boundaries. Expected: all controls pass;
only external-metadata regeneration may skip on another machine. No official/GPU
runtime imports or evaluation occurs in these tests. **STOP and paste results.**

Optional deterministic selection reproduction, performed by the maintainer only;
write outside the repo and compare to committed subsets.json before changing any pin:

```powershell
$subsetReproduction = Join-Path $env:TEMP ('gemma-subsets-' + [guid]::NewGuid().ToString('N') + '.json')
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py freeze 'D:\Downloads\gemma4-dev-metadata\public_dev_task_metadata.jsonl' $subsetReproduction
if ($LASTEXITCODE -ne 0) { throw 'Subset reproduction failed' }
Get-FileHash -LiteralPath $subsetReproduction -Algorithm SHA256
```

After local controls PASS, separately approve the first smoke-5 GPU run:

1. Review and privately attach the complete `local_eval/` directory, the reconciled
   candidate manifest and unchanged `submission.zip.bin`, competition public data,
   official wheelhouse, and matching permitted model. No downloaded trace or complete
   task source enters Git. Verify `manifest_sha256` and `receipt_sha256` from retained
   reconciliation evidence; a manifest claiming portable PASS alone is insufficient.
2. Follow the Copy & Edit and five-input setup above in a disposable Python 3.12
   Linux session. Explicitly approve the official installation with
   `official_environment_authorized=true`; previous CPU scoped-install approval
   does not authorize this broader operation. Keep Internet Off.
3. Import `local_eval.ipynb`, set Accelerator **L4x4**, Internet **Off**. Review the
   GPU-quota effect before enabling the accelerator. Set input paths, candidate,
   raw manifest/receipt pins, fresh output path, and flags. Use the exact phrase
   `AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL p1 ON smoke-5` (replace candidate/subset
   deliberately). All approval flags default false; confirm-20 has an extra gate.
4. First code cell records config exclusively; second launches the watchdog and
   official path. Expected successful state: COMPLETED, five durable task rows,
   populated run metadata and official artifacts. Harness/environment failure or
   guard expiration stops nonzero and preserves partial evidence. Do not automatically
   repeat completed tasks. No Kaggle submission operation is included.
5. Download the entire new output directory outside the repository. Analyze:

```powershell
$localEvalResults = 'D:\Downloads\forgeai-local-eval-p1-smoke5-attempt1'
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py analyze $localEvalResults
if ($LASTEXITCODE -ne 0) { throw 'Local evaluation analysis failed' }
# Only for separately authorized complete matched-subset runs:
uv run --locked --offline --no-sync python -B experiments/gemma4_competition/local_eval/analysis.py analyze 'D:\Downloads\run-a' --compare 'D:\Downloads\run-b'
if ($LASTEXITCODE -ne 0) { throw 'Paired local evaluation analysis failed' }
```

Retain all run/manifest/receipt/subset/package identities, runtime versions, UTC
timestamps, raw official artifacts and partial attempts externally. Commit only
deliberately reviewed metadata/hash records, never traces, patches, test outputs,
candidate binaries, notebooks downloaded after execution or full task data.
Local public-dev performance is development evidence only: no model admission,
production change, leaderboard correctness or general coding-quality qualification.
