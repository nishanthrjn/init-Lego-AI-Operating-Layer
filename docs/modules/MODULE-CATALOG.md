# LegoAI Module Catalog

This is a human-readable index of LegoAI's **real** modules and their current,
evidenced status. It is **not** a machine-readable registry, runtime Capability
Catalog, Plugin registry, manifest or dependency-injection configuration.
Nothing reads this file at runtime.

Last reconciled: 2026-09-29 (CR-4). To assemble an application from these
modules, read [Assembling applications](../ASSEMBLING-APPLICATIONS.md).

## Maturity labels

This catalog uses only these labels, defined in the
[consumer-readiness plan](../../planning/LEGOAI-CONSUMER-READINESS-PLAN.md) §8.
Each label is backed by the linked evidence.

| Label | Meaning |
| --- | --- |
| **implemented** | Code merged; validation pending or not recorded |
| **deterministically qualified** | Offline or fake tests passed locally for the stated scope |
| **live-qualified** | A real provider or tool was exercised locally for the stated scope |
| **experimental** | Partial or pending evidence for part of the scope |
| **deferred** | Planned, not present. Listed only in [Deferred and planned](#deferred-and-planned) |

**How to read qualification:**
- **Locally** means the maintainer's reference machine (Windows) unless the
  evidence says otherwise.
- **Replay-model** qualification proves the architecture and flow, not model
  quality.
- **Docker** qualification is limited to Windows with the Docker Desktop Linux
  engine.
- A **sandbox** gives containment, not result integrity.
- **Local host grants** are volatile, single-operator authority, not durable
  IAM.

## Core runtime (`legoai` / `legoai-reference`)

| Module | Real purpose | Supported public API | Typical uses | Configurable variation | Adapters / providers | Qualification | Important limitations | Consumer guide / evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Public local governed host (ADR-014) | Opens one single-operator governed host: Catalog, resolution, authorization, dispatch, execution contexts | `legoai.runtime.api` (config values, `GovernedHost`, `HostError`, `ModelPurpose`) and `legoai.runtime.local.open_local_host` | Any application making governed model calls; source of `SecurityContext` / `AuthorizationPort` for effect wrappers | Principal, policy, grants (`OperatorGrant`), model bindings and selection, capacity | Ollama (built-in settings); trusted `ModelPort` contributions | deterministically qualified (CR-1b, local) | In-memory, process-lifetime state; volatile local grants, not IAM; one pinned binding per host; thread- and event-loop-confined | [ADR-014](../../adrs/ADR-014.md) §12a |
| Model contract and routing (M6.5, ADR-019) | Provider-neutral chat and embedding; logical profile → configured binding; configuration-selected composition | `legoai.intelligence.model` values and Ports (`ModelPort`, `ModelRequirement`); selection through the public host | Chat, embeddings, profile-based routing | Binding among admitted contributions, selected by data | Ollama; offline fakes | Routing and selection: deterministically qualified. Ollama: live-qualified for the v0.1 DocuMind scope | No token or cost bounds; no credentialed providers; selection internals are private | [model-routing](../model-routing.md), [model-composition](../model-composition.md), [v0.1 readiness](../../planning/V0.1-RELEASE-READINESS.md) |
| One-step Agent runtime (M7) | Governed single Chat step with bounded, validated output | `legoai.execution.agent` (`AgentDefinition`, `AgentRuntimePort`, `AgentRequest`, `AgentResult`); runtime obtained from `GovernedHost.agent_runtime()` | Structured single-call reasoning Agents | Via model routing | The host's governed Chat | deterministically qualified (local) | One step: no tools, memory, retries or multi-turn | [agent](../agent.md) |
| Governance values and Ports | Authority facts and the current-authorization seam used at effect boundaries | `legoai.governance.ports` (`SecurityContext`, `AuthorizationPort`), `legoai.governance.values` | Passing host-issued contexts to authorized wrappers | Grants via the host configuration | The host's reference evaluator (private) | deterministically qualified (Core suite, CR-1b, CR-3) | Applications must not construct `Grant` or `SecurityContext`; approvals are unsupported by engineering wrappers | [ADR-014](../../adrs/ADR-014.md), [ADR-018](../../adrs/ADR-018.md) |

## Engineering (`legoai-engineering`)

Full public-import table and semantics:
[engineering CONSUMING.md](../../packages/legoai-engineering/docs/CONSUMING.md).
Milestone evidence is in the
[engineering README](../../packages/legoai-engineering/README.md).

| Module | Real purpose | Supported public API | Typical uses | Configurable variation | Adapters / providers | Qualification | Important limitations | Consumer guide / evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Repository inspection and workspace (M1–M2) | Bounded read-only repository access | `repository.workspace`, `repository.ports` (`RepositoryWorkspacePort`), `repository.local` | Reading files for tools and Agents | `WorkspacePolicy` (sizes, depth, exclusions) | Local filesystem | live-qualified (local Windows, real filesystem) | Assumes a trusted, stable namespace; no atomic snapshot | [CONSUMING.md](../../packages/legoai-engineering/docs/CONSUMING.md) |
| Git observation (M3) | Read-only HEAD and status | `git.ports` (`GitRepositoryPort`), `git.local` | Operator-facing repository state | `GitReadPolicy` | Local Git executable | live-qualified (local, real Git) | Read-only; no commits; not authorized for model disclosure | [CONSUMING.md](../../packages/legoai-engineering/docs/CONSUMING.md), [engineering README](../../packages/legoai-engineering/README.md) |
| Repository mutation (M4) | Digest-guarded create and update | `repository.mutation`, `mutation_ports`, `mutation_local`, `mutation_errors` | Applying proposed changes | `WorkspacePolicy` | Local filesystem | live-qualified (local) | No multi-file transaction or rollback; partial effects are reported | [CONSUMING.md](../../packages/legoai-engineering/docs/CONSUMING.md), [engineering README](../../packages/legoai-engineering/README.md) |
| Host engineering checks (M5) | Fixed pytest, Ruff and mypy runs | `checks.ports` (`EngineeringCheckPort`), `checks.local` | Checking **trusted** code | Tool paths, `CheckPolicy` | Host processes | live-qualified (local), **trusted code only** | No isolation: code runs as the host user | [CONSUMING.md](../../packages/legoai-engineering/docs/CONSUMING.md), [engineering README](../../packages/legoai-engineering/README.md) |
| Sandbox (M6, CR-2a) | Contains untrusted Python workloads | `sandbox.ports` (`SandboxExecutionPort`), `sandbox.docker` (`DockerSandbox`, closed `SandboxImage` set) | Running model- or repository-controlled code | `SandboxPolicy` within ceilings; image from the closed set | Docker Desktop Linux engine | live-qualified (Windows + Docker Desktop; CR-2a `PYTHON_CHECKS` image Docker-qualified) | Windows only; fixed 1 CPU / 128 MiB / 32 PIDs; containment is not result integrity | [CONSUMING.md](../../packages/legoai-engineering/docs/CONSUMING.md), [engineering README](../../packages/legoai-engineering/README.md) |
| Sandboxed engineering checks (CR-2b) | `EngineeringCheckPort` over the sandbox | `checks.sandboxed` (`SandboxedEngineeringChecks`, `CheckInputPolicy`) | Checking model-written code | `CheckInputPolicy`, `CheckPolicy` | `SandboxExecutionPort` (Docker) | live-qualified (Windows + Docker Desktop) | No host fallback; results don't record which inputs were checked; a pass is a contained observation, not correctness | [CONSUMING.md](../../packages/legoai-engineering/docs/CONSUMING.md), [engineering README](../../packages/legoai-engineering/README.md) |
| Authorized effect wiring (CR-3) | Current authorization immediately before reads, writes and checks | `analyst.authorized`, `coding.authorized`, `repository.mutation_authorized`, `checks.authorized`, `authorization` | Governed engineering applications | Fixed actions; grants from the host | Wraps the adapters above | deterministically qualified (CR-3 validator, including one real-Docker phase) | One workspace per wrapper; approval-bearing contexts refused; needs the `analyst` extra (Core) | [CONSUMING.md](../../packages/legoai-engineering/docs/CONSUMING.md), [engineering README](../../packages/legoai-engineering/README.md) |
| Repository Analyst (M8.1) | Analyzes **supplied** files; returns cited findings | `analyst.api` (`RepositoryAnalyst`), `analyst.values` | Repository Q&A over named files | Via Core routing | Governed Chat | deterministically qualified (fake model) | Cannot discover files; one call; narrative is unverified | [CONSUMING.md](../../packages/legoai-engineering/docs/CONSUMING.md), [engineering README](../../packages/legoai-engineering/README.md); [M8.1 plan](../../planning/M8.1-REPOSITORY-ANALYST-PLAN.md) |
| Independent Reviewer (M8.2) | Bounded review opinion over supplied text | `reviewer.api` (`IndependentReviewer`), `reviewer.values` | Quality gate after deterministic checks | Criteria supplied by the caller | Governed Chat | deterministically qualified (fake model) | `ACCEPT` is an unverified model opinion; independence is by Agent definition only | [CONSUMING.md](../../packages/legoai-engineering/docs/CONSUMING.md), [engineering README](../../packages/legoai-engineering/README.md); [M8.2 plan](../../planning/M8.2-INDEPENDENT-REVIEWER-PLAN.md) |
| Coding Agent (M8.3) | Proposes an M4 change set over authorized current content | `coding.api` (`CodingAgent`), `coding.values` | Code change proposals | Via Core routing | Governed Chat | deterministically qualified (fake model) | Proposes only (never applies or executes); ≤8 files, 8 KiB each | [CONSUMING.md](../../packages/legoai-engineering/docs/CONSUMING.md), [engineering README](../../packages/legoai-engineering/README.md); [M8.3 plan](../../planning/M8.3-BOUNDED-CODING-PLAN.md) |

## Other packs

| Module | Real purpose | Supported public API | Typical uses | Configurable variation | Adapters / providers | Qualification | Important limitations | Consumer guide / evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Document pack (`legoai-document`) | Document parsing, chunking, embedding, ingestion, retrieval (SQLite store), rerank and cited answering; model calls go through **injected** governed embed and chat callables | Package subpackages `parsing`, `chunking`, `embedding`, `ingestion`, `retrieval`, `rerank`, `answering` (their `api`/`values` modules) | Document Q&A applications | Chunking and retrieval parameters; the governed callables supplied by the application | `pypdf` (parsing, internal); SQLite retrieval store; models via Core | live-qualified within the v0.1 DocuMind scope (local Ollama) | No OCR; complex PDF layouts uncharacterized. The package README's "Current capabilities" section lists only parsing and chunking and predates the other subpackages | [v0.1 plan](../../planning/V0.1-DOCUMIND-IMPLEMENTATION-PLAN.md), [v0.1 readiness](../../planning/V0.1-RELEASE-READINESS.md), [package README](../../packages/legoai-document/README.md) |
| Generative media (`legoai-generative-media`) | Governed text-to-image, image transfer and virtual try-on over ComfyUI | `service.open_text_to_image`, `service.open_image_transfer`, `service.open_virtual_try_on`, plus Ports and values | Image generation applications | Provider/driver (`api_family`), `env:NAME` secrets, completion policy | Local ComfyUI (legacy API); Comfy API v2 | Text-to-image: live-qualified (local ComfyUI, maintainer-run). Provider compatibility: local validated; Cloud generation unqualified. Image transfer and try-on: deterministically qualified; try-on live qualification deferred (no CUDA runtime) | **M-01 migration pending maintainer validation:** composition now consumes the ADR-026 public governed execution facade; H-01 remains OPEN, ADR-027 Proposed, credentialed media unqualified and remote VTO unsupported; ComfyUI is operator-managed | [package README](../../packages/legoai-generative-media/README.md), [text-to-image](../../planning/COMFYUI-TEXT-TO-IMAGE-VERTICAL-SLICE.md), [provider compatibility](../../planning/COMFYUI-PROVIDER-COMPATIBILITY-SLICE.md), [VTO-2](../../planning/VIRTUAL-TRY-ON-VTO2.md), [VTO-3](../../planning/VIRTUAL-TRY-ON-VTO3.md) |
| Collation (`legoai-collation`) | Pure source-attributed precedence collation of one field | Package API | Reconciling multi-source field values | Pure inputs and policy | none | deterministically qualified (pack validation, assistant-run record) | Single field; no I/O, entity resolution or authorization | [package README](../../packages/legoai-collation/README.md), [F1 record](../../planning/COLLATION-F1-SLICE.md) |
| Browser hand landmarks (TypeScript, `legoai-browser-hand-landmarks`) | In-browser hand landmark detection | Package exports, `HandConfig` | Gesture interfaces | `maxHands` 1–2 | MediaPipe worker | One hand: live-qualified per user-reported automated and manual validation (package README). Two hands: experimental, needs fresh validation. The slice record still reads "local validation pending" | Browser-only; not Python; separate from Core | [package README](../../packages/legoai-browser-hand-landmarks/README.md), [slice record](../../planning/BROWSER-HAND-LANDMARK-VERTICAL-SLICE.md) |

## Consumer applications (examples, not reusable modules)

These are applications built **on** LegoAI. They are evidence for the assembly
model, not LegoAI modules to depend on.

| Application | What it demonstrates | Qualification | Important limitations | Evidence |
| --- | --- | --- | --- | --- |
| DocuMind (`examples/documind`) | Governed document Q&A: the public host, governed chat and embed, and the document pack | live-qualified for the v0.1 scope with local Ollama; migrated to the public host in CR-1b | v0.1 scope; single operator | [README](../../examples/documind/README.md), [v0.1 readiness](../../planning/V0.1-RELEASE-READINESS.md), [ADR-014](../../adrs/ADR-014.md) §12a |
| ForgeAI (`examples/forgeai`) | Reviewed repository task worker with one bounded rework, assembled from public LegoAI APIs with **no LegoAI platform change** (ForgeAI-1/2/3) | ForgeAI-1/2/3 deterministically qualified with **replay models** and **real Docker** checks (Windows + Docker Desktop); live-model quality **unqualified** | Operator-supplied targets; at most 4 model calls, 2 applies, 2 check batches and 2 reviews; no rollback, Workflow or Team | [README](../../examples/forgeai/README.md) |

## Deferred and planned

These are **not implemented**. Nothing here is available to consumers.

| Capability | Label | Status and reason | Record |
| --- | --- | --- | --- |
| M8.4 Test/Validation Agent | deferred | Validation assessment overlaps `IndependentReviewer`; test-change proposal overlaps `CodingAgent`; execution overlaps checks and sandbox. Only test-gap analysis has distinct semantics, and no consumer or evidence justifies it yet | [direction assessment](../../planning/FORGEAI-4-AND-M8.4-DIRECTION.md) §7 |
| Workflow abstraction | deferred | Not justified: all observed coordination is ForgeAI-owned (Rule of Two not met) | [direction assessment](../../planning/FORGEAI-4-AND-M8.4-DIRECTION.md) §11 |
| Team abstraction | deferred | Not justified: two Agent definitions under one principal; no roles or delegation | [direction assessment](../../planning/FORGEAI-4-AND-M8.4-DIRECTION.md) §11 |
| Target discovery (a future M8.5) | deferred | Needs a paths-only structure-disclosure decision (ADR) first, and operator confirmation of model-proposed targets | [direction assessment](../../planning/FORGEAI-4-AND-M8.4-DIRECTION.md) §9 |
| ForgeAI-LQ1 live-model evaluation | deferred (planned next code slice) | Measurement harness with hidden acceptance tests; not a quality claim | [direction assessment](../../planning/FORGEAI-4-AND-M8.4-DIRECTION.md) §§12, 14 |
| CR-1c generative-media host migration | deferred | Move generative media onto the ADR-014 public host | [readiness plan](../../planning/LEGOAI-CONSUMER-READINESS-PLAN.md) §14 |

## Per-module consumer documentation standard

Each consumer-ready module documents itself with the 18 fixed headings
defined in the [readiness plan §9](../../planning/LEGOAI-CONSUMER-READINESS-PLAN.md).
The reference example is
[engineering CONSUMING.md](../../packages/legoai-engineering/docs/CONSUMING.md).

| # | Heading | # | Heading |
| --- | --- | --- | --- |
| 1 | Purpose | 10 | Adapter/provider replacement path |
| 2 | Real-world use cases | 11 | Security/governance boundary |
| 3 | Non-use cases | 12 | Effect and failure semantics |
| 4 | Supported public imports | 13 | Concurrency and resource behavior |
| 5 | Application-facing contract | 14 | Examples (public imports only) |
| 6 | Configuration surface | 15 | Validation/tests |
| 7 | Runtime inputs vs operator configuration | 16 | Qualification scope |
| 8 | Supported adapters/providers | 17 | Known limitations |
| 9 | Extension path | 18 | Compatibility/version expectations |

**Rule:** a guide must never show a private import. If a capability still
needs one, the guide says the module is not yet consumer-ready and links the
blocking slice. This is human documentation, not a schema.
