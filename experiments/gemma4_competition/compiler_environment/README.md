# FORGEAI-GEMMA4-M2-ISOLATED-COMPILER-ENVIRONMENT-1

Status: specification and metadata-only preflight authored, **NOT RUN — Awaiting
maintainer execution**. Date: 2026-10-19. Baseline commit:
`2731ec799db4694061d0c48cd57ce7219188d3f4`.

The maintainer's previous result established 10 passing policy tests and
M2_BASELINE_LOCAL_STATIC_CHECKS_PASSED. Official compiler validation stopped on
missing adk-submission. Neither official compilation nor package qualification
has been established. This slice does not change the candidate, existing M2 gate,
policy tests, product environment, source register, historical evidence or pilot
admissions. It contains no installer or automatic dependency download.

## Existing environment evidence

Read-only filesystem and distribution-metadata inspection found:

| Location | Observation | Meaning |
| --- | --- | --- |
| Project `.venv/pyvenv.cfg` | CPython 3.14.5; system site disabled | Product environment; preserve unchanged |
| Project `pyproject.toml` | Python >=3.14,<3.15; project runtime dependencies empty | Not the compiler environment |
| PATH Python | `C:\Users\nisha\AppData\Local\Programs\Python\Python313\python.exe` | Not the requested 3.12 target |
| `C:\Users\nisha\AppData\Local\Programs\Python\Python312\python.exe` | Executable version 3.12.10; site-packages contains pip 25.0.1 metadata | Existing 3.12 base, no compiler closure found |
| `C:\Users\nisha\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe` | Executable version 3.12.13; site-packages contains pip 26.1.2 metadata | Preferred existing base for later disposable environment |
| Project site-packages | packaging 26.3 metadata present | Existing metadata-analysis utility; not a preserved wheel |

No compatible pre-existing compiler environment was found in these inspected
locations. This is not an exhaustive scan of private disks, WSL or other users'
environments. The preflight supports explicit additional trusted interpreter
paths. No interpreter was used to import official competition packages.

## Supplied release identities and dependency boundary

The five mandatory public packages are adk-submission 0.2.13, adk-eval-core 0.1.0,
swegemma 0.2.11, google-adk 1.36.1 and google-genai 2.11.0. All five supplied wheels
are `py3-none-any`. Their METADATA and complete RECORD text were read statically;
RECORD entry counts are respectively 25, 52, 40, 590 and 488. Entry count alone
does not verify contents: the authored preflight verifies raw source-register
hashes and each selected wheel's RECORD digests, sizes and coverage when run.

`acquisition-manifest.json` records raw METADATA/RECORD hashes, source-register
wheel hashes, origins as retained by the existing register, exact incoming
constraints and required extras. It is an acquisition request, **not an install
lock or a successful preflight report**. Unknown origins/versions/hashes remain
unknown; local supply and a recorded URL are not an independent publisher-signature
verification. `constraints.txt` freezes the eight supplied release identities
reachable so far; it is deliberately incomplete as an installation plan.

Static dependency analysis for CPython 3.12.13 / Windows AMD64 reaches eight
supplied distributions:

| Package | Supplied version | Windows artifact status |
| --- | --- | --- |
| adk-submission | 0.2.13 | Pure Python wheel |
| adk-eval-core | 0.1.0 | Pure Python wheel |
| swegemma | 0.2.11 | Pure Python wheel |
| google-adk | 1.36.1 | Pure Python wheel |
| google-genai | 2.11.0 | Pure Python wheel |
| transformers | 5.13.1 | Pure Python wheel; native dependencies unresolved |
| tokenizers | 0.22.2 | Only cp39-abi3 manylinux wheel supplied; incompatible with Windows |
| safetensors | 0.8.0 | Only cp310-abi3 manylinux wheel supplied; incompatible with Windows |

60 additional reachable distributions have no wheel in the 41-wheel archive.
Every known incoming requirement is listed in the acquisition manifest. These
include PyYAML, pydantic, packaging, litellm, numpy, pandas, pyarrow, torchvision,
accelerate, requests, httpx, Google cloud libraries and OpenTelemetry libraries.
Their missing METADATA prevents analysis of their further dependencies. The full
closure is therefore **incomplete**, not 68 proven final packages. In particular
torch/native dependencies and platform-specific wheels cannot be assumed present.

Do not discard extras explicitly requested by base dependencies:
google-auth[pyopenssl], google-auth[requests] and
google-cloud-aiplatform[agent-engines] are required dependency edges. User-selected
dev/test/eval/serving extras are not requested. The preflight propagates required
extras to a fixed point, including when a previously visited package gains extras.

Known intersections include pydantic >=2.12.5,<3; PyYAML >=6.0.2,<7;
anyio >=4.9,<5; httpx >=0.28.1,<1; tenacity >=9,<9.2;
websockets >=15.0.1,<16; google-auth >=2.48.1,<3;
tokenizers >=0.22.0,<=0.23.0; safetensors >=0.8.0. These are known incoming
constraints, not selected missing-wheel versions. Additional metadata can tighten
them. No complete compatible resolution has been established.

The other 33 archive wheels are not reachable in the currently known compiler
graph; do not bulk install them. Definite bulk-install conflicts include
xgrammar 0.2.5.post1 requiring transformers <5 versus supplied transformers
5.13.1, and prometheus-fastapi-instrumentator 8.1.0 requiring starlette >=1 versus
google-adk requiring starlette <1. Many supplied native wheels are manylinux-only.
vLLM is not a compiler dependency and its Python <3.14/native serving requirements
do not justify changing product Python. Its CUDA/serving graph is excluded.

Although inference is not executed, swegemma declares torchvision, transformers,
accelerate and other runtime packages unconditionally. They cannot be deleted from
the environment contract just because this is a compiler-only use case. Official
package imports may expose further native/import-time failures; metadata success
cannot establish their absence. A compatible CPU-only native package combination
must be explicitly resolved and reviewed; no CUDA need is asserted for compilation.

Only binary wheels are proposed. No source distributions or source builds are
authorized; project hatchling/editables are not competition build requirements.
An incompatible/missing wheel is a blocker, not permission to build or substitute
an arbitrary release.

## Offline preflight and focused controls

`preflight.py` reads preserved wheel metadata, verifies selected raw hashes against
the unchanged source register, verifies RECORD contents, checks Requires-Python,
version constraints and Windows CPython 3.12 wheel tags, and reports unresolved
metadata explicitly. It is not an index resolver and does not invent versions.
It rejects direct-URL dependencies pending review without fetching them.

For existing interpreters it invokes only a short stdlib metadata reader using
`-I -S`, an empty temporary HOME and a minimal environment. No `.pth`, user-site
or competition package code is imported. Venv site paths are inspected explicitly
because Python 3.12 with `-S` does not initialize venv prefixes normally. Shared
system-site venvs are refused. Results mean metadata compatibility only; native
imports and official compilation remain for the M2 gate. Neither the preflight
nor its tests install anything or invoke the M2 validator.

Working directory: repository root. Use the existing locked environment, which
already supplies packaging for metadata parsing. No credentials or additional
environment variables. Run manually:

```powershell
uv run --locked --offline --no-sync python .\experiments\gemma4_competition\compiler_environment\preflight.py --python 'C:\Users\nisha\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe'
if ($LASTEXITCODE -eq 2) { Write-Host 'Expected prerequisite blocker: inspect missing metadata and wheel tags; do not install automatically.' }
elseif ($LASTEXITCODE -ne 0) { throw 'Compiler environment preflight failed' }
```

Omit `--python` to inspect the current interpreter and known local 3.12 locations;
repeat it to inspect other explicitly trusted existing interpreters. Optional
`--report <new-path.json>` writes JSON exclusively and refuses overwrite. Keep
generated reports outside the repository and historical custody directories.

Exit 2 means no metadata-compatible existing environment. Expected currently:
missing dependency metadata, two incompatible selected wheel tags and missing
installed compiler distributions. Exit 0 means an existing environment passed
metadata checks, even if the local archive is still incomplete; it is **not M2
qualification or permission to provision**. Exit 1 means a failed integrity or
preflight operation. The report distinguishes the archive from installed state.

Focused tests, separately run by the maintainer:

```powershell
uv run --locked --offline --no-sync python -B -m unittest discover -s experiments/gemma4_competition/compiler_environment -p test_preflight.py
if ($LASTEXITCODE -ne 0) { throw 'Compiler environment metadata controls failed' }
```

Seven synthetic controls cover incomplete closure, mandatory transitive extras,
repeated constraints, platform/Python markers, Linux versus Windows ABI tags,
direct URL refusal and valid/tampered RECORD bytes. None has been run by the agent.

## Separately authorized acquisition and provisioning proposal

STOP after preflight results. Current evidence does not permit an offline install.
The maintainer must separately approve acquisition of metadata and Windows wheels
for the 60 missing distributions plus Windows variants of tokenizers 0.22.2 and
safetensors 0.8.0. Exact missing versions are undecided. If those releases have no
suitable Windows wheel, report it and review a compatible release or platform
change separately; do not build or silently change the constraints.

After approval, acquire from reviewed official release sources into a new external
wheelhouse, recording source URL, retrieval date, exact filename/version, SHA256,
size, METADATA, RECORD and platform tags. Do not overwrite the 65-artifact register
or mix acquisition candidates into the historical archive. Expand dependencies
recursively (including required extras), obtain new missing metadata, and record
resolution decisions until closure is complete. A separately reviewed acquisition
register and fully hash-locked `requirements.lock` are prerequisites to installation.
This task does not create a fictitious complete lock or authorize network resolution.

Only after that review, proposed maintainer commands are:

```powershell
# FUTURE, SEPARATELY AUTHORIZED: not executable successfully with today's archive.
$gemmaBasePython = 'C:\Users\nisha\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe'
$gemmaEnv = Join-Path $env:LOCALAPPDATA 'LegoAI\gemma4-compiler-312'
if (Test-Path -LiteralPath $gemmaEnv) { throw 'Choose a fresh environment path; do not overwrite.' }
uv venv --offline --python $gemmaBasePython $gemmaEnv
if ($LASTEXITCODE -ne 0) { throw 'Isolated environment creation failed' }
$gemmaCompilerPython = Join-Path $gemmaEnv 'Scripts\python.exe'
$gemmaWheelhouse = Read-Host 'Absolute path to the separately approved complete wheelhouse'
$gemmaLock = Read-Host 'Absolute path to its reviewed full hash-locked requirements file'
uv pip install --python $gemmaCompilerPython --offline --no-index --no-build --require-hashes --find-links $gemmaWheelhouse -r $gemmaLock
if ($LASTEXITCODE -ne 0) { throw 'Offline isolated provisioning failed; do not fall back to network or source builds' }
uv run --locked --offline --no-sync python .\experiments\gemma4_competition\compiler_environment\preflight.py --python $gemmaCompilerPython
if ($LASTEXITCODE -ne 0) { throw 'Provisioned environment metadata not compatible' }
```

Confirm local uv's supported switches before this later provisioning approval;
no installation command was executed or validated in this slice. Never use the
product `.venv`, `uv sync`, an unrestricted index or `--no-deps` to bypass closure.
No new interpreter download is needed: an existing 3.12.13 executable is available.

## Unchanged M2 gate handoff

The existing M2 validator pins an exact authoring scope relative to its original
Git baseline. The new environment-specification files are deliberately outside
that scope. Do not add a broad ignore/allowlist to make it pass. At the later
maintainer-authorized validation step, use the preserved M2 revision in a clean
detached worktree outside the current checkout. The following prepares that
worktree only after explicit authorization; it does not commit or modify the gate:

```powershell
$gemmaM2Checkout = Join-Path $env:LOCALAPPDATA 'LegoAI\gemma4-m2-offline-checkout'
if (Test-Path -LiteralPath $gemmaM2Checkout) { throw 'Choose a fresh checkout path' }
git worktree add --detach $gemmaM2Checkout 2731ec799db4694061d0c48cd57ce7219188d3f4
if ($LASTEXITCODE -ne 0) { throw 'Preserved M2 checkout preparation failed' }
Push-Location $gemmaM2Checkout
try {
    & $gemmaCompilerPython -B .\validate_forgeai_gemma4_m2_minimal_baseline_1.py
    if ($LASTEXITCODE -ne 0) { throw 'M2 official compiler/package validation failed or blocked' }
} finally { Pop-Location }
```

The compatible interpreter path is the one established in the separate procedure
above, not an implicit activated environment. Only actual official directory
validation and full compilation can establish M2_BASELINE_OFFICIAL_COMPILER_VALIDATED;
only the following deterministic archive checks establish M2_BASELINE_PACKAGE_VALIDATED.
Neither result establishes model quality, hidden scorer parity, Kaggle acceptance,
live execution authorization or submission authorization. No milestone advances
until the maintainer returns those results.

Proposed commit: `chore(gemma4): specify isolated compiler environment and offline preflight`.
