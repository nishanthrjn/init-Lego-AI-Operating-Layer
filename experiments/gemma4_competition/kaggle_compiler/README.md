# FORGEAI-GEMMA4-M2-KAGGLE-COMPILER-VALIDATION-READINESS-1

Decision: **KAGGLE_COMPILER_ENVIRONMENT_PREPARATION_REQUIRED**.
Date: 2026-10-19. Authoring baseline: `fa4706e75acba058e648f6d31f88ebe4b8670ee4`.
Verification: **NOT RUN — Awaiting maintainer execution and notebook approval**.

The shortest supported path is to use an existing compatible Kaggle CPython 3.12
Linux image, not construct a Windows inference dependency stack. Its actual
installed versions/bytes have not been observed. No installation is necessarily
needed if that image already satisfies the gate; otherwise preparation requires
separate authorization. Static tests previously passed 10/10 and environment
preflight tests 7/7, but those results do not qualify this newly factored tooling.

## Official starter and environment findings

Sources are the preserved `docs/getting-started-gemma-4-developer-agent.ipynb`
(code cells 2 and 10, zero-based), `docs/HARNESS_README.md` sections 2/7.1 and
`docs/sample_submission/eval_config.yaml`, plus the previously pinned wheel source.
No new public web assumption or hidden scorer source is used.

The official installation cell uses the attached
`/kaggle/input/datasets/metric/gemma-4-developer-agent-wheelhouse`, creates
`/tmp/wheelhouse` symlinks/copies, restores `+cu128` filenames, excludes cutlass,
removes matching cutlass `.pth` files, then invokes:

```text
python -m pip install -q --no-deps --force-reinstall <all selected local wheel paths>
```

The supplied notebook metadata records Python 3.12.13 and
`kaggle.isInternetEnabled: false`. **Internet: Off** is sufficient for this local-file `--no-deps` installation;
turning it on is neither required nor authorized. The cell assumes the notebook
image supplies dependencies omitted from the wheelhouse. It is not a full offline
dependency resolution, and pip's lack of `--no-index` is not evidence that remote
dependencies are required when explicit files and `--no-deps` are used.

Do not execute that broad cell for this slice. It mutates installed packages and
`.pth` hooks, sets serving-related variables, and includes serving packages that
are unnecessary here. No installation cell is included in `compiler_only.ipynb`.
Missing/mismatched packages cause a stop for a separately approved preparation
plan, not permission to execute the official starter wholesale or install all
41 wheels. Do not copy its credential-variable setup. No model weights are needed.

Settings must be **Accelerator: None**, **Internet: Off** before starting the
notebook. These are operator-visible Kaggle settings, not asserted by notebook
metadata. An empty CUDA_VISIBLE_DEVICES in child processes is defense in depth;
it does not replace selecting None and does not allocate a GPU. No GPU quota
may be used. Notebook CPU/runtime/storage usage and private input/output storage
are the anticipated platform effects. No submission API is used.
The starter metadata also names an nvidiaL4 accelerator despite isGpuEnabled false;
do not inherit that ambiguous configuration. Explicitly select None in a fresh notebook.

## Shared implementation and preserved checks

The former validator's official functions now live in `portable_m2.py` and are
used by both paths: `validate_directory`, full `compile_submission`, the closed
tool/model registries, inert agent/model factories, actual generation types,
`swegemma.config.build_submission_limits`, positive/negative compiler controls,
installed-source comparison, dependency preflight, network/process audit guards,
and deterministic ZIP construction/inspection. There is no alternate mocked
compiler and no syntax-only success fallback. Official imports may pull broad
runtime dependencies; failure remains environment-blocked, not a reason to relax
checks. Python 3.12 Linux supports the authored path in principle; actual import
compatibility and the installed dependency closure still require execution.

The local wrapper retains exact Git mutation scope and working whitespace checks.
Its new exact baseline is the recorded pre-task commit above, thereby preserving
all previously committed candidate, artifact, environment-plan and product files.
Only this six-file factoring slice is permitted: root validator, shared module,
focused tests, notebook, this README and `.gitattributes`. No candidate edits are
authorized. The attribute enforces LF for `baseline/**`. Static checks now reject
CRLF candidate bytes rather than silently normalizing them; raw hashes must agree
across machines. The previous CRLF-equivalence test was changed accordingly.

`--local-only` runs local scope/static checks and focused tests and exports a
fresh external transfer directory plus `local-receipt.json`. The receipt binds
raw bytes of every input. Kaggle checks those bytes before compilation, prints
each candidate SHA256, rechecks inputs afterward and emits a portable-only pass.
The local wrapper must reconcile the returned manifest, compiler result and exact
deterministic ZIP against the original receipt and current repository. Only then
are M2_BASELINE_OFFICIAL_COMPILER_VALIDATED and M2_BASELINE_PACKAGE_VALIDATED emitted.
This is maintainer-reviewed evidence, not cryptographic remote attestation: retain
the notebook execution output and review it with the report. Do not manufacture
receipts or copy historical success fields into new evidence.

Staged-content consistency is a distinct `--pre-commit` phase after functional
validation/reconciliation. It still checks exact staged scope, content equality,
candidate index bytes and staged whitespace. Functional validation does not fail
merely because a newly edited validator has not yet been staged. No staging or
committing is performed by any script.

## Exact transfer inputs

Upload only the exported bundle, preserving directory layout. It contains:

```text
local-receipt.json
validate_forgeai_gemma4_m2_minimal_baseline_1.py
experiments/gemma4_competition/
  portable_m2.py
  OFFICIAL-CONTRACT-REGISTER.md
  source-register.json
  baseline/agent.yaml
  baseline/prompts/system.md
  baseline/configs/sampling.yaml
  baseline/eval_config.yaml
  tests/test_m2_minimal_baseline.py
  kaggle_compiler/compiler_only.ipynb
  docs/archive/adk_submission-0.2.13-py3-none-any.whl
  docs/archive/adk_eval_core-0.1.0-py3-none-any.whl
  docs/archive/swegemma-0.2.11-py3-none-any.whl
```

The three wheels are for the unchanged raw pin and installed-source checks, not
automatic installation. The preserved source register remains complete; other
artifact bytes are not required by this portable gate. Installed google-adk
1.36.1 and google-genai 2.11.0 are also mandatory, with compatible installed
dependencies. The full repository, Git history, credentials, custody databases,
model weights, public evaluation tasks and all 41 wheels are not transfer inputs.
The transferred root wrapper/tests are receipt-bound provenance and can be used
locally; Kaggle invokes only the Git-free portable entry point.

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

## Maintainer steps and approval gates

1. Run the local preparation from the repository root, with the existing locked
   environment and temporary symlink permission. It runs offline tests but no
   official compiler, models, installs or network. Output is a fresh temporary
   bundle; record its printed directory and receipt hash.

   ```powershell
   uv run --locked --offline --no-sync python .\validate_forgeai_gemma4_m2_minimal_baseline_1.py --local-only
   if ($LASTEXITCODE -ne 0) { throw 'M2 portable local preparation failed' }
   ```

   Expected: 12 focused tests pass and LOCAL_SCOPE_AND_STATIC_PASS. These updated
   checks are NOT RUN. If candidate line endings fail, inspect the LF attribute
   and checkout bytes; do not bypass the raw-byte comparison.

2. Return the local result. Separately approve uploading exactly this bundle to
   a private Kaggle input and executing this compiler-only notebook. Uploading
   these repository-derived files is external disclosure and is not performed
   by the coding agent. No other repository content is needed.

3. In a fresh CPU notebook set Accelerator None, Internet Off. Attach the approved
   input, import the authored notebook without running it, and set BUNDLE to its
   actual mounted root. After approval only, set AUTHORIZATION to:
   `AUTHORIZE FORGEAI GEMMA4 M2 KAGGLE CPU COMPILER ONLY`.
   First code cell reads Python/package metadata without importing the compiler.
   It stops on non-3.12/non-Linux or mismatched/missing root distributions. No
   further cell or package preparation is authorized if that check fails.

4. If metadata matches, the approved second code cell invokes the portable gate
   with fresh output/log paths. The gate retains its complete dependency/source
   checks and actual offline compilation. It may still stop on an import/native
   mismatch. Do not install, enable Internet, start serving or retry with loosened
   checks. Preserve the safe failure output for review.

5. Download `/kaggle/working/gemma4-m2-compiler.log` and the complete
   `gemma4-m2-compiler/` folder: compiler-output.json, manifest.json and submission.zip.
   On success these expose compiler output, Python/package versions, sorted member
   manifest and ZIP SHA256. Save outside the repository until evidence review;
   no evidence commit is performed in this slice. Never submit the ZIP to Kaggle.

6. Reconcile locally against the original receipt (no model/compiler execution
   occurs during reconciliation; local offline tests do run):

   ```powershell
   $gemmaReceipt = Read-Host 'Absolute path to the original local-receipt.json'
   $gemmaResults = Read-Host 'Absolute path to the downloaded compiler-results directory'
   uv run --locked --offline --no-sync python .\validate_forgeai_gemma4_m2_minimal_baseline_1.py --receipt $gemmaReceipt --reconcile $gemmaResults
   if ($LASTEXITCODE -ne 0) { throw 'Local/Kaggle M2 evidence reconciliation failed' }
   ```

   Both local scope/static PASS and portable compile/package PASS on identical
   inputs are required. No model quality, hidden-scorer parity or Kaggle acceptance
   claim follows. Review the downloaded log alongside the structured evidence.

7. After functional checks pass and the maintainer stages the reviewed changes,
   perform the separate pre-commit check (it does not stage or commit):

   ```powershell
   uv run --locked --offline --no-sync python .\validate_forgeai_gemma4_m2_minimal_baseline_1.py --pre-commit --receipt $gemmaReceipt --reconcile $gemmaResults
   if ($LASTEXITCODE -ne 0) { throw 'M2 pre-commit staged consistency failed' }
   ```

Later acquisition/installation, public-task smoke, model execution and submission
each need their own explicit authorization. This notebook has no installation,
evaluator, vLLM, inference or submission cells. Stop for maintainer review now.

Proposed commit: `refactor(gemma4): prepare byte-bound Kaggle compiler-only validation`.
