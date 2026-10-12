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

Generative Media now consumes `legoai.runtime.local.open_governed_execution`
for Catalog/lifecycle admission, authorization, dispatch, context establishment,
one-shot claim and canonical settlement. Trusted single-operator composition pins
the exact configuration revision, principal, policy, grant and existing media
Plugin/capability. Requests cannot establish authority. Media retains its adapter,
workflow binding, result validation, image disclosure and job/effect semantics.
This remains process-local operator authority, not durable IAM or tenant isolation.

Each service invocation owns one facade (capacity 1), with the configured media
execution deadline and 5-second preparation/shutdown bounds. It closes on return
or failure, after recording any owner result, including cancellation receipts.
Unresolved close raises the existing `ProviderError` family with the closed reason
`media_execution_unsettled`; owner-private exception custody retains the handle,
unresolved IDs and any failed-settlement receipt. It is not a clean shutdown or
evidence of effect NONE. There is no automatic retry, repair worker or durable
custody; callers must retain the failure for operator investigation. Unclaimed
READY work cannot be settled by inventing owner facts. Other facade refusals map
to `media_execution_refused`. Provider/coordinator internals are not error text.

[Public execution migration](../../planning/GENERATIVE-MEDIA-PUBLIC-EXECUTION-MIGRATION-1.md)
is **pending maintainer validation**; M-01 closes only after that validation passes.
H-01 remains open, ADR-027 remains Proposed, remote VTO remains unsupported and
credentialed media is not qualified. This migration adds no Secret-use authority.
`probe_provider` remains a separate explicit diagnostic; reconciliation remains
read-only and media-owned. Neither opens an execution facade.

Provider selection is configuration. `service.open_text_to_image(config)`
returns a governed `TextToImagePort` + `JobReconciliationPort`. A closed
driver registry chooses the legacy OSS API or Comfy API v2 (Comfy Cloud,
deployments, `comfy-api-proxy`) by explicit `api_family` or by read-only
discovery. Remote endpoints require HTTPS, an allowlisted origin and a bearer
token referenced as `env:NAME`. See
[provider compatibility](../../planning/COMFYUI-PROVIDER-COMPATIBILITY-SLICE.md)
and `uv run --locked python .alidate_comfyui_provider_compatibility.py`.

Privacy-sensitive image inputs (ADR-020): `ImageInput` accepts bounded 8-bit
RGB/RGBA PNG only and keeps just the metadata-free critical chunks.
`service.open_image_transfer(config)` uploads at most two inputs, once each,
to **local** legacy ComfyUI (`type=temp`, UUID names), and reports
`input_disclosure` separately from any job effect. Remote and Cloud are
refused before I/O, and deletion is never claimed. See
[VTO-1](../../planning/VIRTUAL-TRY-ON-VTO1.md).

Virtual try-on (`VirtualTryOnPort`, capability `legoai.virtual-try-on` 1.0.0):
`TryOnRequest(person, garment, seed)` in, `GenerationResult` out.
`service.open_virtual_try_on(config)` checks the explicit deployment declaration
first. Unsupported remote VTO raises the existing `ProviderError` with category
`POLICY_VIOLATION` and reason `remote_personal_images_forbidden`, before credential
resolution/environment lookup, transport construction, discovery (including auto),
workflow loading or personal-image handling. No refusal-capable remote adapter is
constructed. Local family selection and auto-discovery are preserved.

Images enter later through `try_on(request)`, which performs:

- local and capability checks;
- node and model preflight before any personal image is sent;
- two uploads;
- exactly one submission of the approved Qwen-Image-Edit-2509 template
  (fixed 768x1024 portrait; model files come from configuration).

Nothing is retried. See [VTO-2](../../planning/VIRTUAL-TRY-ON-VTO2.md).

Explicit `probe_provider` diagnostics remain a separate operator operation with
their existing contract; opening unsupported VTO never invokes them. This M-04
construction correction is pending maintainer validation. H-01 (purpose-bound
credential use) and M-01 (private Core host coupling) remain open. ADR-027 remains
Proposed; no credentialed media, remote VTO or live ComfyUI is qualified. The
ADR-026 public execution facade is not implemented by this correction.

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
