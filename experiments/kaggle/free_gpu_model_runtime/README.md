# FREE-GPU-MODEL-RUNTIME-KAGGLE-1E

## Correction 1E: trusted driver tool and preserved hardware reasons

Fifth live result: Inspect **KAGGLE_GPU_READY**; Bootstrap
**DEPENDENCIES_READY**, then **MODEL_DOWNLOADED**. Worker CUDA was available,
with two Tesla T4 devices, capability 7.5, 15636037632 bytes each and torch CUDA
12.8. Worker driver_versions was empty and driver_visible_cuda was null; the
reported reason was CUDA_CHILD_ENV_UNAVAILABLE.

Diagnostics identified `/opt/bin/nvidia-smi` as a regular, non-symlink file
resolving to that exact location. Absolute invocation under the sanitized
environment succeeded (exit 0), returning driver 580.178.04 for both GPUs.
The normal banner reports Driver Version 580.178.04 and CUDA Version 13.0.
The usual /usr/local/nvidia/bin, /usr/local/cuda/bin and /usr/bin locations
were absent. The harness used a bare command while its PATH excluded /opt/bin.
It lost driver evidence, then rewrote DRIVER_CUDA_UNSUPPORTED generically.
These are **TRUSTED NVIDIA-SMI EXECUTABLE RESOLUTION DEFECT** and
**HARDWARE REASON-MAPPING DEFECT**, not GPU, CUDA, driver, torch or vLLM failure.

1E authorizes only `/opt/bin/nvidia-smi`. Before execution it must be absolute,
a regular file, not a symlink, resolve exactly to that path and be executable.
There is no PATH search or general /opt/bin authority. Both driver observations
and optional memory sampling use the validated absolute tool. PATH and the
validated LD_LIBRARY_PATH policy remain unchanged; no NVIDIA_* variables are
added. Fifth-run evidence confirms the current CUDA library policy lets the
isolated torch runtime see both devices.

Driver query lines must be bounded numeric versions matching the observed
GPU count. A bounded banner must supply a numeric CUDA version. Missing,
untrusted, failed or malformed tool observations yield missing driver evidence,
which the hardware gate rejects as DRIVER_OBSERVATION_UNAVAILABLE. Valid visible
CUDA below 12.8 remains DRIVER_CUDA_UNSUPPORTED. No new driver-version minimum
is invented. Raw output and exceptions are not persisted.

Only actual cuda_available=False maps to CUDA_CHILD_ENV_UNAVAILABLE. Count,
model, memory, capability and driver reasons remain distinct. All failures stop
before server startup. Pins and the T4 x2 acceptance policy are unchanged.

**1E local validation pending; Kaggle runtime not qualified.** Preserve the
fifth-run evidence. After local validation and commit, rebuild the bundle and
use a fresh session, stopping on failure. Model download is established in the
prior run; vLLM startup, successful model loading and inference remain unproven.


## Historical correction 1D: validated CUDA library propagation

Fourth live result: Inspect **KAGGLE_GPU_READY**; Bootstrap
**DEPENDENCIES_READY**, then **MODEL_DOWNLOADED**; Run **RESULT_INCONCLUSIVE**
with worker reason **CUDA_UNAVAILABLE**. Direct isolated-runtime diagnostics
show torch 2.7.0+cu128 / CUDA 12.8 sees two Tesla T4 devices in the normal
notebook environment, but zero devices with CUDA unavailable in the restricted
harness environment. This is a **HARNESS CUDA-ENVIRONMENT PROPAGATION DEFECT**;
it does not establish GPU, torch, vLLM, model-load or resource failure.

Observed context: LD_LIBRARY_PATH contained NVIDIA/CUDA platform library roots
(with a duplicate CUDA entry); NVIDIA_VISIBLE_DEVICES was `all`;
CUDA_VISIBLE_DEVICES was absent. Raw environment values are not persisted.

1D reads only LD_LIBRARY_PATH, bounded to 512 characters and 8 colon-separated
entries. Every entry must exactly equal `/usr/local/nvidia/lib64` or
`/usr/local/cuda/lib64`. Duplicates are removed preserving order. Empty, relative,
NUL-containing, home, repository, /tmp and /kaggle paths fail closed with
CUDA_PLATFORM_ENV_INVALID. If absent, it stays absent; no arbitrary defaults
are inferred. All other child environment values remain explicit constants.

NVIDIA_VISIBLE_DEVICES and CUDA_VISIBLE_DEVICES are excluded, including `all`
and arbitrary device strings. NVIDIA documents the former as a
[container-runtime GPU enumeration setting](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/docker-specialized.html).
This harness launches processes inside an already configured container, not new
containers. LD_LIBRARY_PATH alone is the narrow candidate correction. The mocked
loader matrix specifies that boundary and cannot establish actual variable
necessity or sufficiency on Kaggle; a fresh live run must establish that.

The frozen Python worker is launched with the sanitized environment. Before
server startup it observes CUDA availability and device count and applies the
unchanged T4 x2 name, capability, memory and driver gates. A failed gate emits
CUDA_CHILD_ENV_UNAVAILABLE and never starts the server. Secrets, proxies and
arbitrary notebook/operator variables remain excluded.

**1D local validation pending; Kaggle runtime not qualified.** Model download
was observed in the fourth live run; successful model load, vLLM startup and
inference were not. Preserve that evidence. After local validation and commit,
rebuild the upload bundle and use a fresh session; stop on any failed phase.



## Historical correction 1C: pinned tool bootstrap without ensurepip

The third live run reached Inspect **KAGGLE_GPU_READY**, then Bootstrap
**RESULT_INCONCLUSIVE / UV_TOOL_UNAVAILABLE**. Base CPython 3.13.15 at
`/usr/bin/python3` has pip 24.1.2 but no ensurepip. System CPython 3.12.3
also lacks ensurepip. System uv is **0.12.9**, not the frozen **0.9.5**.
The tooling stdlib venv failed because base ensurepip is absent. This is a
**HARNESS PINNED-TOOL BOOTSTRAP DEFECT**. It establishes neither missing uv/Python
nor a GPU, Kaggle, model or vLLM failure. Preserve the failed live artifacts.

1C supersedes the historical tooling-venv mechanism below. Base Python pip
installs only `uv==0.9.5` into an absent `SCRATCH/tools`, using `--target`,
`--isolated`, `--no-input`, `--only-binary=:all:`, `--no-deps`, no cache,
zero retries and bounded timeouts. No stdlib venv or ensurepip is required.
No global or user installation is performed. The executable is resolved only
as `SCRATCH/tools/bin/uv`, checked for containment and verified at 0.9.5 before
use. No module-search or PATH fallback to system uv is allowed.

The [pip target option](https://pip.pypa.io/en/stable/cli/pip_install/#cmdoption-t)
and [uv 0.9.5 target layout](https://github.com/astral-sh/uv/blob/0.9.5/python/uv/_find_uv.py)
support this installation layout. Exact system uv 0.9.5 remains acceptable;
other observed versions are evidence only. The optional observation is a bounded
`system_uv_version` string (or null), without executable paths. Current artifacts
require this field; historical artifacts remain unmodified.

Closed failures distinguish `UV_TOOL_VERSION_UNACCEPTED` from
`UV_PINNED_BOOTSTRAP_FAILED`. Runtime creation/isolation reasons remain intact.
Existing tools or runtime directories are refused without deletion. Runtime
CPython 3.12, separate prefix, disabled system/user sites and no inherited
base torch/transformers are verified before installing unchanged inference pins.

**1C local validation pending; Kaggle runtime not qualified.** After validation
and maintainer commit, rebuild the upload bundle and use a fresh Kaggle session.
Run Inspect, Bootstrap, Run once; stop on any failed phase. No model download,
vLLM startup or successful inference is claimed. No 1C live run has occurred.

## Historical correction 1B: valid Python, missing ensurepip

The second live run reached Inspect **KAGGLE_GPU_READY**. Bootstrap returned
**RESULT_INCONCLUSIVE / RUNTIME_PYTHON_UNAVAILABLE**. Operator diagnostics found
valid CPython **3.12.3** at `/usr/bin/python3.12`: `venv` imports, but `ensurepip`
does not, and stdlib venv creation fails. `/usr/local/bin/uv` is available; its
version was not supplied. Base Python is 3.13.15. This is a **HARNESS
ENVIRONMENT-CREATION DEFECT**, not unavailable Python or a GPU/Kaggle/model/vLLM
failure.

1B supersedes the historical 1A stdlib model-venv creation below. Existing uv
is accepted only after verifying **0.9.5**. Otherwise the authorized tooling-only
mechanism obtains pinned uv 0.9.5 and verifies it. The model environment uses:

```text
uv --no-config venv --python /usr/bin/python3.12 --no-python-downloads --seed --index-url https://pypi.org/simple <SCRATCH>/venv
```

The [uv 0.9.5 CLI definition](https://github.com/astral-sh/uv/blob/0.9.5/crates/uv-cli/src/lib.rs)
confirms interpreter selection and pip seeding. uv does not require the runtime
interpreter's ensurepip; seeding can download pip from public PyPI. The separate
fallback tooling venv can still use the base launcher's stdlib venv, with failure
classified as UV_TOOL_UNAVAILABLE rather than missing runtime Python.

Require the entire target directory to be absent, including symlinks. Never
delete an incomplete venv. Verify the executable, CPython 3.12, distinct prefix,
disabled user/system sites and absence of torch/transformers before installing
the unchanged requirements. Verify exact package versions before downloading
the model, and again at worker startup.

Closed reasons now distinguish RUNTIME_PYTHON_NOT_FOUND, RUNTIME_PYTHON_INVALID,
RUNTIME_ENV_CREATION_FAILED, version/isolation failures, UV_TOOL_UNAVAILABLE and
UV_VERSION_MISMATCH. No raw exceptions enter artifacts. Existing evidence stays
untouched. No apt, sudo, base-image mutation, runtime/model-pin change, GPU-policy
change, retry, or Python 3.13 inference fallback is introduced.

After local validation and maintainer commit, upload the corrected source,
manifest and notebook into a **genuinely fresh session**. Preserve the failed
session's evidence. Run Inspect, Bootstrap, Probe once, stopping on failure.
No fresh Kaggle execution has occurred for 1B.

**Implemented; local validation pending; Kaggle runtime not qualified.**
This is a disposable, synthetic-only runtime experiment. It does not import,
upload or connect LegoAI/ForgeAI. No model-quality claim is made.

## Verified platform baseline (2026-10-10)

- Kaggle's [official retirement announcement](https://www.kaggle.com/product-announcements/735239)
  retires P100 on September 15, 2026 and identifies T4 x2 with **16 GB per GPU**
  as the replacement. This is nominal capacity, not a promise of exactly 16 GiB
  reported by CUDA. The harness records actual bytes; the memories are separate.
- [Notebook documentation](https://www.kaggle.com/docs/notebooks) describes free
  GPU queues, a 12-hour CPU/GPU execution ceiling, 20 GB of saved working output,
  an Internet setting, pip installation, and clean-session Save & Run All.
  Its older P100 paragraph conflicts with the newer announcement above.
- [Kaggle's package documentation](https://www.kaggle.com/docs/packages) describes
  Add-ons → Install Dependencies and saved installation archives.
- [Kaggle staff's persistence description](https://www.kaggle.com/discussions/product-feedback/355440)
  distinguishes optional working-file persistence from temporary files.

Availability, quotas, idleness and session termination remain controlled by
Kaggle. Check the free allocation shown in your account. There is no purchased
compute path. If the interface requires payment, **STOP:
ZERO_COST_REQUIREMENT_VIOLATED**. Ephemeral sessions are not production hosting.

## Frozen experiment decision

See [the experiment decision record](DECISION.md). The sole model is
[`Qwen/Qwen2.5-Coder-14B-Instruct-AWQ`](https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct-AWQ),
revision [`eb3172f06a6d6b3a15f08947b0668d782e4d2d2c`](https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct-AWQ/commit/eb3172f06a6d6b3a15f08947b0668d782e4d2d2c).
Qwen publishes the Apache-2.0 4-bit AWQ artifact. Its approximately 10 GB of
weights and attention-head counts divisible by two make two T4s a reasonable
bounded feasibility candidate, **not a demonstrated fit**.

The selected runtime is **vLLM 0.9.2, V0 engine, XFormers attention, FP16,
AWQ, tensor parallel 2, eager mode**. This deliberately fixed candidate retains
the documented V0 switch and Turing AWQ support. It is not a recommendation for
a public or production server. Sources:
[GPU requirements](https://docs.vllm.ai/en/v0.9.2/getting_started/installation/gpu.html),
[AWQ hardware matrix](https://docs.vllm.ai/en/v0.9.2/features/quantization/supported_hardware.html),
[V0 switch](https://docs.vllm.ai/en/v0.9.2/usage/v1_guide.html),
[Chat Completions and generation configuration](https://docs.vllm.ai/en/v0.9.2/serving/openai_compatible_server.html).

No 7B fallback, dynamic quantization, remote model code, alternate backend,
model-quality benchmark, or post-failure retry is implemented. A failed load
is evidence to return, not permission to change the experiment.

## Dependencies and reproducibility boundary

The Kaggle **base image** supplies Linux, Python, NVIDIA driver, and the torch
installation used only for initial hardware inspection. Their versions are
observed, never assumed. The gate requires an isolated Python 3.12 runtime and exactly
two T4 devices with capability 7.5, actual per-device memory between 14 and
17 GiB, working CUDA, and driver-visible CUDA capability at least 12.8. A gate
failure is RESULT_INCONCLUSIVE, not a claim that all other environments fail.

**Explicit experiment packages** are pinned in `requirements-kaggle.txt`.
vLLM's [release dependencies](https://github.com/vllm-project/vllm/blob/v0.9.2/requirements/cuda.txt)
require torch 2.7.0 and its matching audio/vision packages. We select their
CUDA 12.8 wheels from PyTorch's official index and create a separate temporary
venv. Kaggle's base packages and this repository's lockfile are not modified.
No `pip install -U`, source build, Docker, credential or paid API is required.

The standard pip mechanism is used in this first slice so installation remains
isolated from the notebook kernel. Package Manager is supported by Kaggle but
is not configured here to mutate the base environment. Transitive packages
are resolver-selected; the full resolved **name/version** inventory is captured
after bootstrap. This is not a complete hash-locked wheel archive. Return that
inventory before claiming exact-environment replay. Missing wheels stop the
experiment; they do not trigger compilation or a different runtime.

Weights are ten fixed public files at the pinned revision, downloaded once
without credentials. HTTPS redirects are confined to Hugging Face download
domains. Downloads are capped at 12 GiB overall and 30 minutes; no resumptions
or automatic retries. An authentication/download failure stops. No inference
service is contacted. Runtime loading uses local files and offline flags.

Temporary venv, weights and caches live under `/tmp/legoai-kaggle-runtime-1`,
not saved notebook output. Only the small result files go in `/kaggle/working`.
A fresh session rebuilds temporary state. No fully offline reproducibility
claim exists until demonstrated on Kaggle.

## Operator steps

1. **First run the local validator below** and return failures before using a GPU.
2. Sign in at Kaggle, open **Code → New Notebook**. Keep the notebook private.
3. Set **Settings → Accelerator → GPU T4 x2**. This may restart the session or
   queue. If unavailable, stop and wait for a future free session; do not rent GPU.
4. Enable **Internet** in notebook settings for package/weight acquisition.
   Use a fresh session with persistence disabled. The experiment refuses an
   existing result file so evidence is not silently replaced.
5. On your computer, upload **only this experiment folder** as a private Kaggle
   Dataset (Datasets → New Dataset → upload files/folder → create). Preserve
   `fixtures/`. Do not upload the repository, customer files or credentials.
6. In the notebook use **Add Input** to attach that dataset. Import
   `kaggle_runtime.ipynb` using the notebook's import/upload command. The notebook
   has four code cells and no embedded implementation or execution outputs.
7. The first cell discovers exactly one manifest-verified experiment under
   `/kaggle/input`, including `datasets/<owner>/<dataset>/free_gpu_model_runtime`.
   It checks companion-file hashes before executing any attached source. Set `CONFIRM_FREE_SESSION = True` only after confirming the
   selected GPU allocation requires no payment. Run that cell.
8. Run **Inspect**. Read `inspect: KAGGLE_GPU_READY`; otherwise stop. Actual
   GPU names/count/bytes, torch CUDA runtime and driver observations are saved.
9. Run **Bootstrap** once. It creates the venv and downloads the frozen weights.
   Wait for `download: MODEL_DOWNLOADED`. If installation or acquisition fails,
   do not rerun the cell or supply authentication; download the failure result.
10. Run **Load/probe** once. It loads the model, waits for its owned loopback
    listener, sends one GET `/v1/models` and at most three POST chat requests,
    then terminates the runtime. There is no enduring server to connect to.
    You may turn Internet off after bootstrap if the UI preserves the current
    session; restarting at that point loses temporary downloads. Child runtime
    processes use explicit offline/telemetry-disabled settings either way.
11. Download `kaggle_runtime_result.json` and `kaggle_runtime_report.md` from
    `/kaggle/working` using the notebook's Output/files panel, including on failure.
12. Optionally **Save Version → Save & Run All** for a deliberate fresh-session
    replay with all inputs attached. This runs the experiment again and consumes
    another free session allocation; it is not merely saving existing results.
    Quick Save snapshots the notebook without replay. Download evidence before
    ending the session; do not assume temporary or unsaved files survive.

No Kaggle account token is used by the harness. A command failure prints bounded stdout/stderr and the return code before
raising a notebook RuntimeError. Do not proceed to later cells after a failure.
If Kaggle kills the entire session, artifact completion is not guaranteed;
missing evidence is inconclusive, never PASS.

## Limits, phases and evidence

The endpoint is fixed at `http://127.0.0.1:8765/v1` within the same session.
The API and distributed worker interfaces are configured for loopback; there
is no tunnel, relay, external endpoint option, public binding or ForgeAI client.
Loopback is a same-session boundary, not protection from other code you run
inside that notebook. Do not run unrelated clients during qualification.

Three immutable fixtures (digest-checked, accepting CRLF/LF) request READY,
exact JSON `{"status":"ready"}`, and an annotated Python `add` function.
Generated Python is parsed and compared structurally, **never executed**.
Limits: 512 input characters, 256 templated input tokens, 96 output tokens,
temperature 0, seed 0, one sequence, context 512, no CPU offload, no swap,
80% per-device GPU-memory target. Deterministic settings do not promise
bit-for-bit GPU reproducibility across environments.

Startup is bounded by 600 seconds; each HTTP exchange has a 90-second socket
timeout and 16 KiB response cap. The outer load/probe watchdog caps the whole
run at 960 seconds and stops its process group, including server workers.
Bootstrap has separate 30-minute installation and download ceilings. Listener
readiness checks are bounded TCP observations, not generation retries or HTTP
polling. The client has no redirects, proxies, request retries or fallback.

Closed outcomes are defined in `runtime_probe.py` and `result.schema.json`.
Only all three contract assertions, exact response model identity, `stop`
finish reasons, bounded usage, successful local model listing, and the GPU
gates allow KAGGLE_RUNTIME_PASS. HTTP 200 or server startup alone cannot pass.
Startup failure is coarse RUNTIME_START_FAILED; no attempt is made to infer
OOM, payment, authentication or load causes from runtime exception text.
RESOURCE_EXHAUSTED is used only for a directly observed resource bound.

The schema contains experiment/time, model/revision/quantization, fixed settings,
hardware, base/runtime versions, phase outcomes, timings, memory observations,
and at most three synthetic assertion records. Token fields are **counts**,
not credentials or token IDs. Generated content, raw HTTP bodies, environment,
paths containing account details, server logs and exception strings are omitted.
Artifacts are capped at 128 KiB JSON. Server/install stderr is discarded; safe
phase diagnosis is intentionally coarse. No unrestricted traceback is saved.

Startup timing includes model loading; separate load and first-token timings
are `null` because this standard-server/non-streaming path does not measure
them. GPU memory is the maximum of sampled `nvidia-smi` snapshots, not the
allocator's true peak. A telemetry failure is explicitly marked. No cloud
telemetry dependency is added; vLLM [usage reporting](https://docs.vllm.ai/en/v0.9.2/usage/usage_stats.html)
is disabled.

## Local verification and handoff

From the repository root in PowerShell:

```powershell
uv run --locked --offline --no-sync python .\validate_free_gpu_model_runtime_kaggle_1e.py
if ($LASTEXITCODE -ne 0) { throw 'Kaggle harness local validation failed' }
```

The validator uses mock-only experiment tests, existing architecture tests,
mypy, Ruff with Python 3.10 syntax, formatting and whitespace checks. It never
imports torch/vLLM, installs dependencies, opens a network connection or starts
a GPU. Product-directory changes cause a boundary failure for review. A pass
means **HARNESS LOCALLY READY**, not **KAGGLE RUNTIME QUALIFIED**.

Return the local validator transcript first. After a Kaggle run, return the
two result files and whether the session completed or Kaggle terminated it.
Do not return account details, tokens, package-download URLs, raw logs or model
responses. Missing or unsuccessful evidence remains unqualified.

If local OpenAI protocol and runtime qualification succeed, the next research
slice is KAGGLE-FORGEAI-INTEGRATION-OPTIONS-1: supported zero-cost notebook/job
artifact exchange without public tunnels. No such integration is implemented.
If no supported path exists, Kaggle remains a runtime/evaluation sandbox.


## Correction 1A: launcher and runtime Python

The original harness passed 39 experiment and 365 architecture tests plus
mypy/lint/format/whitespace checks. Those were local checks, not GPU qualification.
On **2026-10-10**, the first real Inspect observed Python **3.13.15**, torch
**2.11.0+cu128**, CUDA available, **two Tesla T4** GPUs, **15,636,037,632 bytes**
each, capability **7.5**, torch CUDA **12.8**, driver **580.178.04**, and
driver-visible CUDA **13.0**. It returned RESULT_INCONCLUSIVE because the harness
rejected base Python above 3.12 before KAGGLE_GPU_READY. This was a harness
launcher constraint, not a GPU, Kaggle, model or vLLM failure. No model was
acquired or executed.

1A keeps that GPU policy and all inference pins. Kaggle's Python 3.13 is only
the launcher. Inspect records `base_versions.python` separately from
`runtime_versions.python`. It checks `/usr/bin/python3.12`, then
`/usr/local/bin/python3.12`, verifying CPython 3.12 without downloading anything.
Otherwise `runtime_python_source` is `to_be_bootstrapped`. Inspect writes only
its bounded qualification evidence, not an environment or interpreter.

Bootstrap uses a verified system CPython 3.12 if present (actual patch version
recorded). Otherwise a tooling-only base-Python venv installs **uv 0.9.5** from
PyPI; uv acquires the exact **cpython-3.12.12-linux-x86_64-gnu** distribution.
The tooling environment never hosts inference packages. No source compilation,
Conda, credential, payment or alternate mirror is used. Astral documents
[managed Python acquisition](https://docs.astral.sh/uv/guides/install-python/);
its [0.9.5 download metadata](https://github.com/astral-sh/uv/blob/0.9.5/crates/uv-python/download-metadata.json)
fixes this CPython artifact to python-build-standalone build **20251014**.
The managed binary is an Astral distribution, not a python.org Linux installer.

Only that resolved Python creates `SCRATCH/venv`. Before inference pip runs,
its version must be CPython 3.12, `sys.prefix != sys.base_prefix`, user sites
must be disabled and `pyvenv.cfg` must explicitly disable system site packages.
The worker rechecks these invariants. System patches may differ but are recorded;
the managed path fixes patch/build. No arbitrary minor-version selection occurs.

Schema version 2 adds `runtime_python_source` and nullable closed phase `reason`.
Reasons distinguish platform, CUDA availability, GPU count/model/memory/capability,
driver evidence, missing/wrong runtime Python, package mismatch, isolation failure,
existing evidence and internal bounded failures. No exception text or paths are
stored. Notebook diagnostics redact unexpected text rather than persist tracebacks.

Bootstrap allows at most ten minutes for interpreter/tool acquisition in addition
to its existing installation/download budgets; the notebook wrapper allows 5000
seconds. Source discovery visits at most 4096 entries, depth six, refuses symlinks
and requires exactly one matching identity manifest with intact companions.
`notebook_support.py` is copied verbatim into the notebook's bootstrap cell;
tests enforce consistency. This is source identity checking, not code signing.

After local validation **and the maintainer's commit**, start a genuinely fresh
Kaggle session and run Inspect, Bootstrap, Probe once in order. Preserve the
old failed Inspect evidence; do not delete it to continue in that session.
The previous upload/archive is stale: upload the corrected source, notebook and
manifest together. No fresh Kaggle execution has occurred for this correction.
