# KAGGLE-COMFYUI-T2I-JOB-1

Status: implementation awaiting maintainer validation. Not run on Kaggle;
no GPU artifact or image quality claim. BASE is
`71583827c09a192515b8a54c3a0cdb8cb3650e21`.

## Interpreter pin conflict and authorized resolution

The prior experiment pins uv 0.9.5, whose bundled Python catalogue cannot
install CPython 3.14.5. This experiment alone pins **uv 0.11.13**, the oldest
release adding the stable `cpython-3.14.5-linux-x86_64-gnu` entry. Evidence:

- [0.11.13 tagged download metadata, entry at line 11476](https://github.com/astral-sh/uv/blob/0.11.13/crates/uv-python/download-metadata.json#L11476).
- [0.11.12 predecessor metadata](https://github.com/astral-sh/uv/blob/0.11.12/crates/uv-python/download-metadata.json#L11476)
  lists 3.14.5rc1 at that position; the stable release was added in 0.11.13.
- [Release changelog](https://github.com/astral-sh/uv/blob/main/changelogs/0.11.x.md#01113).

The selected Python build is `20260510`, with archive SHA256
`dc10977b0db3bef1ee2275107fde6fe9c148135b556fa352e83c6baa67d17ed6`,
as recorded in the tagged catalogue. uv owns verification of its bundled
Python download. The command selects the exact GNU x86_64 target, without a
custom catalogue override.

`runtime_probe.py` pins the PyPI release wheel
`uv-0.11.13-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`, SHA256
`e23ddb47f7a317979cf1945cf9ed89d2639f60f7d06164f9ff1ad292c4cc5b3c`.
Source: [PyPI release metadata](https://pypi.org/pypi/uv/0.11.13/json).
Base pip installs that exact wheel with `--require-hashes`, `--no-deps`, and
`--target /tmp/legoai-c1/tools`. No executable directory is added to PATH.
An existing `/usr/local/bin/uv` is reused only after exact version verification.

Copied/adapted logic: `../free_gpu_model_runtime/runtime_probe.py`, `UV_VERSION`
(line 33), `uv_version` (line 865), `verify_uv` (888), `resolve_uv` (893–943).
The adaptation changes only this experiment's tool pin, adds wheel hash
enforcement and uses its own bounded process capture. It does not import or
modify the previous experiment or the repository's general uv policy.
`.python-version` stays **3.14.5**.

## Acquisition and execution

Use a private Kaggle notebook, T4 x1 (P100 acceptable), **Internet ON**, with
no competition attachment. Expected GPU time is under 30 minutes, subject to
downloads and platform availability. Each cell stops on failure; do not rerun
cells out of order. Start a fresh session after any failure.

Internet Off is unsupported. There is **no pre-uploaded dataset path** for uv
or Python. uv reaches the session through its hash-pinned PyPI wheel download;
uv downloads Python from the public python-build-standalone GitHub release
referenced by its catalogue. The two Git checkouts, ComfyUI dependencies and
checkpoint also require Internet. Set `INTERNET_ON` only after confirming the
session setting; false refuses before fetching or bootstrapping. The flag is
an operator declaration, not an automatic observation of Kaggle settings.
Do not attempt this workflow with Internet Off.

Fill `job_manifest.json` with an independently verified ComfyUI commit and
checkpoint SHA256 and byte size, then review and commit the experiment.
Placeholders intentionally remain in the repository and cause `PIN_MISSING`.
Set the notebook's first code cell `LEGOAI_COMMIT` to that full 40-character
commit. Source is fetched by exact SHA into `/tmp/legoai-c1/legoai` and HEAD
is compared before running the checkout's `job_runner.py`. No source dataset
or alternate code location is used.

The phases are `inspect`, `bootstrap`, `start`, `generate`, `finish`. Persistent
scratch markers refuse repeated, out-of-order, interrupted or failed phases.
The batch clock starts at inspect; commands share the deadline. A supervisor
owns ComfyUI across notebook cells, drains bounded logs, and terminates then
kills its process group on finish, failure or deadline. Abrupt VM termination
cannot guarantee final provenance. No generation retry or resubmission occurs.

ComfyUI uses Kaggle's system Python and installed Torch/CUDA. The requirements
filter removes torch, torchvision and torchaudio direct requirements, while
constraints prevent transitive upgrades of their observed installed versions.
Dependency conflicts stop bootstrap. Other requirements are retained.
ComfyUI is bound to `127.0.0.1:8188`, with all custom nodes disabled. No Manager
or tunnel is installed. The selected commit must support these CLI arguments.

The client uses uv-managed CPython 3.14.5 and the unchanged `generate.py` and
`comfy-local.toml`. Root `pyproject.toml` declares `dependencies = []`;
`packages/legoai-generative-media/pyproject.toml` depends only on that local
root package. `examples/comfyui-text-to-image/generate.py` imports stdlib and
repository media modules and bootstraps both source paths. No client package
installation is required.

Only `/kaggle/working/c1/image.png`, `provenance.json`, and bounded `logs/`
are outputs. All checkouts, tooling, caches and weights are under
`/tmp/legoai-c1/`. Downloads are streamed, size/hash checked, and partial files
removed on failure; HTTP 401/403 produces `DOWNLOAD_AUTH_REQUIRED`.
Logs retain only package version pairs and the client's PNG size/hash line;
other lines are redacted. No raw exception, environment, host or URL dump is
persisted. Pip freeze logs are bounded tails, not a complete dependency lock.
ComfyUI's version and device observations are self-reported. PNG checks cover
structure/CRC/dimensions, not image quality or pixel semantics.

## Maintainer validation

Prerequisites: repository root, existing root uv environment with locked dev
tools already installed. No environment variables are required. The validator
runs only offline tests, architecture checks, typing, lint, format, grammar,
scope/preservation and whitespace checks. It performs no installs or GPU work.

```powershell
git status --short
uv run --locked --offline --no-sync python .\validate_kaggle_comfyui_t2i_job_1.py
git diff --check
git status --short
```

Expected: all phases pass; until manifest pins are filled, the nonfailing pin
report says `RUNNABLE ON KAGGLE: NO` and names the missing fields. Final label:

```text
KAGGLE-COMFYUI-T2I-JOB-1 LOCAL CHECKS PASSED; NOT RUN ON KAGGLE; NO GPU ARTIFACT CLAIMED
```

Verification: **NOT RUN — Awaiting user execution**. Paste the complete output
before further debugging or Kaggle qualification.
