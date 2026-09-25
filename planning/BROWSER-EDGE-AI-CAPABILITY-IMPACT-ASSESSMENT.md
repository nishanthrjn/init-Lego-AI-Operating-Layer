# Browser/Edge AI Capability Impact Assessment

Status: assessment complete; proposed implementation scope, not implementation authorization.
Date: 2026-09-25. Repository inspected at a451abe, including the post-M8.3
configuration-selected Model composition increment. Review: same-assistant static
review, not independent audit, execution qualification or browser experiment.

## 1. Executive conclusion

GO for a separately authorized, narrow Browser Hand-Landmark Local Inference
Vertical Slice using MediaPipe. No foundational redesign, new canonical
ExecutionTarget, ModelArtifactRef, browser Agent runtime or general CV ontology
is justified. Python-first already permits language-neutral interoperability.

The architecture can accommodate browser-local capabilities; the current Python
implementation cannot execute them unchanged. The minimum missing implementation
is a small browser adapter, a closed versioned local request/result contract,
approved asset configuration, bounded frame processing, and explicit unsupported/
failure behavior. Keep these application/adapter-local initially. A browser
demonstration must not claim to be a port of the governed Python runtime.

The latest Model composition proof is committed and the starting working tree
was clean. Its documented follow-ups—live provider evaluations, Secret handling,
public authoring facade and assessment HTTP migration—remain open, not abandoned
half-written code. They do not block this isolated credential-free browser
assessment/proof. They do block claiming general production substitution.
M8.3's plan still says local validation pending; do not turn that historical
status into a qualification claim without new evidence.

## 2. Current architecture and implementation evidence

Targeted inspection, rather than a full milestone re-audit, established:

| Area | Current implementation and limit |
|---|---|
| Packages | Python core under src/legoai; optional Engineering package under packages/legoai-engineering; applications/examples separate. Core has no runtime third-party dependencies. |
| Capabilities | CapabilityRequirement/Offer express identity/version. Catalog publishes activated Plugin offers; resolver retains tenant and snapshot revision. Compatibility is not authorization or hardware/model suitability. |
| Execution | ExecutionContext, Coordinator, dispatch arbiter and governed composition exist. Host supervision and the Engineering Docker sandbox do not imply a browser runner or remote execution protocol. |
| Models | ModelPort has chat/embed; M6.5 logical routing and the latest model_selection wiring select exact admitted Chat contributions. Neither is a vision inference contract. |
| Configuration | Owner-issued revision references and immutable values exist. Durable ConfigurationStorePort/codec concern the normalization fixture. New Model selection uses a closed mapping, not a universal manifest/configuration service. |
| Plugins | Declaration, validation, admission, lifecycle and Catalog publication exist. Full policy/health/hardware/dependency negotiation and durable activation recovery are not implemented by the narrow declaration values. |
| Resources | ResourceQuantity/Claim represent declared/accounting facts. They neither reserve GPU capacity nor enforce memory, frame or elapsed-time budgets. |
| Artifacts | Canonical Artifact Management owns exact versions, content references and provenance. No general src/legoai/artifacts implementation exists. SandboxArtifact explicitly holds untrusted bytes, not canonical Artifacts. |
| Intelligence | One-step Agent definition/request/output validation exists. Engineering Analyst, Reviewer and M8.3 Coding compose it; Coding proposes changes rather than applying them. No general implemented Skill/Workflow/Team engine was found. |
| Governance | Explicit TenantContext, Principal/security references, authorization and dispatch separate authority from selection. Model/Agent outputs have no authority. |
| Wire and diagnostics | Immutable nominal values and the owner-specific JSON codec exist; no general browser wire contract. ObservationSinkPort accepts closed diagnostic fields. Evidence custody covers configuration/authorization subjects, not arbitrary inference payloads. |

Evidence: [capability values](../src/legoai/capabilities/values.py),
[resolver](../src/legoai/reference/resolution.py),
[Catalog](../src/legoai/reference/catalog.py),
[execution](../src/legoai/reference/execution.py),
[Model composition](../docs/model-composition.md),
[resources](../src/legoai/resources/values.py),
[codec](../src/legoai/reference/application/codec.py),
[M8.3](M8.3-BOUNDED-CODING-PLAN.md),
[Artifact contracts §22](../contracts/CONTRACTS.md),
[IA-001](../intent-amendments/IA-001.md).

## 3. Requirements from the two concrete consumers

MediaPipe's browser Hand Landmarker accepts images/video frames, produces 21
landmarks per detected hand, and exposes synchronous detection calls. Its guide
recommends workers to avoid blocking the UI. These facts justify a worker and
bounded local result conversion, not a browser workflow engine.
[MediaPipe guide](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/web_js).

ONNX Runtime Web provides WebGPU and WASM execution options. Available browser
APIs alone do not establish that a particular model/operator set will run.
The adapter must validate the selected model's supported execution path.
[WebGPU guide](https://onnxruntime.ai/docs/tutorials/web/ep-webgpu.html).

Both need pinned executable/assets, local input ownership, typed output conversion,
initialization failure reporting and cleanup. They are different technologies,
not interchangeable semantic capabilities by default. An ONNX classification
model cannot replace Hand Landmarker merely because both run in a browser.

## 4. Existing abstractions to reuse

Reuse capability identity/version, Plugin identity/release, configuration revision,
explicit scope, error/effect distinctions and observability/evidence separation.
Reuse their meaning, not Python object serialization or fabricated client-side
authority. If a server later participates, its existing Catalog/admission and
authorization remain accountable owners.

Model is an intelligent interaction abstraction; Capability states what is
provided; Tool mediates actions. ONNX is execution technology, MediaPipe is an
implementation technology, WebGPU is a backend, and browser is an environment.
An adapter translates capability semantics into that technology. Transport
carries messages; Artifact identifies versioned content. No new taxonomy or
canonical entity is needed to preserve these distinctions.

## 5. Gaps and decision classification

A = no semantic change; B = application-local; C = adapter-local;
D = small LegoAI extension; E = new primitive.

Actual gaps are browser execution code (C), local media lifetime management (C),
a hand-task contract (B), explicit local-only configuration interpretation (B/C),
asset verification (C), and a language-neutral representation for the task (B).
The current resolver cannot evaluate local-only/device/model constraints; a
browser adapter's preflight must enforce them separately from identity/version
matching. Broadening generic CapabilityRequirement is not required for one task.

There is no E gap established. There is no immediate D core API change required.
Promotion of repeated task constraints or provenance representations to published
LegoAI contracts is a future D candidate, contingent on actual second-consumer
evidence. ONNX and MediaPipe alone do not prove identical result semantics.

## 6. Reuse versus Extend versus Create matrix

“New” below means a small local contract/implementation unless explicitly stated;
it does not mean a new canonical primitive.

| Requirement | Existing abstraction | Reuse as-is | Extend | New | Justification/class |
|---|---|---|---|---|---|
| Browser execution | Execution/adapter ownership | Meaning | No core change | Local worker adapter | C; Python Coordinator is not a browser dispatcher |
| Execution location | Plugin realization/configuration semantics | Ownership | None now | Local fixed environment field | C; no scheduler needs a target entity |
| Local-only constraint | Policy/configuration separation | Principle | Task configuration only | Closed local-only field | B/C; existing resolver has no privacy evaluator |
| Runtime features | Capability resolution | Identity/version | None now | Small preflight result | C; no general hardware taxonomy |
| Asset identity | Artifact exact-version/content semantics | Meaning | None now | Local asset descriptor | C; implement no Artifact service |
| Adapter selection | Catalog/admission/resolution | Owners | Browser binding representation only | Static known binding | C; no executable imports from data |
| Hand output | Versioned capability contract | Mechanism | None now | One application-owned value | B; no reusable CV ontology yet |
| Telemetry | ObservationSinkPort | Existing subset | None now | Local bounded diagnostic record | C; no arbitrary attribute bag |
| Errors | ErrorCategory/EffectExtent | Meaning | None now | Task status/reason codes | B/C; unsupported is not a new ExecutionState |
| Cancellation/deadline | Execution distinctions | Meaning | No Python changes | Local lifecycle handling | C; late-result discard differs from stopping compute |
| Configuration | Immutable revision pinning | Principle | None now | Task-specific serialized snapshot | B/C; env input is not authority |
| Provenance | Artifact/provenance ownership | Principle | None now | Claimed local attribution | C; browser claims are not custody evidence |
| Budgets | ResourceQuantity/Claim | Vocabulary | None now | Local frame/queue limits | C; no reservation or GPU capacity guarantee |
| Wire representation | Owner-specific codecs | Pattern only | None now | Closed task schema | B; normalization codec is not reusable wire transport |

## 7. Minimal proposed contract changes

Change no ModelPort, Kernel or canonical execution enum. Specify only a versioned
hand-task request/configuration and result representation with explicit validators.
Use a bounded request identifier, schema version, immutable configuration/asset
pin, image/video mode, maximum hands, frame-size limits and local-only requirement.
Host code selects from packaged known implementations; no module/class/URL field
may become arbitrary executable loading.

A result distinguishes success (including zero hands) from unsupported,
invalid input, initialization failure, execution failure, deadline and cancellation.
Define safe reasons; map to existing server error categories only when a server
operation actually exists. Do not equate camera permission refusal with LegoAI
authorization denial. Preserve room for future declared extensions; reject unknown
mandatory fields rather than silently weakening requirements.

## 8. Python/control-plane versus browser responsibilities

Python or deployment tooling may validate/publish non-secret configuration,
approve/pin assets and known contribution bundles, and establish real tenant,
Plugin admission and authorization facts for server-owned operations. A future
server validates submitted results as untrusted input and controls protected
effects. It does not receive raw frames merely to orchestrate local inference.

The browser owns user-mediated camera acquisition, local handles, worker lifetime,
feature detection, approved asset loading, inference, output validation and
local visualization. It can enforce the supported local composition but cannot
mint server permits or attest its own honesty.

The first static example needs no live Python control plane and no round trip per
frame. It demonstrates contract interoperability, not full distributed governance.
Do not synthesize Principal/TenantContext or admission records in JavaScript to
make it resemble an authorized Python execution.

## 9. Local-only and privacy semantics

Define raw image/video non-egress as a mandatory task constraint. Default derived
landmarks to local-only too: they may be sensitive even without pixels. Model
asset downloads are distinct from inference uploads; approve their sources before
camera use. Unknown configuration or no supported local path fails closed.

Separate five decisions: requested privacy policy; observed device/runtime
features; compatible binding selection; authorization for protected effects; and
local resource admission. None substitutes for another.

Allow WebGPU to local WASM only when explicitly permitted and qualified for that
model. Otherwise return unsupported/no-compatible-execution. Never introduce a
remote endpoint fallback. Failure after inference starts is not permission to
replay through another provider.

Use pinned self-hosted assets, restrictive deployment CSP/network rules, no upload
API, no third-party analytics, and network-negative tests. These are protections
for the shipped trusted application under its stated browser threat model, not
proof against compromised JavaScript, extensions, the OS or a malicious client.

## 10. Narrow runtime capability negotiation

Return a bounded preflight report: selected implementation/release, requested
backend, observed usable backend, unsupported reason, and whether required assets
and task settings initialize. Camera API presence, permission state and active
stream availability are distinct; do not prompt merely to populate telemetry.

For later ONNX, attempt the allowed backend with the pinned compatible model;
surface device loss or initialization failure. Do not infer free memory or usable
tensor support from navigator.gpu alone. Keep provider options private.
ONNX exposes execution-provider and WASM configuration settings; threading also
has deployment prerequisites. Choose a minimal supported setup rather than
requiring accelerated/multithreaded execution.
[ONNX session settings](https://onnxruntime.ai/docs/tutorials/web/env-flags-and-session-options.html).

No marketplace, discovery network, optimization engine or hardware taxonomy.

## 11. Model assets and Artifact semantics

Canonical ArtifactVersion meaning already covers immutable identity, version,
content interpretation and provenance independent of storage location. The absence
of its general implementation is not grounds to invent ModelArtifactRef.
ModelId alone is not a digest, asset version or reproducibility guarantee.

Initially use an adapter-local closed approved-asset descriptor: logical asset
identifier/version, SHA-256 digest, format, byte ceiling and same-origin location.
Pin SDK/WASM dependencies too. Verify all executable/model bytes needed by the
bundle before use, not just a top-level filename. Provenance records publisher,
license/source and approved build identifiers; a digest proves byte identity,
not trust or scientific accuracy.

Cache by pinned content identity; validate restored content and fail closed on
missing/corrupt assets. Cache eviction is not replacement permission.
ONNX deployment may involve separate WASM files and model external data; its
documentation also describes model caching. A future descriptor must cover
the selected bundle's actual files.
[ONNX deployment](https://onnxruntime.ai/docs/tutorials/web/deploy.html).

## 12. Browser input/output boundary

Keep MediaStream, HTMLVideoElement, ImageBitmap/frame handles, GPUBuffer, tensors,
sessions and MediaPipe task objects private to browser adapter/acquisition code.
Canonical/task configuration describes intent and constraints, not those objects.
Use an internal transferable-frame boundary only if the selected browser supports
it; frame ownership must make disposal explicit. Raw frames do not cross Python
or network boundaries under local-only policy.

For the first proof choose one hand maximum, fixed landmark ordering and 21
finite x/y/z values, plus optional handedness with declared score semantics.
Specify coordinate frame, mirroring and depth interpretation; do not treat
relative depth as calibrated metric distance or silently clamp invalid output.
Use bounded local frame sequence/timestamp attribution and no identity tracking.
Empty landmarks are a valid successful observation, not a transport failure.

Do not export world coordinates, generic tensors, bounding boxes, masks, pose or
face types unless the first consumer needs them. Visualization may consume plain
values; it must not depend on MediaPipe result classes.

## 13. Observability and evidence

A bounded local record may carry task/configuration version, implementation,
asset digest, backend, duration, allowed fallback use, safe status and reason.
No raw media, landmarks/biometric payloads, SDK dumps, Secrets or arbitrary labels
belong in telemetry. Disable network telemetry in the first proof.

Existing Observation supports correlation/configuration references, event/error
codes, latency and sizes. Map only truthful available fields if later exported;
do not invent server-issued identities or overload safe-cause text with a JSON
bag. Extra local attribution is not automatically canonical Observation.

Evidence custody currently accepts particular authoritative subjects. Do not
stuff browser claims into that Port as verified inference evidence. Observation
is diagnostic; custody records attributable facts; authoritative state belongs
to its owner. A later server may record that it received a claim, not that the
claimed inference or privacy guarantee is proven.

## 14. Security and trust boundary

Treat browser code/results as untrusted at any server boundary. Server-side
authorization cannot rely on reported local policy, model identity, landmark
confidence or claimed execution success. Camera permission is controlled by the
user/browser and does not confer broader LegoAI permissions.

Dependencies and assets are supply-chain inputs: require pinned builds, integrity
checks and restricted origins; no latest CDN scripts or arbitrary asset URLs.
Cache contents are mutable/unavailable client state, not trusted publication.
Use no credentials in the proof. Browser attestation, trusted execution and
malicious-client proof of non-egress are explicitly unsolved.

Known/admitted compatible contributions remain the rule for a later managed
integration. Static approved build composition in this isolated proof is not
represented as complete implementation of server Plugin lifecycle/admission.

## 15. Offline implications

No foundational contract blocks offline inference. A future installed/cached
example must have static code, WASM and exact model assets available locally;
first-load network availability and subsequent offline availability are different
claims. Missing assets yield explicit unavailable status, never cloud inference.

Do not persist camera frames or sensitive outputs for later sync. Bounded
diagnostics may be dropped. Deferred telemetry, cache upgrade/revocation,
offline authority leases and reconciliation are separate later requirements.
No service worker or synchronization subsystem is required merely for this
assessment; the future milestone must state its actual offline support.

## 16. Package/dependency recommendation

Keep Python canonical contracts in existing owners. Recommend an isolated future
browser adapter package under packages/ with its own build/lock and contract
fixtures, and a static consumer under examples/. Names are provisional; exports
must be limited to the hand task. No dependency from Python core to npm packages.
AirTouch business behavior belongs in an application package/repository.

Host wiring imports the browser adapter; the adapter privately imports MediaPipe.
A future ONNX adapter privately imports ONNX Runtime Web. Domain code consumes
task values, never session/task/tensor objects. Language-neutral schemas and
golden valid/invalid vectors are interoperability artifacts, not a TypeScript
Kernel port. Add Python validation only for a real consuming boundary.

## 17. Explicit non-goals / NOT NOW

Defer complete CV ontology, segmentation/object-detection/pose frameworks,
VLM multimodal ModelPort expansion, TensorRT, ComfyUI, COLMAP, Gaussian Splatting,
Three.js and WebRTC abstractions, browser Agents, browser Plugin ecosystem,
duplicated governance, cloud/edge scheduling, distributed model registries,
training, fine-tuning, conversion services, semantic caching, GPU fleet scheduling
and Kubernetes. Also defer Face/Pose tasks, gestures, DOM actions, AirTouch SDK,
remote config/storage, broad provider negotiation and authenticated inference.

ONNX receives this boundary assessment only; do not implement it alongside the
first MediaPipe proof or describe it as a compatible second provider without
task/model evidence.

## 18. Exact next vertical implementation milestone

Propose: Browser Hand-Landmark Local Inference Vertical Slice.

A static example captures explicitly user-enabled camera frames, passes bounded
local frames to one MediaPipe adapter, validates plain hand results and renders
a local overlay. No server inference, Agent, LLM, gesture interpretation or DOM
automation. Before coding, pin one supported browser/SDK/model tuple and document
its license/digest and worker compatibility.

Acceptance gates:
1. Contract vectors reject unknown versions, non-finite numbers and oversized
   requests/results; a fake adapter substitutes without domain-code changes.
2. Pin one in-flight inference and no unbounded frame queue; drop superseded
   frames. Bound resolution, session duration and accepted output size.
3. Worker cancellation stops acceptance, discards late output and requests cleanup;
   terminate/recreate the worker when needed. Report whether completion/cleanup
   was observed; never claim hard GPU interruption or deadline enforcement merely
   because a Promise timed out. Stop camera tracks separately.
4. Test denied camera permission, no supported runtime, unavailable/corrupt assets,
   initialization failure, device loss where applicable, timeout, cancellation,
   repeated start/stop and unsupported fallback with no remote request.
5. Contract tests may be deterministic; real inference uses declared tolerances
   and representative licensed fixtures. Do not require cross-backend bit equality.
6. Network tests verify no raw/derived media egress, including error paths.
   Diagnostics remain bounded and media-free.
7. Record actual backend/model/configuration attribution and explicit limits.
   Static asset hosting or configuration export demonstrates Python coexistence
   without claiming distributed governance.
8. Static and behavioral tests pass before widening to a second task/provider.

A minimal future ONNX adapter would load a verified model bundle, validate its
fixed input/output shapes and dtypes privately, select only qualified local
backends, convert outputs into the consumer's task values and implement the same
truthful cleanup/failure boundaries. No ONNX model conversion project is implied.

## 19. Risks, open questions and static design challenge

Resolve before implementation: exact supported browser/version and worker/media
path; approved model/SDK license and digests; coordinate/mirroring conventions;
safe frame limits and measured latency; backend-specific disposal behavior;
and the precise offline claim. No API currently proves universal GPU memory
availability or hostile-browser privacy.

Static review answers: no second LegoAI runtime; no browser objects in Python
canonical APIs; no inference-runtime-as-Model classification; no SDK types in
consumer values; no speculative CV ontology; no duplicated Artifact/Resource
owners; no authorization from selection; no remote fallback; no trusted browser
claims; no unused infrastructure. The separate local task schema and static
approval boundary are intentional limitations, not hidden general platform claims.

## 20. Go / No-Go and completion boundary

GO for the specified separately authorized MediaPipe implementation, with its
acceptance gates. NO-GO for claiming full governed browser execution, arbitrary
ONNX/MediaPipe substitution, strong hostile-client privacy attestation, or
production qualification based on this assessment.

No unfinished prior runtime work must be completed solely to assess or build this
isolated proof. Preserve prior open items and qualification limits; do not label
M8.3 validated based on source inspection. This task changes only this assessment
document. No runtime code, dependency, canonical contract or browser experiment
was added. Implementation must wait for the next instruction.
