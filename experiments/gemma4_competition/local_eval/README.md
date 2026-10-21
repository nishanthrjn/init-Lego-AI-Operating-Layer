# FORGEAI-GEMMA4-M3-LOCAL-EVAL-HARNESS-1

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
Runtime preflight checks installed versions and those member bytes without
installing or repairing anything. The selected official wheel files are also
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
| Runtime package preparation | starter cell 2 | Official offline wheelhouse procedure is a **separate maintainer operation**, not an automatic notebook install. It replaces many packages and removes cutlass `.pth` hooks; review and authorize it in a disposable session only |

Local dependency pins: adk-submission 0.2.13, adk-eval-core 0.1.0, swegemma 0.2.11,
google-adk 1.36.1, google-genai 2.11.0, vLLM 0.19.1, transformers 5.13.1.
The broad serving environment is distinct from the previous CPU compiler-only
five-wheel install; that CPU qualification does not qualify GPU serving.
Any missing distribution, source mismatch or import failure is ENVIRONMENT_BLOCKED
or HARNESS_ERROR, not a coding-model failure. No automatic package download,
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
2. Prepare an official compatible Python 3.12 Linux serving environment in the
   disposable session. If packages are missing, **stop for separate approval** of the
   official starter cell 2 installation; do not infer it is covered by previous CPU
   scoped-install approval. Keep Internet Off. No automatic preparation is implemented.
3. Open `local_eval.ipynb`, set Accelerator **L4x4**, Internet **Off**. Review the
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
