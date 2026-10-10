# Experiment decision: isolated free-GPU runtime qualification

## 1G amendment: constrain presentation before generation

Observed fenced JSON calls for explicit prompt wording and the pinned server's
supported json_object response format. Select the smallest public request field,
only for JSON; leave strict semantic/AST validation and all runtime policies
unchanged. A bounded builder admits only known frozen fixture cases. Reject
cross-experiment evidence before Bootstrap/Run. Source-level support and mocked
regressions do not establish a new live qualification; fresh 1G execution is required.

## 1F amendment: contract alignment and observable behavior

Interpret the unchanged JSON fixture as exact JSON object semantics, not an
unspecified serialization. Reject duplicate/extra keys and wrapped output.
READY stays exact; ADD stays exact AST. Record only schema-controlled structural
facts; known mismatches have their own closed reason. The latest live response
was not preserved, so no claim is made about which JSON property failed.
Remove unmeasurable telemetry and define measured durations precisely. Notebook
cancellation must unwind owned worker groups. Keep runtime, GPU, acquisition,
identity and authority policies frozen. Only a fresh live result can qualify
1F; local offline checks cannot establish GPU success.

## 1E amendment: exact platform executable authority

Live CUDA visibility succeeds; driver observation fails because PATH excludes
/opt/bin. Validate and invoke only /opt/bin/nvidia-smi, without widening PATH.
Reject missing/untrusted/failed/malformed observations separately from observed
unsupported CUDA. Preserve specific hardware reasons and map only actual CUDA
invisibility to the child-environment reason. Reuse the same trusted executable
for memory sampling. No pins, GPU acceptance gates or environment expansion.
Local validation and fresh live qualification remain pending.

## 1D amendment: narrowly validated CUDA platform context

Live diagnostics isolate CUDA invisibility to sanitized child environment
construction. Preserve only exact observed LD_LIBRARY_PATH platform roots,
bounded and deduplicated; reject all other paths. Exclude container-launch
visibility selectors and all other ambient state. The existing frozen worker
hardware preflight remains before server startup, now with a child-environment
failure reason. Mocked contracts establish sanitization and ordering, not real
CUDA sufficiency. Fresh Kaggle qualification remains required. Pins and GPU
acceptance gates do not change.

## 1C amendment: pinned tool target installation

The third live result proves both base and runtime Python lack ensurepip;
system uv 0.12.9 does not satisfy the frozen 0.9.5 policy. Replace the tooling
venv with base pip installing the pinned wheel into SCRATCH/tools. Invoke only
the contained target binary after exact version verification. Refuse partial
targets, preserve bounded version observations, and stop with closed failures.
This supersedes the historical tooling-venv decisions below. It changes no
inference pins, GPU gates or product architecture. Local and live qualification
of 1C remain pending.

## 1B amendment: interpreter availability and environment creation

Live evidence confirms valid CPython 3.12.3 without ensurepip. Use verified uv
0.9.5 to create and seed the model environment. Prefer existing uv only after
version verification; otherwise use the authorized pinned tooling acquisition.
Refuse existing runtime directories without deletion. Verify Python, isolation
and absence of base ML packages before installing unchanged inference pins.
Classify creation failure separately from missing Python. GPU and product
boundaries remain unchanged.


Status: accepted for implementation; local and Kaggle qualification pending.
Scope: FREE-GPU-MODEL-RUNTIME-KAGGLE-1 only. No Core architecture change.

The operator requires zero paid compute. HF returned HTTP 402 and the operator
reports $0.00 credit. That route is paused rather than bypassed. We need evidence
that one public coding model can load and satisfy tiny contracts on free GPUs.

Reuse a published AWQ model and vLLM's standard local server. Keep a source
probe, thin notebook, immutable fixtures, bounded artifacts and offline tests
outside all product packages. An isolated venv avoids coupling to Kaggle's
changing package image or LegoAI's Python 3.14 environment. The observed base
hardware/Python/driver must meet the candidate gate before installation.

Choose Qwen's own 14B AWQ distribution at an immutable revision, with vLLM
0.9.2's explicit V0/Turing settings. Two-way tensor parallelism distributes
weights; it does not merge GPU address spaces. Published artifact size supports
trying the preferred model, not claiming a successful fit. A single T4, another
accelerator or runtime failure stops. A 7B model would be a separately frozen
experiment, not a runtime fallback.

Alternatives considered: installing into Kaggle's base environment risks ABI
conflicts; forcing the latest runtime leaves hardware/engine changes unfrozen;
direct Transformers inference would not exercise the desired local protocol;
publicly exposing Kaggle or integrating ForgeAI exceeds the authorized scope.

Consequences: the candidate runtime is deliberately older and for isolated
synthetic qualification only. Full transitive wheel locking and true offline
replay remain unproven until a successful resolved environment is returned.
Standard server startup errors remain coarse because unrestricted logs are not
persisted. Tight output contracts may fail despite feasible GPU execution;
such failures remain evidence, not permission to relax pass criteria.


## 1A amendment — base launcher is not the inference interpreter

Real Kaggle evidence shows base Python 3.13.15. Widening the old gate alone
would incorrectly create a Python 3.13 inference venv. Resolve an existing
verified CPython 3.12 at two fixed system paths first; otherwise install pinned
uv in a separate tooling venv and acquire its fixed public CPython 3.12.12
Linux x86_64 GNU distribution. Create and verify the model venv before installing
its unchanged packages. Closed phase reasons and manifest-bound source discovery
address the live diagnostic and mount-layout gaps. Neither correction changes
GPU policy, inference behavior, product architecture or qualification claims.
