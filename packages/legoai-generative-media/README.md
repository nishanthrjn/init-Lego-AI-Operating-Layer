# LegoAI generative media

Local ComfyUI text-to-image vertical slice. Deterministic validation and live
generation/reconciliation were validated locally by the maintainer; see the
implementation document for the exact evidence.

The optional package depends on legoai-reference and Python's standard library;
Core has no dependency on this package. `TextToImagePort.generate` accepts only
`TextToImageRequest(prompt, seed=None)`. A prompt is nonblank, <=4096 UTF-8 bytes,
with no control characters. Seed is an exact integer (not bool) in 0..2**63-1;
omission uses the approved template's deterministic seed 0.

One frozen operator-approved workflow has identity/version/SHA-256 and fixed
prompt slot 6.text, seed slot 3.seed and output node 9. Only these two values are
patched in a private copy. The graph is original project-owned JSON, not copied
from an external workflow: seven built-in nodes, 512x512, batch 1, 20 steps,
Euler/normal, CFG 7, denoise 1, empty negative prompt and filename prefix legoai.
Only an installed checkpoint basename from the operator profile is admitted.
A compatible SD1.x-style checkpoint is required; availability alone does not prove
architectural/model compatibility. No models or nodes are installed by this package.

`LocalComfyUIAdapter` uses bounded HTTP polling with one call in flight and one
submission per call. Timing is one operator-side `CompletionPolicy`, which is
never part of the request. Defaults: 300 s total wait, 1 s poll interval and
10 s per HTTP exchange (connect <= 3 s). The total wait may be up to 1800 s,
for example 900 s for CPU runs. The poll count is derived from the policy. The
deadline uses a monotonic clock.
`reconcile(ProviderJobRef)` inspects an existing job read-only and returns
PENDING, COMPLETED, FAILED, NOT_FOUND or UNRESOLVED. It can never POST.
JSON is <=1 MiB, workflow/request <=256 KiB, PNG <=16 MiB. No automatic retries.
Literal loopback HTTP IPs with explicit ports only; no DNS names, proxies, URL
credentials, redirects or remote hosts. Transport injection is trusted test/host
wiring, never data-derived configuration.

`GeneratedImage` is immutable PNG bytes and provider/job/workflow/seed attribution,
with digest and dimensions. It is NOT a canonical Artifact. PNG validation checks
signature, chunk sequence, CRC, supported 8-bit RGB/RGBA noninterlaced format and
512x512 dimensions; it does not decode pixels or certify compressed pixel semantics.
No partial/oversized image is returned successfully. Bytes live with the result;
ComfyUI owns external output retention. The helper exclusively creates the explicit
output destination and never deletes provider output.

Cancellation raises `GenerationCancelled`, retaining a typed result/job reference.
It stops local I/O/waiting only; no /interrupt or queue mutation is issued. Known
jobs remain available for operator reconciliation. Timeout/lost acknowledgment
never cause resubmission. Successful generation followed by failed image retrieval
retains COMPLETED generation effect while reporting a failed result. Remote
cessation is UNKNOWN, not promised. Process crashes lose in-memory job state.

Composition selects a known exact Contribution using existing Catalog/Plugin
lifecycle/version resolution; configuration cannot import code or grant admission.
The reference local host explicitly issues a scoped grant and uses existing
in-memory authorization, dispatch arbitration, invocation claim and settlement.
Its operator authority is illustrative single-process scope, not durable IAM or
multi-tenant isolation. Constructors/settings are trusted; current lifecycle
withdrawal remains the host's responsibility. No generic provider registry.

Provider selection is configuration. `service.open_text_to_image(config)`
returns a governed `TextToImagePort` + `JobReconciliationPort`. A closed
driver registry chooses the legacy OSS API or Comfy API v2 (Comfy Cloud,
deployments, `comfy-api-proxy`) by explicit `api_family` or by read-only
discovery. Remote endpoints require HTTPS, an allowlisted origin and a bearer
token referenced as `env:NAME`. See
[provider compatibility](../../planning/COMFYUI-PROVIDER-COMPATIBILITY-SLICE.md)
and `uv run --locked python .alidate_comfyui_provider_compatibility.py`.

From the repository root:

```powershell
python .\validate_comfyui_text_to_image.py
```

The launcher uses the existing root `.venv` and its pinned dev tools. If absent,
operator setup is `uv sync --locked` at repository root. No package installation
is performed by validation. Source imports use explicit paths; the launcher builds
a wheel in a temporary directory and imports it without installing it. It checks
only affected existing governance/import-boundary tests, not the full repository.

See [live instructions](../../examples/comfyui-text-to-image/README.md) and
[implementation boundaries](../../planning/COMFYUI-TEXT-TO-IMAGE-VERTICAL-SLICE.md).
