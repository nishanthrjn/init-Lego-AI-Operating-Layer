# FORGEAI-GEMMA4-M2-OFFICIAL-ENVIRONMENT-DEVIATION-GATE-1

Verification: **NOT RUN — AWAITING MAINTAINER EXECUTION**.

The previous local-only run passed 21 controls. The maintainer's Python 3.12.13
Linux CPU/Internet-Off Kaggle run installed the five pinned wheels successfully,
but correctly stopped at ENVIRONMENT_BLOCKED before compilation. Its receipt is
`a7956cedbb9734a25dd4bb4b32d52c6f385a890b36e81430e679fa76d4d65def`.
Preserve that blocked install evidence and every old receipt unchanged. This
slice requires a new bundle/receipt; historical reports cannot be upgraded.

Reported initial versions: google-adk 1.29.0, google-genai 1.68.0; the three
competition distributions were missing. Reported post-install versions matched
all five pins. pip check exited 1 without stderr and reported these scoped lines:

```text
google-adk 1.36.1 requires google-cloud-bigquery-storage, which is not installed.
google-genai 2.11.0 has requirement google-auth[requests]<3.0.0,>=2.48.1, but you have google-auth 2.47.0.
google-genai 2.11.0 has requirement pydantic<3.0.0,>=2.12.5, but you have pydantic 2.12.3.
google-cloud-aiplatform 1.148.1 has requirement google-genai<2.0.0,>=1.66.0; python_version >= "3.10", but you have google-genai 2.11.0.
```

Five other reported findings involved bigframes, google-colab (two), dopamine-rl
and moviepy. Their exact lines were not supplied here and are not reconstructed.
The new gate retains all actual pip-check stdout and parsed findings.

These observations establish deviations in the reported participant session.
The official starter's no-deps wheelhouse installation supports the requested
classification rule, but does not independently establish the hidden scoring
image/version or identical runtime behavior. OFFICIAL_ENVIRONMENT_DEVIATION is
a rule-derived label, not proof of harmlessness or hidden-scorer parity.

## Inputs and platform settings

Use Python 3.12 Linux, **Accelerator: None**, **Internet: Off**. Do not inherit
GPU settings from the starter. No model weights are needed. Attach both inputs:

- The fresh receipt-bound transfer bundle. Set BUNDLE to its mounted root
  (default `/kaggle/input/forgeai-gemma4-m2/bundle`). Preserve its internal paths.
- The official wheelhouse dataset at the starter's exact path:
  `/kaggle/input/datasets/metric/gemma-4-developer-agent-wheelhouse`.

The two existing untracked historical bundle ZIPs are pinned by raw SHA256 in
the local scope guard. They are preserved, not transferred as new compiler input.

The bundle contains the four unchanged candidate files, shared portable entry
point, root validator, focused tests, notebook, contract/source registers, three
core wheels and local-receipt.json. The other two install wheels come from the
attached official wheelhouse, checked against the bundled source register. Do
not transfer credentials, custody, the full repository or model weights.

The notebook checks both mounts and a fresh output/log location before proceeding.
It imports only the transferred stdlib-based preparation module at this point.
The official compiler remains behind its existing dependency, installed-byte and
no-external-effects checks. Transfer disclosure is limited to the named bundle.

## Single approval and bounded effects

After reviewing the notebook and settings, the operator sets AUTHORIZATION to:

`AUTHORIZE FORGEAI GEMMA4 M2 KAGGLE CPU SCOPED INSTALL AND COMPILER ONLY`

The only install cell selects exactly these filenames (unique match required):

- `adk_submission-0.2.13-py3-none-any.whl`
- `adk_eval_core-0.1.0-py3-none-any.whl`
- `swegemma-0.2.11-py3-none-any.whl`
- `google_adk-1.36.1-py3-none-any.whl`
- `google_genai-2.11.0-py3-none-any.whl`

All sizes and SHA256 values must match source-register.json before any pip call.
The three core wheels must also equal the bundled bytes. Missing pins, ambiguous
filenames and hash mismatches stop before installation. No version substitution.
The exact subprocess action uses the current notebook Python:

```text
python -m pip install --no-deps --no-index --force-reinstall <five explicit verified wheel paths>
```

Do not run the official starter installation cell. That broad cell installs other
packages and modifies cutlass .pth hooks; neither action is included here. This
slice performs no explicit .pth edits, cutlass cleanup, serving-package installs,
Internet enablement, inference, evaluator calls or submission. Pip may replace
only the five named distributions; their dependencies must already be compatible.
Normal installer changes to those distributions in the disposable session are
expected. CPU/runtime and input/output storage are the remaining platform effects.

Before pip, the entire mounted wheelhouse is inventoried with sorted filenames,
streamed SHA256 and sizes. It must equal all 41 source-register wheel pins;
extra/missing/modified wheels block without installation. All five selected
wheel and three duplicate checks remain. The observed image also has
`/usr/local/bin/uv`; this slice keeps `python -m pip install --no-deps --no-index`
for the requested organizer-starter parity and never invokes uv in Kaggle.

Every pip-check dependency line must parse into dependent/version, required name,
missing/version-conflict kind, installed version (or null), requirement and raw
line. The successful `No broken requirements found.` sentinel is explicitly
recognized. Unparseable lines, inconsistent return codes or any stderr block.
Scope is re-derived from pinned package requirements, not the returned report.
Out-of-scope lines are retained and counted but receive no classification.

For each in-scope finding, canonical required distribution names are compared
with the verified wheelhouse metadata:

- No wheel for that distribution: OFFICIAL_ENVIRONMENT_DEVIATION.
- A wheel exists and the reported installed version equals its pin:
  OFFICIAL_ENVIRONMENT_DEVIATION.
- A wheel exists but the installed version differs or is missing:
  DIVERGENT_FROM_OFFICIAL, which blocks.

With install returncode 0, exact five post-versions, exact inventory and valid
pip-check evidence, no scoped findings gives SCOPED_INSTALL_PASS; exclusively
official-deviation findings gives SCOPED_INSTALL_PASS_WITH_OFFICIAL_DEVIATIONS.
Anything else is ENVIRONMENT_BLOCKED. Reconciliation re-parses the raw report and
rejects stored records, classifications or state that disagree. No dependency
repair, additional package installation or normalization of findings is allowed.

The maintainer separately approved deferring only the exact evidenced metadata
failures to compilation. The worker re-verifies the receipt and install evidence;
it matches the dependent/version, required name, failure kind and observed
installed version before deferring an edge. Version conflicts also require the
reported specifier/extras to match; pip omits those in missing-package lines, so
missing edges require the identical package identity and confirmed absence. Unobserved/transitive failures
still block; installed byte checks and Python compatibility checks remain.
Explicit google.adk/google.genai imports precede the unchanged official directory
validation, full compilation and negative controls. Their failures remain
ENVIRONMENT_BLOCKED, with the failure stage/category recorded; no compiler pass
is emitted. Deviation acceptance is not compiler success.

Every pip/compiler child inherits os.environ after case-insensitive removal of
*TOKEN*, *KEY*, *SECRET*, *PASSWORD*, *CRED*, KAGGLE_*PROXY* and HF_* names.
Other Kaggle flags, including KAGGLE_DISABLE_GOOGLE_GENERATIVE_AI_INTEGRATION,
are preserved. Only removed names are logged. PATH/LD_LIBRARY_PATH remain.
Temporary HOME/TMPDIR and existing CUDA/OTEL/LITELLM/pip overrides still apply.
Use a fresh session without attached credentials; name matching alone cannot
prove that arbitrary differently named variables contain no secrets.

## Evidence and qualification boundary

Installation writes schema-2 `install-evidence.json` into the fresh downloadable output
directory, including wheel names/hashes/sizes, pre/post versions, Python/platform,
removed variable names, return codes, full pip-check stdout/stderr, parsed records and classified scoped findings. Raw installer
stdout/stderr is suppressed. A failure after installation starts preserves bounded
failure evidence; failures before pip leave the environment unchanged and stop.

Compilation accepts an output directory containing only the successful install
evidence. It prints each candidate SHA256 before compilation and retains the
unchanged official directory validation, full compilation, closed registries,
negative controls and deterministic archive checks. It never executes model/tools.
Download the complete output directory and compiler log. On success the directory
contains install-evidence.json, compiler-output.json, manifest.json and submission.zip.
The manifest includes install evidence and its hash, verbatim classified deviation
records, package/Python versions,
sorted ZIP members and ZIP SHA256. Local reconciliation requires the install
artifact, its manifest binding and the same new receipt/candidate bytes.

Portable PASS alone never emits M2 qualification. Both local scope/static PASS
and portable compile/package PASS are required. The package is not a Kaggle
submission authorization, hidden-scorer parity claim or model-quality result.
Downloaded evidence is operator-provided evidence, not remote attestation.

## Separate eval_config finding — candidate unchanged

| Key | Our candidate | Supplied sample |
| --- | ---: | ---: |
| timeout_seconds | 60 | 60 |
| max_tool_calls | 10 | 10 |
| max_time_minutes | 1 | 1 |
| max_turns | 50 | 50 |

All four values match. The sample's comment describes Stage 1 inference budgets.
HARNESS_README explicitly says `scripts/inference.py:load_submission_eval_config`
consumes these submission overrides during Stage 1. Thus they are **documented
scoring-inference inputs, not local-evaluation-only settings**. The starter's
cell 10 also demonstrably reads them and passes them into EvalConfig for its local
two-task demonstration. We do not run that cell.

The hidden inference/metric entry-point implementation is still unavailable;
actual hosted consumption, clamps and environment overrides are not independently
verified. README's illustrative snippet uses timeout_seconds 300, while the
supplied sample uses 60. README lists broader defaults of 60 minutes, 100 inference
tool calls, 500 turns and 300-second command timeout, plus scorer environment
overrides. The sample values are not global scorer limits. README separately
describes Phase 2 verification timeout as 300 seconds; our timeout_seconds is not
proof of controlling that hidden verification budget. No budget change is made.

## Maintainer commands and notebook sequence

From the repository root in the existing locked environment:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_gemma4_m2_minimal_baseline_1.py --local-only
if ($LASTEXITCODE -ne 0) { throw 'M2 scoped-install local preparation failed' }
```

Expected: all focused controls pass, M2_BASELINE_LOCAL_STATIC_CHECKS_PASSED,
LOCAL_SCOPE_AND_STATIC_PASS, and a fresh bundle directory/receipt SHA256. No
installation or official compiler runs locally. Preserve the prior bundle.

After reviewing that result, upload only the new bundle as a private input;
attach the official wheelhouse. Import the updated compiler_only.ipynb from that
bundle, select Accelerator None / Internet Off, set BUNDLE to the actual mount,
and enter the combined approval above. Before every new run, download prior evidence and use **Factory reset / a fresh
session**; restarting cells does not undo installs or clear /kaggle/working.
Run cells in order once. The install cell must emit SCOPED_INSTALL_PASS or
SCOPED_INSTALL_PASS_WITH_OFFICIAL_DEVIATIONS before compilation proceeds. On ENVIRONMENT_BLOCKED,
download evidence and stop; do not install dependencies or rerun the cell.

On success expect PORTABLE_COMPILE_AND_PACKAGE_PASS. Download
`/kaggle/working/gemma4-m2-compiler.log` and the entire
`/kaggle/working/gemma4-m2-compiler/` directory. Keep these outside the repository
pending evidence review. Do not submit submission.zip.

```powershell
$gemmaReceipt = Read-Host 'Absolute path to the NEW local-receipt.json'
$gemmaResults = Read-Host 'Absolute path to the downloaded gemma4-m2-compiler directory'
uv run --locked --offline --no-sync python .\validate_forgeai_gemma4_m2_minimal_baseline_1.py --receipt $gemmaReceipt --reconcile $gemmaResults
if ($LASTEXITCODE -ne 0) { throw 'M2 local/Kaggle evidence reconciliation failed' }
```

Expected: M2_BASELINE_OFFICIAL_COMPILER_VALIDATED and
M2_BASELINE_PACKAGE_VALIDATED. Reconciliation runs the local offline controls but
no compiler/install/model. After functional success, review and stage the intended
changes yourself, then run the separate pre-commit phase:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_gemma4_m2_minimal_baseline_1.py --pre-commit --receipt $gemmaReceipt --reconcile $gemmaResults
if ($LASTEXITCODE -ne 0) { throw 'M2 pre-commit staged consistency failed' }
```

Expected: M2_PRE_COMMIT_STAGED_CONSISTENCY_PASSED. This does not stage or commit.
The default combined local/compiler mode cannot provision Kaggle; use the explicit
local-only, notebook, reconcile sequence above. No automatic installation path was
added to the repository validator.

Proposed commit: `feat(gemma4): reconcile pinned official environment deviations before compilation`.

STOP and paste maintainer results before further work.
