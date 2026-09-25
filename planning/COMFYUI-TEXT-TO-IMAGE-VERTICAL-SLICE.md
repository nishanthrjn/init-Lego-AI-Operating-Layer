# Local ComfyUI Text-to-Image Integration

Status: IMPLEMENTATION COMPLETE — LOCAL VALIDATION PENDING.
Assessment authority: [ComfyUI impact assessment](COMFYUI-INTEGRATION-IMPACT-ASSESSMENT.md).
No Core, ModelPort or browser contract changes. No live runtime calls or tests run
internally; only syntax/import sanity and focused static source review/formatting.

## Scope and ownership

`packages/legoai-generative-media` owns immutable task values, TextToImagePort,
fixed workflow validation, private ComfyUI transport/adapter, explicit composition
and deterministic tests. `examples/comfyui-text-to-image` is the operator consumer.
No new Kernel primitive, Artifact owner, Model provider, Workflow engine or registry.

Host composition binds one exact configuration revision, approved workflow,
Catalog entry and active Plugin lifecycle record. Requirement compatibility uses
the existing resolver. Authorization/dispatch remain existing reference owners;
claim_invocation prevents a second invocation of the same in-process Execution.
The synchronous deterministic string helper is not used. Unknown external effects
are settled explicitly. No exactly-once, durable recovery or hostile-process claim.
The local reference host explicitly creates operator authority; env/JSON do not.

## Contract and workflow

Request: bounded UTF-8 prompt and optional 63-bit nonnegative seed. Result:
GenerationResult with truthful effect and optional bounded GeneratedImage carrying
job/workflow/seed attribution. It owns bytes, not canonical Artifact custody.

One original built-in-node template is prepared for operator review. Exact bytes
are SHA-256 pinned at startup, then checked against the single supported shape.
Only prompt/seed slots change per invocation. Fixed 512x512 PNG, batch one and
sampler settings. Checkpoint is an operator profile basename, never consumer data.
Template source is an explicit operator file read with a byte ceiling, not a
filesystem path supplied in TextToImageRequest. No generic graph DSL or node loader.

## Transport and lifecycle

Literal loopback HTTP only, explicit port, no hostname resolution, proxy routing,
redirects or compression. Each request has bounded connect/exchange time, header,
JSON and image bytes. Preflight checks required built-in node declarations and
that the approved checkpoint is listed. This does not prove model compatibility;
live generation is required. Route declarations were read in the external local
server source (/prompt, /history/{prompt_id}, /object_info/{node_class}, /view).
The external runtime was not modified or run and its live version is unqualified.

One submission -> bounded history polling -> exactly output node 9 and one output
image -> safe filename/subfolder query -> bounded PNG validation -> typed result.
No direct output-directory reads. External filenames are locators, not trusted
paths or permanent image identity. PNG structure/CRC/dimensions are validated
without decoding compressed image pixels. No renderability/quality claim until live
inspection. Default ceilings and constraints are documented in the package README.

## Effects and cancellation

| Phase | Failure effect |
|---|---|
| Input/preflight before submission | NONE |
| Submission might have been accepted, including malformed/lost response | UNKNOWN |
| Polling deadline/cancel/runtime error without stronger evidence | UNKNOWN |
| Confirmed terminal generation success, retrieval/validation fails | COMPLETED generation; failed result |
| Validated PNG | COMPLETED, successful image result |

Cancellation stops local waits/I/O and propagates GenerationCancelled with the
known job/effect receipt; Execution settlement retains those facts. The outer
execution deadline preserves that receipt rather than losing the job ID.
No global or scoped interrupt is implemented: the safe shared-runtime default
is unknown provider cessation. There is no retry, queue clearing or deletion.
Diagnostic sink failures cannot alter settled effects; observations contain only
safe operation/configuration/category/size fields. Provider receipt is not Evidence
custody. No raw prompts, history, image bytes or provider tracebacks are logged.

## Security, hardware and limitations

Trusted single operator, not multi-tenant isolation or a sandbox for ComfyUI.
Built-in-node allowlisting cannot attest the code actually served by a compromised
runtime. Literal loopback does not authenticate the runtime. Model compatibility,
quality, CPU/CUDA performance and cancellation reconciliation require live evidence.
CPU, CUDA and low/high-VRAM modes have identical application semantics; runtime
hardware selection remains external deployment responsibility. No hardware flags
or installation paths occur in the application task contract.

In-memory authority/configuration lifecycle, no persistent job recovery; workflow
approval is an operator act, not a hash or environment variable. Returned PNGs may
contain provider metadata; do not treat them as sanitized for public distribution.
No automatic remote cessation or output retention guarantee. Core resource claims
are not GPU reservations. Package wheel qualification reuses the pinned root dev
toolchain and imports the wheel from a temporary location without installing it.

## Validation and exact live procedure

Run `python .\validate_comfyui_text_to_image.py`. It uses stdlib orchestration,
streams output, stops on failure, and runs contracts, fake/local-server transport,
effects/cancellation, composition, architecture, temporary wheel import and affected
existing checks. It never installs dependencies, changes source/Git state, starts
ComfyUI or claims live success. Temporary tool/build outputs are removed on exit.

Follow [the example instructions](../examples/comfyui-text-to-image/README.md) for
operator runtime startup, checkpoint prerequisites, template approval, exact command,
explicit output path, cancellation and optional second hardware profile. Paste
validation output and safe result evidence. Do not run Virtual Try-On afterward.

Deferred: remote TLS/auth and Secret integration, job-scoped cancellation after
version-specific proof, Artifact publication/storage, process management, downloads,
custom nodes, generic graph editing, WebSocket transport, retry/recovery, GPU scheduling,
Virtual Try-On, ControlNet and LoRA management.
