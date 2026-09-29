# LegoAI consumer-readiness plan and ForgeAI-1 prerequisites

**Date:** 2026-09-28
**Status:** PLAN ONLY. No source, test, dependency, ADR or public API change.
**Inspected at:** branch `br-LegoAI-PyLLM-ComfyUI-CustomerRec`, HEAD `2b633b1`.
**Primary consumer evidence:** [FORGEAI-REUSE-GAP-ASSESSMENT.md](FORGEAI-REUSE-GAP-ASSESSMENT.md).
**Authority read:** ADR-002 §§4, 11–12 (runtime facade, public/private rule);
ADR-INDEX (ADR-014 unallocated); IMPLEMENTATION-READINESS §4 (ADR-014 route),
Gate 3 and §12; `docs/model-composition.md` (ADR-019); package READMEs; the
executable modules cited below.

---

## 1. Executive summary

LegoAI's capabilities are **reusable inside the repository but mostly not yet
consumer-ready**. The gap is in the *assembly layer*, not in capability semantics.

- **B1 is confirmed and broader than the ForgeAI-0 statement.** No application can
  obtain a governed model or Agent path without importing internals. There are
  three hand-written copies of the same "local governed host" wiring:
  - `examples/documind/src/documind_app/composition.py`;
  - `packages/legoai-generative-media/src/legoai_generative_media/local_host.py`, which is production package code;
  - `packages/legoai-engineering/examples/governed_demo.py`.

  All three import `legoai.reference.*` realizations, which ADR-002 §11 makes
  internal, and two also import `legoai.runtime._composition.*`. Each one builds
  its own in-memory Catalog, authorization, arbiter and Coordinator, and issues
  its own Grants in code.

  ADR-002 §12 already reserves a public `legoai.runtime.api` facade but leaves
  "actual factories, instance lifetime, bootstrap order, config loading" undecided.
  **ADR-014 is exactly that missing decision.** Scoped narrowly, it should
  standardize one public, config-driven *local governed host* entry point. Three
  existing consumers satisfy the Rule of Two before ForgeAI counts.
- **B2 is confirmed and larger than "one adapter".** `EngineeringCheckPort` is the
  right interface, and M6 is the right isolation owner. However:
  - `DockerSandboxConfig` accepts exactly **one** pinned stdlib-only image, which contains no pytest, Ruff or mypy.
  - The per-container memory limit is a fixed 128 MiB, unmeasured for mypy.
  - Inputs are capped at 64 text files.
  - `CheckFailure` cannot express cancellation or resource exhaustion.

  B2 therefore needs a qualified toolchain image profile (an M6 extension) *and* the adapter.
- **Authorized wrappers:** keep two (mutation apply, check execution) as decorators
  implementing the *existing* Ports. Drop the Git-inspection wrapper for now.
- **Documentation:** a human-facing Module Catalog, a per-module consumer template
  and an application-assembly guide are needed. None of them may introduce a registry.

**Decision:** **FORGEAI-1 READY AFTER M8.3-closure + CR-1 + CR-2 + CR-3** (§18).
**Status (2026-09-29):** all prerequisites are complete and locally qualified. **FORGEAI-1 READY.**

## 2. Why ForgeAI exposed platform reuse gaps

ForgeAI is the first consumer that needs *several* LegoAI owners at once: a
governed Agent, authorized reads, mutation, checks, isolation and Git. Earlier
consumers each needed one path, and each solved assembly locally by copying
reference wiring. That was tolerable for single-purpose slices. ForgeAI would
have been the fourth copy, and Gate 3 forbids it. The evidence also shows a quiet
governance smell: every copy *self-issues* `Grant` objects in application code.
Authority is therefore created by the consumer instead of being supplied as
explicit operator configuration.

## 3. Current reusable-platform maturity

Consumer-ready standard (§17), scored from repository evidence. "Partial" means
the property exists but is undocumented or reachable only through internals.

| Area | 1 Public imports only | 2 Config variation | 3 Adapter swap | 4 Documented wiring | 5 Effects documented | 6 Fakes | 7 Example | 8 Qualification stated |
|---|---|---|---|---|---|---|---|---|
| Core governed runtime (Catalog, governance, Coordinator) | **No** (`reference.*`, `_composition`) | No | Yes (Ports) | **No** | Yes | Test-only (`tests/support`) | Private | Yes |
| Model (ModelPort, Ollama, routing, ADR-019 selection) | **No** for selection/governed use | Partial (ADR-019, private) | Yes | Partial | Yes | Example-only | Private | Yes |
| Agent (M7) | Contracts yes; runtime **no** | Via routing | Yes | Partial | Yes | Example-only | Private wiring | Yes |
| Engineering M1–M6 | Yes for Ports/values/local adapters | Typed values, no capture | Yes | Monolithic log | Yes | None shipped | Yes | Yes |
| Engineering M8.x Agents | Partial (`_composition` modules) | Via Core | Yes | Log | Yes | Example-only | Uses private wiring | M8.3 pending |
| Document pack | Yes (contracts) | Via DocuMind | Yes | README | Yes | — | DocuMind | v0.1 |
| Generative media | `service.open_*` public, but **package internals import `reference.*`** | **Yes** (driver, `env:NAME` Secret refs) | Closed driver set | Yes | Yes | Transport injection | Yes | Mixed (§9) |
| Collation | Yes | n/a (pure) | n/a | Yes | Yes (pure) | n/a | Yes | Yes |
| Browser hand landmarks (TS) | Yes (package) | `HandConfig` | Worker adapter | Yes | Yes | — | Yes | 1-hand yes, 2-hand pending |

Generative media's `service.open_text_to_image(config)` shape is the repo's most
consumer-ready pattern. It takes validated config and returns governed Ports, with
provider selection by data. B1 generalizes this shape rather than inventing another.

## 4. B1 — public composition boundary

### 4.1 Verified current state

| Fact | Evidence |
|---|---|
| `legoai.runtime` exports nothing; `runtime/__init__.py` is inert, and there is **no `runtime/api.py`** | source |
| Private composition surface: `direct.compose_direct`, `governed.invoke_governed_text_normalization`, `model_governed.invoke_governed_chat/embedding/invoke_routed_chat/ConfiguredModelBinding`, `model_selection.capture_model_selection/compose_model/ModelContribution`, `agent.GovernedAgentChat` | `src/legoai/runtime/_composition/*` |
| ADR-002 §11: "all `legoai.reference.*`, `_composition`… are internal"; public = Kernel, owner `values`/`ports`, Plugin `spi`, thin `runtime.api` | ADR-002 L412 |
| ADR-002 §12: public `legoai.runtime.api` is a thin facade over injected contracts; "factories, lifetime, bootstrap order, config loading and authorization are later mechanism decisions" | ADR-002 L424–426 |
| Readiness §4: ADR-002 "does not authorize a public alias for private wiring"; route is ADR-014 | IMPLEMENTATION-READINESS L130–132 |
| There is no public Port for the Coordinator (`ExecutionCoordinator` is a reference class); public Ports exist for `DispatchArbiterPort`, `SecurityContextResolutionPort` and `AuthorizationPort` | `execution/ports.py`, `governance/ports.py` |
| DocuMind imports 8 `reference.*` names plus `_composition.model_governed` and self-issues Grants | `documind_app/composition.py` |
| Generative media's production code imports `reference.execution/resolution/catalog/governance/plugins/evidence` and self-issues Grants in `prepare_local` | `local_host.py`, `composition.py` |
| Engineering examples import `reference.*` and `_composition.agent/model_governed`, plus engineering `analyst._composition` / `coding._composition` | `examples/governed_demo.py`, `bounded_coding.py` |

### 4.2 Recommended shape (repo-consistent)

A single-operator **local governed host**, opened from validated configuration.
The name follows existing vocabulary: generative-media's "reference local host"
and `open_*` entry functions, and ADR-002's `runtime.api` facade. It is not an
ApplicationRuntime, Builder, DI container or service locator.

**Public imports (new, versioned):**

| Module | Content |
|---|---|
| `legoai.runtime.api` | Public *types only*, per ADR-002: `LocalHostConfig` (tenant id, principal, policy ref, **explicit operator grants** as data: action, resource scope, lifetime), `HostContribution` (trusted declaration plus constructor; code, never data), `GovernedHost` Protocol, `HostOpenError(reason)` |
| `legoai.runtime.local` | **Public entry function** `open_local_host(config, contributions, *, clock) -> GovernedHost`. This is the one sanctioned public module allowed to import `_composition` and `reference.*` (the ADR-014 decision point; see §5) |

**`GovernedHost` returns only public contracts (smallest set used by current consumers):**

| Member | Returns | Needed by |
|---|---|---|
| `new_execution(operation, *, deadline=None, causation=None)` | `ExecutionContext` with a registered security context for a configured grant | all |
| `agent_runtime(binding_selection)` | `AgentRuntimePort` (M7 over the ADR-019 selected binding) | engineering Agents, ForgeAI |
| `governed_chat(context, request)` / `governed_embed(context, request)` | `(ExecutionResult, ChatResult \| None)` etc., unchanged semantics | DocuMind |
| `authorization` | `AuthorizationPort` | engineering authorized wrappers |
| `security_context(context, action, resource_scope)` | `SecurityContext` bound to configured grants | engineering authorized wrappers |

Generative media's `Contribution` invoke path can be added in a later member
(CR-1c). It is not required for ForgeAI-1, and no unused members are added speculatively.

**Stays private:** every `legoai.reference.*` class, the `_composition` functions,
`ConfiguredModelBinding`, the Coordinator, in-memory registries and plugin
lifecycle helpers. Consumers never receive a concrete reference instance.

**Initialization inputs:** `LocalHostConfig` (validated data; rejects
import/class/Secret-value fields, as ADR-019 does); trusted `HostContribution`
tuple (operator code); ADR-019 model-selection data plus pinned
`ConfigurationRevisionRef`; clock.

**Lifecycle:** `open_local_host` performs inert admission, activation and Catalog
publication. It does **no provider I/O**, which matches DocuMind today. The
host is an explicit value with no global singleton, and one host is independent
of another. It owns no background work, so no shutdown API is added until ADR-015
supervision is in scope. Per-run state lives in `ExecutionContext`, never in the host.

**Failure semantics:** open-time problems raise `HostOpenError` with closed
reasons (reuse ADR-019 `CompositionFailure` categories plus `INVALID_CONFIG`,
`GRANT_SCOPE`). Invocation keeps existing semantics: `ExecutionResult` / `AgentResult`
with NONE/UNKNOWN effects, no retries, and cancellation propagates. Denial happens
before any provider call.

**Governance honesty:** grants remain in-memory, single-operator local authority,
now *declared in operator config* instead of constructed in app code. This is not
IAM, multi-tenant isolation or durable authority.

### 4.3 Test strategy

- Clean-install test: a fresh venv using only `legoai.runtime.api/local` plus
  owner `values`/`ports` runs the Agent and chat examples offline.
- Architecture: consumers (examples, DocuMind, engineering examples) import no
  `legoai.reference.*` and no `_composition`. The generative-media exception is
  listed until CR-1c.
- Substitution: fake-model contribution ↔ Ollama with mocked transport, with the
  same consumer code (extends the existing ADR-019 tests).
- Governance negatives: no configured grant → denied, zero provider calls;
  expired grant; wrong tenant; approval-bearing context fails closed.
- Pinning: a stale revision is rejected, with no latest-revision substitution.
- Isolation: two hosts and two executions share no state.

### 4.4 Migration

1. Engineering `examples/governed_demo.py` → `open_local_host` (first proof).
2. DocuMind `composition.py` → `open_local_host`. Behavior is unchanged; its
   hard-coded grant becomes operator config (second proof).
3. CR-1c (not ForgeAI-blocking): generative-media `local_host.prepare_local` →
   public host member. Until then it remains a recorded, test-listed exception.
4. Existing `_composition` code stays private and becomes the facade's implementation.

## 5. ADR-014 proposal

**Status update (2026-09-28): CR-1a COMPLETE. ADR-014 ACCEPTED. CR-1b COMPLETE —
LOCALLY QUALIFIED (offline, deterministic).**
[ADR-014 — Public local governed host composition boundary](../adrs/ADR-014.md)
was accepted by the maintainer, and its §13 decisions are resolved. CR-1b adds
`legoai.runtime.api`/`legoai.runtime.local` and migrates two existing consumers,
the engineering Agent examples and DocuMind, with no private imports. All 20
validator phases passed; see ADR-014 §12a for the evidence. B1 is closed for these
consumers; generative media remains a listed exception until CR-1c.
**M8.3 closure is COMPLETE (2026-09-29):** it passed in a symlink-capable session
with all six symlink boundary tests passing; see the
[M8.3 completion report](M8.3-BOUNDED-CODING-PLAN.md#completion-report).
**CR-2a COMPLETE — LOCALLY DOCKER-QUALIFIED (2026-09-29):**
- All 20 validator phases passed.
- `SandboxImage.PYTHON_CHECKS` is bound to the qualified local image ID
  `sha256:4c64580306983d70e059f5f133f6bb3f82657c9c61fa96f562f42594f20269df`.
- The unchanged 128 MiB profile fits the qualified small fixture. Measured
  whole-container peaks: mypy about 69 MB, pytest 40–66 MB, Ruff about 10 MB,
  with no OOM kills.
- Memory exhaustion is reported as `RESOURCE_LIMIT`.
- See the engineering README "CR-2a qualification evidence". The §6.3 items on the
  closed image set and the fixed resource profile are closed.

**CR-2b COMPLETE — LOCALLY DOCKER-QUALIFIED (2026-09-29):**
- `SandboxedEngineeringChecks` realizes the unchanged `EngineeringCheckPort`
  over `RepositoryWorkspacePort` and `SandboxExecutionPort`.
- Host and sandbox share one private command table.
- `CheckInputPolicy` is bounded.
- The adapter adds four sandbox-only `CheckFailure` members.
- There is no host fallback.
- All 20 phases of `validate_consumer_readiness_cr2b.py` passed against the
  recorded CR-2a image. See the engineering README "CR-2b qualification evidence".
- A sandboxed pass is contained, not proven correct.
- Input identity is deferred to CR-3 or ForgeAI-1.

**CR-3 COMPLETE — LOCALLY QUALIFIED (2026-09-29):**
- `AuthorizedRepositoryMutation` and `AuthorizedEngineeringChecks` decorate the
  unchanged Ports with per-effect current authorization.
- One private helper is shared with the read composition.
- The read composition is public (`analyst.authorized`, `coding.authorized`).
- ADR-018 has an addendum, and `docs/CONSUMING.md` is written.
- All 20 phases of `validate_consumer_readiness_cr3.py` passed, including the
  real-Docker authorized sandboxed check, the clean-install consumer proof and
  the structural readiness proof. See the engineering README "CR-3
  qualification evidence".

**FORGEAI-1 READY.** No new blocker was found. The known limitations carried
into ForgeAI-1 are in `docs/CONSUMING.md` §17: no checked-input identity, one
workspace per wrapper, unsupported approvals, and operator-only Git.

Where the ADR differs
from the sketch in this section and §4.2, the ADR is authoritative:
- `model_execution(purpose)` replaces a generic `new_execution`;
- `agent_runtime()` takes no argument;
- a closed built-in provider set is paired with trusted code contributions;
- a hard execution capacity is added;
- event-loop confinement is added.

The original scoping text follows.

- **Decision question:** How does an application obtain supported governed LegoAI
  capabilities through a public, versioned entry point, without importing
  reference realizations or private composition, while preserving revision
  pinning, resolution, authorization, execution context and adapter replacement?
- **Current problem:** §4.1. There are three duplicated wirings, private-import
  dependence and consumer-issued grants. Gate 3 items 2 and 4 are unmet.
- **Alternatives:**
  - (a) Keep private and document pinned exceptions.
  - (b) Declare `legoai.reference.*` public.
  - (c) Builder/fluent API.
  - (d) Declarative manifest loader.
  - (e) Direct Python entry function plus public Protocol over injected contracts (**recommended**).
- **Why (e):** it matches readiness §4's "Direct Python API" candidate, ADR-002 §12's
  thin facade and generative-media's proven `open_*(config)` pattern. It adds no
  loader or expression language (d). It doesn't freeze reference internals (b). It
  adds no fluent layer (c), and it removes permanent private coupling (a).
- **Public/private boundary:** §4.2. ADR-014 must explicitly authorize **one** public
  module (`legoai.runtime.local`) to depend on `_composition` and `reference.*`. This
  is a narrow amendment to ADR-002 §9's dependency table, while `runtime.api` stays
  contract-only.
- **Out of scope:** DI framework, service locator, plugin container, workflow system,
  application framework, manifest language, remote or multi-tenant hosts, durable
  authority, supervision/shutdown (ADR-015) and Secret use (ADR-010).
- **Migration:** §4.4. The first release is pre-1.0 (`0.1.0.dev0`); stability is
  promised for the listed names only.
- **Acceptance:** §15 CR-1.
- **Why replaceable:** consumers depend on `GovernedHost` (Protocol) and owner Ports.
  A future durable or remote host can implement the same Protocol, and the local
  realization can change without consumer edits.

## 6. B2 — sandboxed `EngineeringCheckPort` adapter

### 6.1 Verified facts

| Fact | Consequence |
|---|---|
| `EngineeringCheckPort.check(CheckRequest) -> CheckResult`; `CheckRequest(kind, targets: tuple[RepositoryPath, ...])`; closed `CheckKind` | Reuse unchanged; no new command surface |
| M5 fixed options live inline in `checks/local.py` (`-q -o addopts= -p no:cacheprovider`, `check --no-fix --no-fix-only --no-cache`, `format --check --no-cache`, `--no-incremental --cache-dir devnull`) | Extract one private command table shared by both adapters |
| `SandboxExecutionPort.execute(SandboxRequest(script, files: RepositoryText ≤64, artifacts), CancellationSignal)` | Adapter depends on the Port, not on Docker |
| `DockerSandboxConfig.image` **must equal** one stdlib `python@sha256:82bc…` digest ("other pinned images require a new operator qualification") | **Toolchain image profile needed first** |
| Fixed profile: 128 MiB, 32 PIDs, 1 CPU, `network=none`, 32 MiB `/work`, ≤300 s, Windows + Docker Desktop Linux only (`os.name != "nt"` → UNSUPPORTED) | mypy memory unmeasured; platform-limited |
| Inputs are text only: ≤256 KiB each, ≤1 MiB total, ≤64 files | Only small repositories/fixtures fit |
| `CheckFailure`: UNAVAILABLE, IO, TIMEOUT, OUTPUT_LIMIT, CLEANUP | Cannot state CANCELLED / RESOURCE_LIMIT / INPUT_LIMIT truthfully |
| `EngineeringCheckPort.check` has no cancellation parameter | Bind the signal per adapter instance (per run) and do not change the Port |

### 6.2 Design

**Placement:** `legoai_engineering.checks.sandboxed.SandboxedEngineeringChecks`,
implementing `EngineeringCheckPort`. It depends on `RepositoryWorkspacePort`,
`SandboxExecutionPort` and `CancellationSignal | None` (bound at construction).
It does not import Docker or `subprocess` on the host.

1. **Input selection (the new logic):** operator-configured `CheckInputPolicy`.
   This is a bounded recursive walk, via `list_entries`, from configured input
   roots, with a suffix allowlist (`.py`, `.pyi`, `.toml`, `.cfg`, `.ini`, `py.typed`),
   M2 exclusions and sandbox ceilings. Every `CheckRequest` target must fall inside
   the selection. There is no silent truncation: overflow fails with `INPUT_LIMIT`.
2. **Trusted runner:** a module-constant Python runner selected only by `CheckKind`.
   It invokes the image's fixed tool path with the **shared** fixed options, then `--`
   and the targets, `shell=False`, and exits with the tool's exit code. There is no
   caller script, argv or environment.
3. **One sandbox execution per `CheckRequest`**, so a pytest run cannot influence a
   Ruff or mypy result.
4. **Mapping:** exit code, stdout and stderr go to `CheckResult`, and outcome derivation
   is unchanged. `SandboxError` TIMEOUT → `TIMEOUT`, OUTPUT_LIMIT → `OUTPUT_LIMIT`, and
   unavailable environment → `UNAVAILABLE`. New additive `CheckFailure` members:
   `CANCELLED`, `RESOURCE_LIMIT`, `INPUT_LIMIT`, `CONFINEMENT`, with the sandbox error
   chained as cause. This is an additive public enum change, documented.

**Toolchain image profile (M6 extension, precedes the adapter):** a checked-in
Dockerfile builds from the already-pinned base digest and installs hash-locked
pytest 9.1.1, Ruff 0.16.8 and mypy 2.3.1, matching the repo's dev pins. The build
is an operator step that needs network; runtime stays `network=none`. The
resulting digest joins a **closed** set of qualified images in
`DockerSandboxConfig` (for example `STDLIB`, `PYTHON_CHECKS`). The caller still
cannot choose arbitrary images. Qualification must *measure* mypy/pytest peak
memory under 128 MiB. If that fails, a second fixed resource profile is itself an
M6 qualification decision and not an adapter setting.

**Truthful limits to document:**
- Containment is not result integrity. Sandboxed pytest runs model-written code in
  the pytest process, so that code can forge its exit code or output (for example
  `os._exit(0)`). A PASSED outcome is "observed exit status of a contained run",
  not proof. Ruff does not execute target code. mypy executes only configured
  plugins, and those are contained too.
- There is no aggregate host budget. Each check is a new workload plus collector
  pair, and concurrent checks multiply memory. Only Windows with Docker Desktop
  Linux is qualified. There are no image pulls, and sandbox execution creates no
  cache or bytecode on the host.

### 6.3 Tests

- Unit tests with a fake `SandboxExecutionPort`: runner selection per kind,
  options identical to M5 (shared table), target containment, input selection
  bounds and exclusions, error mapping, and cancellation before and during execution.
- Architecture: no host `subprocess`/`os.system`/`shell=True`; no Docker import; a
  single command table.
- Real Docker qualification (toolchain profile):
  - pytest outcomes: pass, fail, no-tests and collection error;
  - Ruff and mypy findings;
  - network denial and host secret absence from test code;
  - source bytes unchanged;
  - failure modes: timeout, OOM → `RESOURCE_LIMIT`, output overflow, cancellation cleanup;
  - a mypy peak-memory measurement;
  - a *documented* forged-exit test that shows the integrity limitation.

## 7. Authorized-wrapper assessment

The wrappers would reuse the existing ADR-018 check, currently private
`AuthorizedRepositoryEvidence._authorize`. That check binds tenant equality, the
operation subject to the workspace ref, action and resource scope, rejects
approvals, and evaluates current authorization per call with a fresh timestamp.
It is about 30 lines of subtle governance logic, so it is not a pass-through.

| Wrapper | Implements (existing Port) | Real responsibility added | Still in LegoAI if ForgeAI vanished? | Decision |
|---|---|---|---|---|
| `AuthorizedRepositoryMutation` | `RepositoryMutationPort` | Current authorization before a **write effect**; M8.3 README already requires "separately authorized external code" before M4 apply; roadmap Phase H needs it | **Yes** | **Create in CR-3** |
| `AuthorizedEngineeringChecks` | `EngineeringCheckPort` | Current authorization before **executing** repository code (isolated or not) | **Yes** (any validation workflow) | **Create in CR-3** |
| Authorized Git observation | `GitRepositoryPort` | Read-only local metadata that ForgeAI-1 shows only to its operator, never to a model | Not proven | **Do not create**; revisit when Git data is disclosed to a model or a less-trusted principal |
| Evidence-capturing wrappers | — | No engineering evidence contract exists; would invent one | — | **Do not create** |

The shared check becomes one private engineering helper reused by the existing
readers and the two new decorators. The action names (for example
`apply-repository-changes`, `run-engineering-check`) need an ADR-018 addendum.

## 8. Module Catalog design (`docs/modules/MODULE-CATALOG.md`)

This is a human-facing index only. It is not machine-readable, does not duplicate
the runtime Capability Catalog and is not a registry. It lists one row per
**real** module, links each row to the module's consumer guide, and uses only these
maturity labels, each backed by evidence:

- **implemented**: code merged, validation pending;
- **deterministically qualified**: offline or fake tests passed locally;
- **live-qualified**: a real provider or tool was exercised locally for the stated scope;
- **experimental**: partial or pending evidence for part of the scope;
- **deferred**: planned, not present. Deferred modules go in a separate section and never in the main table.

Columns: `Module | Real purpose | Public API | Typical uses | Configurable variation | Adapters | Qualification | Limitations | Consumer guide`.

**Superseded (2026-09-29, CR-4):** the canonical, current catalog is
[docs/modules/MODULE-CATALOG.md](../docs/modules/MODULE-CATALOG.md). The draft
rows below are kept as the planning-time snapshot; several are now out of date.

**Draft rows from planning-time evidence (historical):**

| Module | Real purpose | Public API | Typical uses | Configurable variation | Adapters | Qualification | Limitations | Guide |
|---|---|---|---|---|---|---|---|---|
| Core governed runtime | Catalog, resolution, authorization, dispatch, execution context | Owner `values`/`ports`; **no host entry yet (B1)** | Any governed invocation | Not yet data-driven | In-memory reference owners | deterministically qualified (Core suite, local) | Volatile state; single-operator authority | to write (CR-1) |
| Model (`intelligence.model`) | Provider-neutral chat/embed; profile routing; config selection | `ModelPort`, `ModelRouterPort`, values; selection **private** | Chat, embeddings, classification | Binding among admitted contributions (ADR-019, private) | Ollama; offline fakes | Ollama live-qualified for v0.1 DocuMind scope; routing/selection deterministically qualified | No token/cost bounds; no credentialed providers | `docs/model-routing.md`, `model-composition.md` |
| Agent (`execution.agent`, M7) | Governed one-step bounded Agent | `AgentRuntimePort`, `AgentDefinition`; runtime **private** | Structured single-call reasoning | Via routing | `OneStepAgentRuntime` | deterministically qualified | One step; no tools/memory | `docs/agent.md` |
| Engineering workspace/Git/mutation (M2–M4) | Bounded repo read, status, digest-guarded edits | Ports/values/local adapters | Code tools, repo apps | Typed policies (no data capture) | Local filesystem, local Git | live-qualified locally (Windows, real Git/FS) | Trusted stable namespace; no atomic snapshot | engineering README (CR-3 guide) |
| Engineering checks (M5) | Fixed pytest/Ruff/mypy | `EngineeringCheckPort` | CI-like verification | Tool paths, timeout, output | Host adapter | live-qualified locally, **trusted code only** | No isolation | same |
| Engineering sandbox (M6) | Contain generated Python | `SandboxExecutionPort` | Run untrusted Python | Timeout/output within ceilings | Docker Desktop Linux | live-qualified (reference scope) | One stdlib image; Windows only | same |
| Engineering Agents (M8.1–8.3) | Analyst, Reviewer, Coding proposal | `RepositoryAnalyst`, `IndependentReviewer`, `CodingAgent` | Repo Q&A, review, edits | Via Core | Via Core | 8.1/8.2 deterministically qualified; **8.3 implemented** | Wiring private; single call | same |
| Document pack | Parse/chunk/embed/retrieve/rerank/answer | Package contracts | Document Q&A | Via DocuMind config | Ollama via Core | live-qualified (v0.1 DocuMind scope) | v0.1 scope | package README |
| Generative media | Text-to-image, try-on, image transfer | `service.open_*`, Ports/values | Image generation | Provider/driver, `env:NAME` secrets, completion policy | Local ComfyUI, Comfy API v2 | Text-to-image live-validated per package README; *root README still says "pending"*: reconcile | Internals use `reference.*`; ComfyUI only | package README |
| Collation (F1) | Source-linked precedence collation | Package API | Field reconciliation | Pure inputs | n/a | deterministically qualified | Single-field | package README |
| Browser hand landmarks (TS) | In-browser hand landmarks | Package exports, `HandConfig` | Gesture UIs | `maxHands` 1–2 | MediaPipe worker | one-hand live-qualified (manual); **two-hand experimental** | Browser-only; not Python | package README |

## 9. Per-module consumer contract template

`packages/<pkg>/docs/CONSUMING.md` (or a README section), with fixed headings:

1. Purpose
2. Real-world use cases
3. Non-use cases
4. Supported public imports (explicit table; everything else internal)
5. Application-facing contract (inputs, outputs, errors)
6. Configuration surface (typed values, data capture, defaults, ceilings)
7. Data/runtime inputs vs operator configuration
8. Supported adapters/providers
9. Extension path (new adapter for the existing Port)
10. Provider replacement path
11. Security/governance boundary (what authorizes it; what it never grants)
12. Effect and failure semantics (NONE/COMPLETED/UNKNOWN; retries)
13. Concurrency and resource behavior
14. Examples (public imports only)
15. Validation/tests (commands; fakes available)
16. Qualification scope (maturity label and evidence link)
17. Known limitations
18. Compatibility/version expectations

Rule: no guide may show a private import. If one is unavoidable, the guide
states that the module is *not yet consumer-ready* and links the blocking slice.

## 10. `docs/ASSEMBLING-APPLICATIONS.md` structure

1. **Intent first:** write the domain task, inputs, effects and authority before choosing modules.
2. **Discover:** the Module Catalog, maturity labels and consumer guides.
3. **REUSE > EXTEND > CREATE**, with worked examples from ForgeAI-0: the Coding Agent is reused, mutation authorization is extended, `TaskRequest` is created.
4. **Application input vs operator configuration:** the no-URL/key/image/argv-in-request rule.
5. **Configuration vs adapter:** selecting among admitted contributions is config; a new technology needs an adapter behind an existing Port.
6. **Compose through public entry points:** `open_local_host`, package `open_*` services, per-run `ExecutionContext`.
7. **Domain code placement:** domain/application layers import Ports and values only; the composition root is the only concrete-import site.
8. **When something belongs in LegoAI:** the "if the application disappeared" test, the Rule of Two (with DocuMind, generative-media and engineering as the example), and the readiness §12 promotion workflow.
9. **Avoiding private imports:** the architecture-test recipe consumers copy.
10. **Testing substitutability:** fake contributions, fake Ports, and the governance negatives every app should keep.
11. **Qualification honesty:** what "works locally" does and does not claim.

## 11. Config / data-driven assembly assessment

Target chain: `config → resolve profile → select adapter → pin revision → compose Port → domain`.

| Chain step | Works today? | Where |
|---|---|---|
| Validated config capture | Partial | ADR-019 model selection (private); generative-media `config.py`; DocuMind `config.py`; engineering none |
| Resolve capability/profile | Yes | `reference.resolution.resolve`, `DeterministicModelRouter` (internal) |
| Select adapter by data | Yes, among admitted contributions | ADR-019 (private); generative-media driver registry (public) |
| Bind immutable revision | Yes | `ConfigurationRevisionRef` pinned in routes, bindings and selection |
| Compose public Port | **No** for the Core governed path (B1); yes for generative media's `open_*` | — |
| Domain workflow | App-owned | — |

## 12. Configuration capabilities vs gaps

| Variation | Config-driven today? | Application code change? | Adapter required? | Notes |
|---|---|---|---|---|
| Model/provider | Among admitted contributions, via ADR-019 (private) | Yes today (private wiring); No after CR-1 | Yes for any unrealized provider | Only Ollama plus fakes; credentialed providers need adapter plus ADR-010 |
| Model profile | Binding table per revision | No (binding data) | No | `ModelRequirement` is fixed per `AgentDefinition` version, by design |
| Deadlines/timeouts | Typed values (Ollama, Git, check, sandbox, ComfyUI `CompletionPolicy`) | Only where the app lacks capture | No | No end-to-end deadline across sync steps |
| Workspace root | Typed `LocalWorkspaceRoot` / `WorkspacePolicy` | App must capture | No | Engineering capture helper: promote after a second consumer |
| Sandbox profile | **No**: one pinned image, fixed resources | Code change plus qualification | No (profile, not adapter) | CR-2a adds a *closed* second profile |
| Approved engineering tools | Closed `CheckKind` (code, by design); tool paths are config | Adding a tool = LegoAI change | No | Intentional: no arbitrary commands |
| Storage adapter | `ConfigurationStorePort` + SQLite for app config only; everything else in-memory | Not selectable | Yes for durable state | ADR-004 realization beyond config is outstanding |
| Generative-media provider | **Yes** (driver, endpoint, `env:NAME` secret) | No | Yes for non-ComfyUI | Most mature example |
| Workflow/template selection | Generative media: operator-approved frozen templates; general workflows: none | — | — | Phase G unbuilt; no YAML workflow engine |
| Evidence/observation profile | **No** | — | — | `ObservationSinkPort` exists; ADR-013 Proposed |
| Secrets | Package-local `env:NAME` (generative media only) | — | — | Core ADR-010 mechanism not realized |

## 13. Three-consumer reuse sanity check

| Question | ForgeAI | DocuMind | Unrelated agentic app (Career Inbox Assistant, named in `docs/model-composition.md`) |
|---|---|---|---|
| Same public composition boundary? | Yes: `open_local_host` → `agent_runtime` | Yes: `governed_chat/embed` | Yes: `agent_runtime` or `governed_chat` |
| Provider switch config-only? | Yes among admitted bindings | Yes after migration (currently hard-codes Ollama) | Yes for the model; **no** for Gmail/Telegram (new adapters) |
| Private imports needed after CR-1? | No | No | No |
| Engineering module independent? | Consumes it | Unaffected | Never imports it |
| Truly cross-application | Core host, model routing/selection, Agent, governance | same | same |

Engineering is cross-application only among software-engineering consumers,
which is appropriate. No ForgeAI concept is needed by the other two, and this
check found no need for a generic app builder.

## 14. Implementation slices

| Slice | Owner | Scope | Blocks ForgeAI-1 |
|---|---|---|---|
| M8.3-closure | legoai-engineering | Run `CODING_AGENT_M8_3_test.ps1`; close symlink tests | **Done 2026-09-29** |
| CR-1a | Maintainer | Allocate and decide ADR-014 per §5 | **Yes** |
| CR-1b | Core runtime | `legoai.runtime.api` + `legoai.runtime.local.open_local_host`; migrate engineering examples and DocuMind | **Yes** |
| CR-1c | Generative media | Migrate `local_host.prepare_local` to the public host | No |
| CR-2a | legoai-engineering (M6) | Toolchain image profile: Dockerfile, hash-locked tools, closed image set, memory qualification | **Done 2026-09-29** (Docker-qualified) |
| CR-2b | legoai-engineering | `SandboxedEngineeringChecks` plus additive `CheckFailure` members | **Done 2026-09-29** (Docker-qualified) |
| CR-3 | legoai-engineering | Authorized mutation and check decorators; shared authorization helper; public (non-underscore) evidence wiring over the CR-1 host; ADR-018 addendum for actions; `CONSUMING.md` | **Done 2026-09-29** (locally qualified) |
| CR-4 | Docs | `MODULE-CATALOG.md`, `ASSEMBLING-APPLICATIONS.md`, template; reconcile the root README generative-media status | No (recommended with ForgeAI-1) |

## 15. Acceptance criteria per slice

- **CR-1a:** ADR-014 is recorded with the §5 scope and Accepted by the maintainer.
  The ADR-002 dependency-table amendment is explicit, and the ADR-INDEX register is updated.
- **CR-1b:**
  - The engineering Agent example and DocuMind run offline using only
    `legoai.runtime.api/local` plus owner `values`/`ports`, from a clean install.
  - The architecture test forbids `reference.*` and `_composition` in those consumers.
  - Grants come from config, and no grant means a denial with zero provider calls.
  - A binding switch requires no code change, and a stale revision is rejected.
  - Existing Core and DocuMind suites are unchanged and green.
- **CR-2a:**
  - The image builds reproducibly from hash-locked inputs, and its digest is in the closed set.
  - Any other image is still rejected.
  - All M6 controls pass on the new profile.
  - mypy, pytest and Ruff peak memory is measured and within limits, or the slice stops for a decision.
- **CR-2b:**
  - The adapter implements `EngineeringCheckPort` unchanged, with the same options as M5 (shared table).
  - Outcomes are correct for all kinds, and the new failure reasons are truthful.
  - No host execution of target code occurs, and source bytes are unchanged.
  - The integrity limitation is documented and tested.
- **CR-3:**
  - Denied mutation → no write.
  - Denied check → no sandbox call.
  - Authorization is current per call.
  - Approvals fail closed.
  - The engineering examples use no underscore modules.
  - `CONSUMING.md` follows §9.
- **CR-4:** every catalog row cites evidence; no row claims a maturity it lacks;
  the guide's examples use public imports only.

## 16. Tests and evidence needed

Offline or fake tests for every slice; real-Docker qualification for CR-2a/2b on
the reference Windows host; clean-install tests for CR-1b and CR-3; affected
suites only (Core composition/architecture, DocuMind, engineering). Record
maintainer-returned output in each slice's completion report. No internal run is
claimed as qualification.

## 17. Consumer-ready acceptance standard

A LegoAI capability is **consumer-ready** when an independent application can:

1. import only supported public APIs;
2. configure supported variation without modifying capability internals;
3. replace a supported adapter without changing application-domain code;
4. instantiate/compose it through documented public wiring;
5. understand its security and effect semantics;
6. test it through documented fake/reference adapters;
7. find a working example;
8. know its current qualification status and limitations.

At planning time, by this standard, nothing on the Core governed path was
consumer-ready (criteria 1 and 4 failed). Engineering M1–M6 were close (they
needed 4 and 6 documented), and generative media was closest overall, although
its internals failed 1 indirectly.

**Current (2026-09-29, CR-4):**
- The Core governed path meets criteria 1 and 4 through the ADR-014 public
  host (CR-1b).
- The engineering governed path meets the standard: CR-3 public wiring,
  `CONSUMING.md`, and clean-install and public-import tests. ForgeAI-1/2/3
  and DocuMind are independent consumers.
- Generative media still composes through private reference wiring, so it
  does not meet criterion 1 until CR-1c.

See [docs/modules/MODULE-CATALOG.md](../docs/modules/MODULE-CATALOG.md).

## 18. Explicit non-goals

No YAML/declarative workflow engine; no application builder or visual editor; no
marketplace; no machine-readable module registry; no DI container or service
locator; no agent-team generator; no durable IAM, multi-tenant or remote hosts; no
Secret mechanism (ADR-010); no supervision/shutdown API (ADR-015); no
observation-profile config (ADR-013); no new sandbox backend; no ForgeAI source.

## 19. Recommended sequence to unblock ForgeAI-1

```
(parallel)  M8.3-closure        CR-1a ADR-014        CR-2a toolchain image
                                   │                      │
                                 CR-1b public host      CR-2b sandboxed checks
                                   └──────────┬───────────┘
                                            CR-3 authorized decorators + engineering guide
                                              │
                                          ForgeAI-1   (CR-4 docs alongside; CR-1c later)
```

**FORGEAI-1 READY AFTER:** M8.3-closure, CR-1a, CR-1b, CR-2a, CR-2b, CR-3.
All six are complete (2026-09-29): **FORGEAI-1 READY.**

**ForgeAI-1 COMPLETE — LOCALLY QUALIFIED (2026-09-29):**
- A single repository task worker lives in `examples/forgeai`.
- It is assembled from public LegoAI APIs only.
- No LegoAI platform change or gap was needed.
- All 20 phases of `validate_forgeai_1.py` passed. They used the offline
  replay model, real sandboxed checks and a clean install; see
  `examples/forgeai/README.md`, "Qualification evidence".
- Live-model quality is not qualified.

**ForgeAI-2 COMPLETE — LOCALLY QUALIFIED (2026-09-29):**
- It adds one independent review gate, the unchanged M8.2 `IndependentReviewer`.
- The review runs after every deterministic gate: exactly two model calls, with no rework, retry or rollback.
- No LegoAI change or platform gap was needed.
- All phases of `validate_forgeai_2.py` passed. They used replay outputs for
  both calls and real sandboxed checks; see `examples/forgeai/README.md`,
  "ForgeAI-2 qualification evidence".
- Live-model quality is not qualified.

**ForgeAI-3 COMPLETE — LOCALLY QUALIFIED (2026-09-29):**
- It adds exactly one bounded rework, only after review #1 completes with `CHANGES_REQUIRED`.
- Ceilings: at most 4 model calls, 2 applies, 2 check batches and 2 reviews; the second review is terminal.
- There is no retry, rollback or Workflow abstraction.
- No LegoAI change or platform gap was needed.
- All phases of `validate_forgeai_3.py` passed. They used replay outputs for
  all four calls, real sandboxed checks for both attempts, and a clean install;
  see `examples/forgeai/README.md`, "ForgeAI-3 qualification evidence".
- Live-model quality is not qualified.
