# ComfyUI integration impact assessment

Status: assessment only; proposed implementation boundary, not authorization or
runtime qualification. Prepared 2026-09-25. The maintainer reports the browser
hand-landmark slice locally qualified; this assessment does not reopen it.

## 1. Executive conclusion

Represent ComfyUI as an **external workflow execution provider implementing a
narrow image-generation Capability adapter**. Start with an optional Python
extension package and one text-to-image Port, not a new Kernel primitive,
ModelPort operation, generic workflow engine or provider registry.

No Core contract change is needed for the proposed first proof. Reuse admission,
Catalog resolution, configuration revision, governance and Execution semantics.
New task-specific values and a Port are needed because the existing executable
Model API is chat/embed, and no executable Artifact storage API exists yet.
A typed generated-image result is feasible now; claiming canonical Artifact
publication would require a separately scoped realization of the existing
Artifact owner, not a fabricated reference or new storage framework.

The runtime at `D:\Work\Projects\AI-Applications\ComfyUI\ComfyUI_windows_portable`
remains external and operator-managed. It was not inspected, started, modified,
or contacted in this assessment. Its installed version, checkpoint availability,
workflow compatibility and cancellation behavior remain unverified.

## 2. Current relevant LegoAI abstractions

Inspected only the relevant contracts and wiring:

- [Capability values](../src/legoai/capabilities/values.py): CapabilityRequirement
  expresses identity/version range; CapabilityOffer declares an exact version.
  It is not yet a general feature negotiation or image-generation schema.
- [Catalog](../src/legoai/capabilities/ports.py),
  [Plugin declarations](../src/legoai/plugins/values.py) and lifecycle contracts:
  retain contribution identity, release, tenant and admission; selection is not authority.
- [Execution values](../src/legoai/execution/values.py): ExecutionId,
  ExecutionContext with deadline/correlation, terminal ExecutionResult.
  [Coordinator](../src/legoai/reference/execution.py) supports claim/settlement.
  Its `invoke_governed` accepts a synchronous string-producing callable; do not
  pass an async network job into it or reuse its failure-to-NONE assumption.
- [Model Port](../src/legoai/intelligence/model/ports.py): chat/embed only.
  [Model governed wiring](../src/legoai/runtime/_composition/model_governed.py)
  demonstrates network-effect phase mapping; reuse the pattern, not Model types.
- [Configuration-selected composition](../docs/model-composition.md) and
  [ADR-019](../adrs/ADR-019.md) (Proposed): host-bound constructors, exact
  configuration association, admitted Catalog entries and active lifecycle.
  Existing ModelContribution/ModelBinding are Model-specific, not a ready-made
  generic composition registry.
- [SPEC Artifact/ArtifactVersion and Tool semantics](../SPEC.md): image work
  products already fit the vocabulary. No `src/legoai/artifacts` implementation,
  Artifact reference in the inspected Kernel references, or general ToolPort was
  found. SandboxArtifact explicitly denotes untrusted bytes, not canonical Artifact.
- [Errors](../src/legoai/kernel/errors.py), [effects](../src/legoai/kernel/effects.py),
  [Observation](../src/legoai/observability/values.py) and its sink are reusable.
  EvidenceRecord subjects currently cover configuration/authorization, not arbitrary
  generation provenance. ResourceClaim is declarative, not a GPU reservation service.

Follow existing ownership boundaries in ADR-002/019: package contracts own task
values; private host composition binds implementations; Catalog, Plugin Lifecycle,
Application Composition, Governance and Execution keep their respective authority.

## 3. Correct architectural classification

| Candidate | Decision |
|---|---|
| ModelPort adapter | No: workflow graphs contain models and other executable nodes; chat/embed do not express the operation. |
| Tool | A bounded generation action may later be exposed as a Tool; no Agent/Tool subsystem is required for direct application use. |
| Capability adapter | Yes: implements a declared, versioned text-to-image behavior. |
| External workflow execution provider | Yes: describes ComfyUI's runtime role behind that adapter. |
| Existing canonical Workflow engine | No: do not map ComfyUI nodes into a LegoAI graph or delegate canonical lifecycle ownership to them. |

Use a proposed `TextToImagePort` and `LocalComfyUIAdapter` in an optional
`packages/legoai-generative-media` package. These names are recommendations,
not newly implemented public APIs. Do not name a provider-neutral Port ComfyUIPort.

## 4. Reuse / extend / create matrix

| Requirement | Existing abstraction | Reuse | Extend | New | Why |
|---|---|---|---|---|---|
| Workflow identity | SPEC ArtifactVersion semantics | Immutable version/content identity | Local approved-template descriptor | Package value only | No executable Artifact owner to call today. |
| Generation request | Typed Model/Agent value pattern | Frozen/plain validation pattern | — | TextToImageRequest | ChatRequest cannot express this job. |
| Async job identity | ExecutionId, OperationRef | LegoAI attempt/operation attribution | — | ProviderJobRef in package | ComfyUI prompt ID is not a LegoAI execution identity. |
| Execution status | ExecutionState/ExecutionResult | Terminal lifecycle | Composition phase mapping | Private provider observations | Queued/submitted are not new canonical states. |
| Cancellation | Async execution cancellation/deadline | Caller stop and settlement | External-job cancellation handling | Narrow cancellation disposition | Task cancellation cannot prove remote cessation. |
| Generated artifact | SPEC Artifact/ArtifactVersion | Identity/provenance/ownership meaning | Future owner realization only if promotion required | Bounded GeneratedImage value now | Do not pretend a filename is a governed Artifact. |
| Endpoint configuration | Exact ConfigurationRevisionRef binding | Capture/pin and owner association | Package-specific settings | No configuration service | Endpoint data grants no admission. |
| Error mapping | ErrorCategory, ErrorDetail, EffectExtent | Existing vocabulary | Phase-specific translation | Safe package reason codes | Preserve uncertainty after external submission. |
| Observability | ObservationSinkPort | Correlation, latency, size, safe category | Event codes | No telemetry framework | Diagnostics do not replace evidence. |
| Provenance | Operation/Execution/configuration/Plugin identities | Exact attribution | Typed generation receipt | No new canonical entity | Existing Evidence subject union is not general-purpose. |

## 5. Minimum adapter contract

Propose one asynchronous `TextToImagePort.generate(request) -> GenerationResult`.
The host binds an approved workflow and exact configuration before invocation.
The application supplies a bounded prompt and optional bounded seed, not graph
JSON, checkpoint names, node IDs, output paths or endpoint overrides.

Package values:

- `ApprovedWorkflowRef`: operator-approved identity, immutable version and SHA-256
  of exact template bytes; host manifest specifies allowed input slots/output node.
- `TextToImageRequest`: prompt plus optional integer seed. An explicit effective
  deadline is supplied by host wiring; it cannot exceed the enclosing execution deadline.
- `ProviderJobRef`: bounded opaque prompt ID scoped to the exact runtime binding.
- `GeneratedImage`: bounded immutable bytes, content type, byte length and digest,
  plus producer/provenance receipt. Exactly one image on success.
- `GenerationResult`: success/failure/cancelled/deadline outcome, optional job ref,
  image only on success, ErrorDetail where appropriate, and separate effect extent
  and cancellation disposition (not requested/requested/confirmed/unknown).

Use Python async cancellation; preserve job/effect facts through a package-specific
phase record consumed by host settlement before propagating cancellation. No new
public submit/poll/download service is needed; those steps remain adapter-private.
One call spans the bounded external job. No restart recovery claim or automatic retry.

## 6. Workflow identity and pinning

Approve one API-format text-to-image template, its digest, required built-in node
classes, runtime version and checkpoint compatibility in a trusted manifest.
Patch only declared prompt/seed slots into a private copy after validation. Fix
image dimensions, batch size 1, sampler steps and output node in the approved
profile. User data cannot change class names, links, filenames or loader paths.

The checkpoint binding belongs to the approved runtime/workflow profile, not
application code. Another compatible machine may use another approved binding
without changing that code. Changing the template/checkpoint binding requires a
new exact configuration association; never silently substitute the latest workflow.
A hash identifies content, not approval, node safety or an authenticated runtime.

Reuse ArtifactVersion meaning for the workflow document, but the first proof's
approved descriptor is not a claim of canonical Artifact custody/publication.
Do not invent ComfyUINode or a portable graph language.

## 7. Async job lifecycle

Use HTTP polling initially; WebSocket is optional and deferred unless polling
cannot satisfy the consumer. ComfyUI documents submission at `/prompt`, prompt
history, queue inspection and `/view` retrieval. A successful submission returns
an ID, not a generated image. [Official route documentation](https://docs.comfy.org/development/comfyui-server/comms_routes).

Proposed sequence: validate/admit/claim -> preflight -> submit once -> retain ID ->
bounded history polling -> validate terminal success and expected output -> retrieve
one image -> validate -> settle. Poll an empty history only until the deadline;
absence is not completion. Bound requests, response bytes, poll count and elapsed
wall time. Reserve a small bounded cleanup budget explicitly; no unlimited cleanup.

If WebSocket support is later necessary, correlate every event with the exact job,
bound messages and use terminal history to validate output. `executed` is a node
UI update, not universal job completion. [Official message semantics](https://docs.comfy.org/development/comfyui-server/comms_messages).

Never equate provider queue status with a new ExecutionState. A local cancelled or
failed execution may coexist with an external job whose outcome remains unknown.
A lost submission response is ambiguous: do not resubmit or claim exactly-once.
Retain a known job ID for operator reconciliation; automatic durable resume is deferred.

Cancellation: delete only the exact queued job when supported, and confirm as far
as the pinned runtime allows. Current upstream `/interrupt` accepts a prompt ID,
but omission is global. Older portable versions may differ; queue-check plus global
interrupt is racy. Require verified job-scoped interruption or an explicitly exclusive
runtime before attempting active interruption; otherwise stop local waiting and
report external state unknown. HTTP acknowledgment alone is not cessation evidence.
[Upstream server implementation](https://github.com/Comfy-Org/ComfyUI/blob/master/server.py).

## 8. Artifact / output handling

Treat history and output descriptors as untrusted. Accept one output from the
approved output node, type `output`, validated filename/subfolder and expected MIME.
Reject absolute paths, traversal, drive/UNC paths, separators in basenames, control
characters and output-count violations. Encode query parameters; never concatenate
untrusted URLs or copy an output directory. No direct reading of ComfyUI's filesystem.

Retrieve via the configured origin's `/view`, with redirects disabled and streaming
byte limits. Validate PNG signature/structure, dimensions and MIME against the fixed
profile; constrain decoder resource use if decoding is needed. Compute a SHA-256
of retrieved bytes. Oversized, malformed or unexpected results cannot be successful.
The official example demonstrates history-based image retrieval;
its sample buffering is not a production resource bound.
[Official API example](https://github.com/Comfy-Org/ComfyUI/blob/master/script_examples/websockets_api_example.py).

External output filename is a temporary provider locator, not stable file identity.
The returned digest identifies bytes, not ownership or authorization. The immutable
result owns its bounded in-memory bytes until released by the consumer. ComfyUI
retains its own file under operator policy; LegoAI neither deletes it nor guarantees
its lifetime. If the example saves an image, use an explicitly selected destination,
exclusive/atomic creation and explicit cleanup ownership; no implicit overwrite.

Canonical Artifact promotion is outside this first proof: it would need real owner,
tenant, policy, retention, visibility, version and authorized retrieval behavior.
Record ComfyUI as external producer with exact job/workflow attribution, and the
local Execution as requester/collector; do not invent a local production event.

## 9. Configuration boundary

Minimal host settings: loopback endpoint, approved workflow binding, total timeout,
poll interval and finite request/history/image bounds. Suggested initial ceilings
(subject to local qualification): prompt 4 KiB UTF-8, template 256 KiB, metadata
response 1 MiB, one PNG <=16 MiB and <=1024x1024, one active adapter call, 1-second
poll interval and <=300-second total deadline. These are proposed acceptance limits,
not measured performance promises. CPU workloads may time out explicitly.

Application CapabilityRequirement -> immutable desired configuration binding ->
admitted compatible Catalog contribution -> resolution -> exact provider/Plugin
activation/configuration association -> Port -> governed execution. Known constructors
are trusted host code, never arbitrary imports selected by configuration strings.

Environment/.env may feed validated host settings; they are not canonical authority,
tenant identity or Plugin admission. No configuration DB/service. Preserve Plugin
identity and lifecycle rather than introducing a global ProviderRegistry. Credentialed
remote endpoints are unsupported; future credentials use governed Secret references.

## 10. CPU / CUDA portability rule

The LegoAI API boundary has the same semantics for CPU, CUDA, low-VRAM CUDA and
high-VRAM CUDA deployments. Hardware may change latency, compatible workflows,
memory availability and failures, not request/result meaning. No guarantee of
pixel-identical output, identical performance or seed determinism across hardware.

No application `use_cuda`, GPU name, CUDA version, Python path, launcher filename,
VRAM switch or checkpoint filesystem path. ComfyUI's operator owns deployment.
Do not launch processes, detect CUDA, manage environments or build a GPU scheduler.

## 11. Security / trust boundary

Default to literal `http://127.0.0.1:8188`; optionally admit explicit loopback IPv6.
Reject remote hosts, URL credentials/query/fragment, redirects and proxy-based
routing. If localhost names are supported, resolve and verify loopback without
allowing DNS rebinding. Endpoint selection is operator-controlled, never prompt data.

Loopback is not authentication or tenant isolation. The first proof requires an
operator-trusted local runtime and scoped access; no shared hostile multi-tenant
claim. Permit only approved built-in nodes and locally installed model dependencies.
Custom nodes execute runtime-side code: an allowlist is not a ComfyUI sandbox.
No secrets in prompts/templates; do not record raw workflow or error payloads.
The adapter's loopback transport does not prove an arbitrary runtime/node never
performs egress. Qualify the approved workflow and runtime separately.

## 12. Error / effect semantics

| Observation | Category / disposition | Effect extent |
|---|---|---|
| Invalid input, template or output policy before dispatch | ValidationError or PolicyViolation | NONE |
| Stale binding / incompatible version / disabled contribution | Conflict, VersionMismatch or existing admission failure | NONE |
| Preflight cannot connect; required node/model absent | DependencyFailure | NONE if no submission occurred |
| Submission write/read failure with possible acceptance | DependencyFailure; reconciliation required | UNKNOWN |
| Queue acceptance then deadline or cancelled wait | DeadlineExceeded or cancelled execution | UNKNOWN unless more precise evidence exists |
| Runtime execution error | ExecutionFailure; safe restricted cause | PARTIAL only with evidence, otherwise UNKNOWN |
| Generation completed but image retrieval/validation failed | DependencyFailure or ValidationError; no successful image | COMPLETED for proven generation; retrieval failed separately |
| Validated image retrieved | Success | COMPLETED |

Effect extent describes actual external work, not just availability of a returned
image. Cancellation may leave files or partial work; do not map it automatically
to NONE. PotentiallyRetryable is classification, never permission to replay a
submission. Admission denial remains distinct from provider validation errors.
Use claim_invocation/settle through narrow composition wiring, not the deterministic
string helper. Cancellation cleanup must preserve the original error/uncertainty.

## 13. Observability / provenance

Reuse Observation for safe phase event codes, correlation/trace/operation,
configuration revision, latency, size and error category. Keep approved workflow
reference/digest, provider ID, Plugin release/admission/activation association,
ComfyUI job ID, runtime version when available, seed and image digest in a bounded
typed receipt. Model/checkpoint labels are declared/reported unless a content hash
was actually verified; never upgrade a filename to cryptographic attribution.

Do not emit prompt text, pixels, raw history, machine paths, credentials or stack
traces. Observation is diagnostic, not evidence custody. Existing EvidenceRecord's
subject restrictions preclude pretending a generation receipt was canonically
custodied. No new evidence backend, generic provenance graph or telemetry service.

## 14. Explicit non-goals

No Virtual Try-On, AirTouch, Agents, ControlNet, LoRA management, model downloads,
custom-node installation, workflow editor, generic graph schema, remote GPU/cloud,
process launcher, GUI automation, CUDA tuning, automatic update, config service,
Artifact storage framework, automatic retry or durable job recovery. Do not copy,
vendor, move or modify the external ComfyUI installation.

## 15. Exact first implementation vertical slice

**Local ComfyUI Text-to-Image Integration** — the sole proposed milestone:

1. Operator supplies an already running loopback runtime, pinned supported version,
   one approved API workflow and its already available checkpoint.
2. A direct consumer supplies a prompt and optional safe seed through the narrow Port.
3. Known admitted compatible contribution is selected by exact configuration binding;
   governance/claim occurs before submission.
4. Adapter preflights, submits once, waits boundedly and retrieves one validated image.
5. Return typed image/provenance and settle canonical execution/effect facts.
6. Support cancellation/deadline with explicit remote-stop uncertainty; no global
   interrupt on a shared runtime. Application code contains no GPU-specific behavior.

Acceptance: deterministic transport/contract tests for invalid parameters, unknown
workflow, digest mismatch, unadmitted/disabled/incompatible/stale binding, unavailable
runtime, missing checkpoint/node, lost submit acknowledgment, malformed history,
job mismatch, bounded responses, output traversal, timeout, queued/running cancellation,
failed retrieval and successful one-image result. Test that cancellation never targets
another job and failure never triggers fallback/resubmission. Test fake/real adapter
substitution through the same consumer; construction is not behavioral equivalence.
Then operator-run live generation and cancellation qualification with safe evidence.
CPU/CUDA portability is a contract invariant; claim measured cross-hardware behavior
only after both profiles are tested. No tests or runtime calls were made here.

## 16. Go / No-Go recommendation

**GO for the narrowly scoped implementation**, with no new Core primitive and no
ModelPort changes. Minimal extension: task-specific Port/values, one ComfyUI adapter
and explicit host composition/effect mapping, plus a small consumer and tests.

**NO-GO for production qualification** until the installed runtime version/API,
approved workflow/model dependencies, output bounds and safe cancellation behavior
are verified. Canonical Artifact publication, durable job recovery and runtime
cessation guarantees are not included. If canonical Artifact custody is made a
mandatory first-slice acceptance criterion, stop and scope its missing owner
realization explicitly rather than returning a fictitious Artifact reference.
