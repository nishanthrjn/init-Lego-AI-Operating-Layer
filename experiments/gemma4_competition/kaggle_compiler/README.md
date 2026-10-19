# FORGEAI-GEMMA4-M2-KAGGLE-SCOPED-COMPILER-INSTALL-1

Verification: **NOT RUN — AWAITING MAINTAINER EXECUTION**.

The maintainer's previous local-only run passed 12 controls. This slice adds a
single, explicitly approved installation of five pinned wheels in a disposable
Kaggle CPU session. It does not qualify a package or authorize model execution.
The earlier receipt `593a9042a90d1f48d46a99f6ee5319d67ea2e9233f2c9fdb3b71e83e89d87537`
remains historical evidence. Generate a new transfer bundle and receipt because
the notebook, shared tooling, tests and root wrapper are receipt-bound.

## Inputs and platform settings

Use Python 3.12 Linux, **Accelerator: None**, **Internet: Off**. Do not inherit
GPU settings from the starter. No model weights are needed. Attach both inputs:

- The fresh receipt-bound transfer bundle. Set BUNDLE to its mounted root
  (default `/kaggle/input/forgeai-gemma4-m2/bundle`). Preserve its internal paths.
- The official wheelhouse dataset at the starter's exact path:
  `/kaggle/input/datasets/metric/gemma-4-developer-agent-wheelhouse`.

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

Pre/post versions are retained. The post-install equality gate requires all five
exact versions. `python -m pip check` inspects the environment; only findings
owned by those five distributions or their declared direct requirement names
(including optional declarations) are retained. Unrelated findings are counted,
not printed. Relevant unmet requirements, unrecognized pip failures or stderr
produce ENVIRONMENT_BLOCKED. No dependency repair or second install is permitted.
A clean scoped pip check is not proof that the whole image is consistent; the
unchanged recursive compiler dependency and source-byte preflight still applies.

Every pip/compiler child inherits os.environ after case-insensitive removal of
KAGGLE_*, *TOKEN*, *KEY*, *SECRET*, *PASSWORD*, HF_* and GOOGLE_*CRED* names.
Only removed names are logged. PATH and LD_LIBRARY_PATH are preserved. Temporary
HOME/TMPDIR and related paths, disabled CUDA visibility and OTEL/LITELLM overrides
are then applied. Pip config-file loading and version checks are disabled. Name
filtering cannot certify that arbitrary differently named variables are secret-free;
use a fresh notebook with no credentials configured. Do not attach secrets.

## Evidence and qualification boundary

Installation writes `install-evidence.json` into the fresh downloadable output
directory, including wheel names/hashes/sizes, pre/post versions, Python/platform,
removed variable names, return codes and the scoped pip-check excerpt. Raw installer
stdout/stderr is suppressed. A failure after installation starts preserves bounded
failure evidence; failures before pip leave the environment unchanged and stop.

Compilation accepts an output directory containing only the successful install
evidence. It prints each candidate SHA256 before compilation and retains the
unchanged official directory validation, full compilation, closed registries,
negative controls and deterministic archive checks. It never executes model/tools.
Download the complete output directory and compiler log. On success the directory
contains install-evidence.json, compiler-output.json, manifest.json and submission.zip.
The manifest includes install evidence and its hash, package/Python versions,
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
and enter the combined approval above. Run cells in order once. The install cell
must emit SCOPED_INSTALL_PASS before compilation proceeds. On ENVIRONMENT_BLOCKED,
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

Proposed commit: `feat(gemma4): gate five-wheel Kaggle compiler install with pinned evidence`.

STOP and paste maintainer results before further work.
