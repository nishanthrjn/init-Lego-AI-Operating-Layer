# ForgeAI-0 — LegoAI reuse / gap assessment and first vertical-slice design

**Date:** 2026-09-28
**Status:** ASSESSMENT ONLY. No source, test, package, dependency or ADR change.
**Inspected at:** branch `br-LegoAI-PyLLM-ComfyUI-CustomerRec`, HEAD `2b633b1`.
**Authority read:** IA-001, ADR-INDEX addendum, `planning/IMPLEMENTATION-READINESS.md`
§§11–12 (Gate 3, promotion workflow), `planning/PYTHON-FIRST-REUSABLE-AI-PLATFORM-PLAN.md`
§§K–L, ADR-017/018/019 status lines, `docs/agent.md`, `docs/model-composition.md`,
`packages/legoai-engineering/README.md` (M1–M8.3), and the executable Ports/values listed in §3.

---

## 1. Executive summary

LegoAI already has almost all of the parts needed for a single repository-task
worker. The engineering pack provides bounded workspace reads (M2), typed Git
status (M3), digest-preconditioned text mutation (M4), fixed pytest/Ruff/mypy
invocations (M5), a Docker sandbox (M6), and a governed Coding Agent (M8.3). That
Agent returns an actual M4 `RepositoryChangeSet` through the governed one-step
Agent runtime (M7) and configuration-selected model routing (M6.5 / ADR-019).
ForgeAI does not need to rebuild any of them.

Two problems stop ForgeAI-1 from being built **under the current rules** without
either breaking them or placing platform behavior in ForgeAI:

- **B1 — No supported application composition boundary (CORE CONTRACT / PLATFORM GAP).**
  Every governed Agent/Model consumer, including DocuMind and the engineering
  examples, is wired through private `legoai.runtime._composition.*` modules and
  underscore-private `legoai_engineering.*._composition` modules. Gate 3 requires
  ADR-014 to be accepted and a thin supported entry interface to exist. It also
  says ForgeAI must not import private reference wiring. ADR-014 is still unallocated.
- **B2 — No isolated execution of verification over model-generated code (PLATFORM GAP, security).**
  M5 says in bold that it is *not safe execution of untrusted repository code*.
  M6 isolates generated Python, but its completion report states that
  "sandboxed pytest/Ruff/mypy composition is not implemented". Running M5 on the
  host after a model edit would breach M5's documented trust boundary.

**Decision: FORGEAI-1 BLOCKED** (see §20). Both prerequisites are narrow, and each
has a correct LegoAI owner. B2 is a new adapter for the **existing** `EngineeringCheckPort`.
Everything else classifies as REUSE or as a small EXTEND that follows the
established ADR-018 "authorized wrapper" pattern. The maintainer can instead
explicitly accept two scoped exceptions, as was done for DocuMind (§20.3). That
would turn the decision into READY WITH CONDITIONS. This assessment does not make
that choice.

## 2. ForgeAI first-user objective

Prove that one ForgeAI worker can complete one small, real coding task on a
disposable local Python repository by **composing** LegoAI. Example task: "add
input validation to a function and update its test". The worker:

    TaskRequest → Git inspect (before) → governed Coding proposal
      → authorized M4 apply → approved checks → Git inspect (after)
      → evidence-backed TaskResult

ForgeAI owns only the task semantics, the step ordering, the result disposition
and the operator configuration capture. LegoAI owns model access, governance,
workspace containment, mutation, Git observation, check execution and isolation.

## 3. Current LegoAI capabilities inspected (executable interfaces)

| Area | Public interface actually present | Notes relevant to ForgeAI |
|---|---|---|
| Model invocation | `legoai.intelligence.model.ports.ModelPort` (`chat`, `embed`, async); `ModelPreflightError` / `ModelResponseUncertainError` / `ModelResponseRejectedError` → NONE/UNKNOWN/NONE effect | Provider-neutral. Only Ollama plus offline fakes are realized; credentialed providers are unsupported (`docs/model-composition.md`) |
| Routing / profile | `ModelRouterPort.route(ModelRequirement, TenantContext)`; `reference.model_routing.DeterministicModelRouter(revision, bindings)` | Exact profile match; NO_MATCH/AMBIGUOUS are results; the binding pins `ConfigurationRevisionRef` |
| Config-selected provider | `runtime._composition.model_selection.capture_model_selection(data, pinned_revision)`, `compose_model(...)` (ADR-019, Proposed) | **Private module.** Closed-field JSON input; rejects class/import/Secret/tenant fields |
| Governed Agent | `legoai.execution.agent.ports.AgentRuntimePort.run(AgentDefinition, AgentRequest) → AgentResult`; `reference.agent.OneStepAgentRuntime`; `runtime._composition.agent.GovernedAgentChat` | One model call, no retries; accepted-output bound only. **`GovernedAgentChat` is private** |
| Execution identity / deadline | `ExecutionContext(execution_id, operation, tenant_context, security_context_ref, correlation_id, trace_id, deadline, causation)`; `ExecutionResult(final_state, effect, error)` | The Coordinator enforces the *admission* deadline; it does not terminate an in-flight provider call |
| Governance | `governance.ports.AuthorizationPort.evaluate(SecurityContext) → AuthorizationDecision`; `Grant`, `Principal`, `PolicyRef`; reference in-memory registries | Approval-bearing contexts are unsupported on the engineering read path (fail closed) |
| Catalog / resolution | `reference.catalog.InMemoryCatalog`, plugin `inspect/validate/admit/initialize/activate` | Model contributions pin the CatalogEntry and the Plugin lifecycle record |
| Evidence | `evidence.ports`; `reference.evidence.InMemoryEvidenceCustody` | Volatile reference custody only |
| Config revision | `application.ports.ConfigurationStorePort`; `reference.application.sqlite_store` | Revisioned configuration publication for the Application owner. No engineering-policy schema |
| Resources | `resources.values.ResourceClaim/ResourceQuantity` | No consumer on the Agent path ("no usage-accounting consumer is present"): no token/cost budget |
| Workspace read | `repository.ports.RepositoryWorkspacePort` (`list_entries`, `read_text`); `repository.local.LocalWorkspaceRoot`, `LocalRepositoryWorkspace(root, WorkspacePolicy)` | Root identity bound; link/reparse/hardlink rejection; no deadline/cancel |
| Mutation | `repository.mutation_ports.RepositoryMutationPort.apply(RepositoryChangeSet) → RepositoryMutationResult`; `MutationConflict`, `MutationApplyError(completed, uncertain, temporary_paths)` | CREATE/UPDATE/DELETE with digest/absence preconditions; `.git` protected; no multi-file atomicity or rollback; **concurrent use of one workspace unsupported** |
| Git | `git.ports.GitRepositoryPort.inspect() → GitRepositoryState(head, entries)`; `git.local.LocalGitRepository(root, LocalGitExecutable, GitReadPolicy)` | HEAD plus porcelain-v2 status only; **no diff**; rejects linked worktrees, submodules and unknown config |
| Checks | `checks.ports.EngineeringCheckPort.check(CheckRequest) → CheckResult`; `checks.local.LocalEngineeringChecks(LocalCheckTools, CheckPolicy)`; kinds PYTEST, RUFF_CHECK, RUFF_FORMAT_CHECK, MYPY | Fixed argv, no shell; **host execution, trusted code only**; per-call timeout, no cancellation token |
| Sandbox | `sandbox.ports.SandboxExecutionPort.execute(SandboxRequest, CancellationSignal) → SandboxResult`; `sandbox.docker.DockerSandbox` | One Python script, explicit inputs, pinned stdlib image; no network, 128 MiB, 32 PIDs, ≤300 s; **does not run M5 checks** |
| Coding Agent | `coding.api.CodingAgent(evidence_reader, agent_runtime).propose(CodingRequest) → CodingResult`; `coding._composition.AuthorizedCodingEvidence` | Returns a validated M4 changeset and never applies it. **M8.3 local validation pending**. Wiring module is underscore-private |
| Analyst / Reviewer | `analyst.api.RepositoryAnalyst`, `reviewer.api.IndependentReviewer` | Available but not needed for the smallest slice (§13) |

## 4. REUSE / EXTEND / CREATE matrix

| ForgeAI need | Current LegoAI capability / interface | Decision | Why | Gap |
|---|---|---|---|---|
| Model inference | `ModelPort` behind `AgentRuntimePort` (M7) | REUSE | Governed, single call, effect-classified | Token/cost budget absent (§16) |
| Provider/model selection by config | ADR-019 `capture_model_selection`/`compose_model`; M6.5 router bindings | REUSE semantics; **B1** for access | The mechanism exists and is tested with two adapters | Private module; only Ollama plus fakes; credentialed providers need an adapter plus ADR-010 Secret use |
| Governed Agent composition | `OneStepAgentRuntime` + private `GovernedAgentChat` + Coordinator + arbiter | REUSE semantics; **B1** for access | Exact semantics required | No supported facade (ADR-014) |
| Repository inspection (file text) | `CodingAgent` via `AuthorizedCodingEvidence` over M2 | REUSE | Authorized, bounded, digest-bound acquisition already exists | Wiring class is underscore-private (B1 applies to engineering too) |
| Plan + proposed edits | `CodingAgent.propose` → `CodingProposal(changeset, summary, reasons, risks, unknowns)` | REUSE | Proposal already *is* the bounded plan plus edits | M8.3 local validation pending |
| Repository mutation | `RepositoryMutationPort.apply` | REUSE mechanism | Preconditions, `.git` protection, partial-failure report | — |
| Mutation authorization | none; README: "only separately authorized external code may call M4 apply" | **EXTEND** (engineering) | Same owner pattern as ADR-018 `AuthorizedRepositoryEvidence`; application-independent | Small authorized wrapper plus action name |
| Git inspection | `GitRepositoryPort.inspect` | REUSE | Revision (HEAD commit) and status suffice for evidence | No textual diff (not required; §13) |
| Git observation authorization | none | EXTEND (engineering) | Same pattern | Small wrapper |
| pytest / Ruff / mypy | `EngineeringCheckPort`, `LocalEngineeringChecks` | REUSE Port; **B2** for the adapter | Correct semantic Port with fixed commands and closed outcomes | Host adapter unsafe for model-generated code |
| Sandbox for verification | `DockerSandbox` (M6) | **EXTEND (B2)**: new adapter implementing *existing* `EngineeringCheckPort` using M6 controls | Isolation owner exists; composition missing | Pinned image with pinned tools; input acquisition; cancellation mapping |
| Check authorization | none | EXTEND (engineering) | Same pattern | Small wrapper |
| Governance / authorization | `AuthorizationPort`, `SecurityContext`, `Grant` | REUSE | Evaluated outside the model | New engineering action names (ADR-018-style decision) |
| Execution lifecycle / identity | `ExecutionContext`, `ExecutionId`, `ExecutionResult` | REUSE | Run identity = `ExecutionId`; no ForgeAI `RunId` | No public run supervisor for sync steps (§10) |
| Deadline / cancellation | `ExecutionContext.deadline` (admission); per-step timeouts (M3 ≤60 s, M5 ≤3600 s, M6 ≤300 s, Ollama `timeout_seconds`); M6 `CancellationSignal` | REUSE per step | Bounded per step | No end-to-end deadline or cancellation across sync steps; ForgeAI checks between steps only |
| Evidence | `InMemoryEvidenceCustody` (governed path); typed step results | REUSE (volatile) | Attribution values already exist (`AgentResult`, `CheckResult`, `FileChangeResult`, `GitRepositoryState`) | No durable evidence; TaskResult is a report, not canonical Evidence |
| Configuration revision binding | `ConfigurationRevisionRef` pinned in router/bindings; `ConfigurationStorePort` | REUSE | Pins exact revision per run | No schema for engineering policies (see next row) |
| Engineering operator config capture (WorkspacePolicy, GitReadPolicy, CheckPolicy, tool paths) | Typed immutable values only; no data capture | **CREATE IN FORGEAI** (candidate for later promotion) | One consumer; Rule of Two not met | Promote on second consumer |
| Per-run workspace provisioning | none (M3 rejects linked worktrees; no clone/copy capability) | Operator/test harness provisions; not ForgeAI-1 | No proven reusable need yet | PLATFORM GAP, deferred |
| Single-workspace exclusivity | none (M4: concurrent use unsupported) | CREATE IN FORGEAI (in-process lease) | Application run policy | Not cross-process (§9) |
| Task semantics, step order, disposition | n/a | CREATE IN FORGEAI | Domain/application behavior | Roadmap Phase H may later absorb generic parts (§21) |
| Presentation (CLI/API) | n/a | CREATE IN FORGEAI (deferred past ForgeAI-1) | Presentation | — |

## 5. Responsibilities and dependency direction

```
forgeai.presentation (example script now; CLI later)
        │
        ▼
forgeai.composition  ── operator config capture → LegoAI typed values;
        │               builds per-run objects; ONLY module touching concrete adapters
        ▼
forgeai.application  ── RepositoryTaskWorker (step ordering, disposition, lease)
        │
        ▼
forgeai.domain       ── TaskRequest, TaskResult, TaskDisposition, TaskEvidence (pure values)
        │
        ▼ (Ports/values only)
legoai_engineering public Ports/values  ── CodingAgent, RepositoryMutationPort,
        │                                  EngineeringCheckPort, GitRepositoryPort
        ▼
legoai public contracts ── ExecutionContext, AgentRuntimePort, AuthorizationPort, kernel refs
        │
        ▼ (wired only by composition roots)
LegoAI adapters ── LocalRepositoryWorkspace/Mutation, LocalGitRepository,
                   sandboxed checks (B2), OllamaModelAdapter, Coordinator (via ADR-014 facade, B1)
```

`forgeai.application` depends on LegoAI **Ports** and on `CodingAgent`, a frozen
public API class whose collaborators are Ports. There are no ForgeAI-specific
Ports, because every external concern already has a LegoAI Port.

**Forbidden directions (enforce with architecture tests, following the engineering `test_architecture.py` style):**

| From → To | Rule |
|---|---|
| forgeai.domain → anything except stdlib and LegoAI immutable values | forbidden |
| forgeai.domain/application → `subprocess`, `os`, `pathlib` I/O, provider SDKs, `legoai.reference.*`, `*.local`, `*.docker`, `legoai.runtime._composition` | forbidden |
| forgeai.application → concrete storage/adapter classes | forbidden (Ports only) |
| any ForgeAI module → `legoai_engineering.*._composition` or `legoai.runtime._composition` | forbidden once B1 lands; until then only `forgeai.composition`, if the maintainer accepts §20.3(a) |
| forgeai → `legoai_generative_media`, `legoai_document`, ComfyUI | forbidden (irrelevant) |
| `legoai` / `legoai_engineering` → `forgeai` | forbidden (IA-001) |
| legoai_engineering → ForgeAI vocabulary (Task, TaskResult, disposition names) | forbidden |

## 6. Proposed ForgeAI components (minimum)

| Component | Responsibility | Inputs | Outputs | Depends on | Why ForgeAI | Stability |
|---|---|---|---|---|---|---|
| `TaskRequest` (domain value) | One bounded task: objective, 1–8 targets (path + CREATE/UPDATE), 0–8 constraints | user data only | validated immutable value | stdlib; `RepositoryPath`, `FileChangeKind` values | Task vocabulary is product semantics | Expected stable for ForgeAI-1/2; may gain a rework option later |
| `TaskResult` + `TaskDisposition` + `TaskEvidence` (domain values) | Closed outcome plus evidence record (§13) | step results | immutable report | LegoAI result values | Disposition vocabulary is ForgeAI's | Disposition set may grow; existing members stable |
| `RepositoryTaskWorker` (application service) | Execute the fixed step sequence for one run; map each step outcome to a disposition; never retry effects | `TaskRequest`, `ExecutionContext` | `TaskResult` | `CodingAgent`, `RepositoryMutationPort`, `EngineeringCheckPort`, `GitRepositoryPort`, clock, verification profile | Application workflow; LegoAI Phase H is not built yet | Internal; *not* a promised API |
| `WorkspaceLease` (application, in-process) | Refuse a second active run on the same operator workspace binding | workspace binding id | acquire/release | none | M4 forbids concurrent use of one workspace; arbitration is application run policy for now | Replaceable later |
| `forgeai.composition` (composition root) | Capture operator config into LegoAI typed values; build per-run adapters and Agent runtime | operator config, pinned revision | worker instance | LegoAI public facade (after B1) and adapters | Operator assembly is application-owned | Changes as LegoAI facade evolves |

**Considered and rejected for ForgeAI-1:** `ChangePlan` (`CodingProposal` already carries summary, per-change reasons, risks and unknowns); `RepositoryContext` (`CodingEvidence` already exists); `VerificationPlan` as an interface (a tuple of `CheckRequest` values in configuration is enough); a ForgeAI `RunId` (`ExecutionId` exists); ForgeAI Ports that wrap LegoAI Ports (they would add no semantics).

## 7. Data / configuration-driven assembly

```
operator config file (revisioned)            ── captured & validated by forgeai.composition
   ├─ model selection {revision, binding}    → ADR-019 capture_model_selection → compose_model  [B1: needs public facade]
   ├─ governance {principal, grants, policy} → SecurityContext / Grant / registries             [B1]
   ├─ workspace profile                      → LocalWorkspaceRoot + WorkspacePolicy
   ├─ git {executable, GitReadPolicy}        → LocalGitRepository
   ├─ verification profile {kinds, targets}  → tuple[CheckRequest] + CheckPolicy + sandboxed adapter [B2]
   └─ run limits {deadline_seconds, require_clean_start}
        ↓
RepositoryTaskWorker (per run) ── execute(TaskRequest)
```

What exists now: model/provider selection is genuinely data-driven between
**already-supported** contributions. Changing `binding` from `offline` to
`ollama` changes no consumer code, and that is tested. Engineering policies are
typed values with validation but no data capture. The smallest gap is a ForgeAI-local
capture function that maps closed-field data onto those existing constructors.
It is not a generic LegoAI configuration framework and not DI. Adding a provider
that is not yet realized (for example a hosted API with a key) needs a new
`ModelPort` adapter plus ADR-010 Secret-reference use. Configuration alone cannot do it.

## 8. Configuration vs application input boundary

**Application / domain input (`TaskRequest`):** objective text; target paths and
CREATE/UPDATE intent; constraints. Nothing else.

**Operator / deployment configuration:** model binding/revision; provider
endpoint and timeout; principal/grants/policy; workspace root and exclusions;
Git executable path; check tool paths or sandbox image digest; check kinds and
targets; per-step timeouts and output caps; run deadline; clean-start policy.
The request never carries a URL, key, image, executable, argv, DSN or absolute path.

Illustrative fragment. **Conceptual**: no such ForgeAI schema exists, and the
model block mirrors ADR-019's existing `{"revision","binding"}` capture.

```json
{
  "revision": "forgeai-ops-1",
  "model": {"revision": "composition-1", "binding": "offline"},
  "workspace": {
    "binding": "fixture-a",
    "exclusions": [".git", ".venv", "__pycache__"],
    "max_entries": 512, "max_depth": 8,
    "max_read_bytes": 65536, "max_text_chars": 65536
  },
  "git": {"timeout_seconds": 20, "max_output_bytes": 262144,
          "max_status_entries": 256, "max_scan_entries": 4096},
  "verification": {
    "isolation": "sandbox",
    "checks": [{"kind": "ruff_check", "targets": ["src", "tests"]},
               {"kind": "mypy", "targets": ["src"]},
               {"kind": "pytest", "targets": ["tests"]}],
    "timeout_seconds": 120, "max_output_bytes": 262144
  },
  "run": {"deadline_seconds": 600, "require_clean_start": true}
}
```

The workspace `binding` maps to an absolute root, and the tool/sandbox paths are
host-specific values held **outside** this file, in the operator host binding. No
Secret is needed for ForgeAI-1, and none is accepted in the data. Capture
must reject a configuration whose summed per-step worst-case bounds exceed `deadline_seconds`.

## 9. Concurrency and run isolation

| Crossover risk | How two simultaneous runs stay separate |
|---|---|
| Task state | Each run gets a new `RepositoryTaskWorker` invocation with a fresh `ExecutionContext`/`ExecutionId`; the worker holds no mutable fields |
| Model context | `OneStepAgentRuntime` retains no conversation; each call builds its prompt from that run's evidence only |
| Files | Each run is bound to a **distinct operator-provisioned workspace root**; M2 root identity is rechecked per call; `WorkspaceLease` refuses a second in-process run on the same binding |
| Git changes | M3 binds explicit `--git-dir/--work-tree` per root; no commits or staging; the clean-start precondition makes the final status attributable to the run |
| Command output | `CheckResult` bytes are returned per call and never logged or shared |
| Evidence | `TaskEvidence` is built per run from typed step results carrying that run's `ExecutionId` |

**Limits (honest):** the lease is in-process only. Two processes pointed at one
root are unsupported and must be prevented by the operator's provisioning. M2/M4/M5
are trusted-stable-namespace designs and are not race-proof against hostile concurrent
writers. Sync steps (M2, M3, M4, M5) block their thread. ForgeAI-1 supports
concurrency by running each run on its own thread or process. No public bounded
thread bridge (ADR-015) was found on the inspected surfaces, and ForgeAI must not invent one.

## 10. Failure / cancellation / effect boundaries

| Step | Effect | Failure → disposition | Retry? |
|---|---|---|---|
| Accept / validate | none | `REJECTED_REQUEST` | n/a |
| Git inspect (before) | read (local process) | `WORKSPACE_UNAVAILABLE`; dirty start → `REJECTED_PRECONDITION` | no |
| Coding proposal | model call (NONE/COMPLETED/UNKNOWN preserved in `AgentResult`) | `INVALID_REQUEST`→`REJECTED_REQUEST`; `MODEL_FAILURE`; `OUTPUT_INVALID`→`PROPOSAL_INVALID` | **no**: an UNKNOWN model effect is reported, not repeated |
| Authorize + apply | local writes | denial → `DENIED` (no write); `MutationConflict` → `MUTATION_CONFLICT` (no write); `MutationApplyError` → `MUTATION_PARTIAL`, reporting `completed`/`uncertain`/`temporary_paths` verbatim | **no**: no rollback, no compensation |
| Checks | isolated execution (B2) | FAILED/INTERRUPTED/NO_TESTS/ERROR → `CHECKS_FAILED` (changes remain applied); `CheckError` → `VERIFICATION_ERROR` | no |
| Git inspect (after) | read | failure → the result retains the prior evidence plus `EVIDENCE_INCOMPLETE` | no |

**Cancellation:** the worker checks the cancellation signal and the deadline
before each step. The async model call propagates `CancelledError` and does not
guarantee that the provider stopped. A running M5 check is bounded by its timeout
only. The sandboxed adapter (B2) should honor M6's `CancellationSignal`. A cancelled
run after apply reports `CANCELLED_AFTER_EFFECTS` with the confirmed mutation prefix.

**Cleanup:** the workspace is disposable and left as-is for inspection. There is
no automatic revert, because a revert is another effect. Operators discard the
per-run directory. No exactly-once guarantee is claimed.

## 11. Security / governance boundary

- The model proposes only. Every effect passes deterministic, externally
  configured checks. Reads use `read-for-model-analysis` (existing ADR-018 action,
  per read and before release). Model invocation uses `invoke-capability` through
  the Coordinator. Mutation, Git observation and checks need authorized wrappers
  (EXTEND) with explicit action names that operators grant.
- Proposal paths are restricted to request targets (the Coding Agent enforces
  this) and then to M4 preconditions. `.git` and dot-paths are rejected. DELETE is
  not proposable.
- No shell or argv surface exists anywhere. Checks are the closed `CheckKind` set
  with fixed options. Targets come from operator config, not from the model.
- Nothing in the prompt grants authority. Approvals are unsupported and fail closed.
- Model-generated code runs **only** inside the M6-grade boundary (B2), or under an
  explicitly accepted exception (§20.3).
- Source text and raw output are excluded from repr and logs, as in the existing modules.
  `TaskResult` holds bounded bytes that trusted consumers only may decode.

## 12. Reusable-module documentation gaps

| Module | Public interface documented | What apps may depend on | Config points | Extension / provider replacement | Security / effects | Unsupported | Consumer tests/examples | Verdict |
|---|---|---|---|---|---|---|---|---|
| legoai-engineering (all) | Yes, but spread across a 1,335-line milestone log | **No explicit list**; examples import `_composition` modules | Implicit in constructors | Partly implied ("future adapters implement the Port") | Thorough | Thorough | Examples use private wiring | **DOCUMENTATION GAP** |
| M4 mutation | Yes | Implicit | WorkspacePolicy | Stated briefly | Thorough | Thorough | Example | Minor gap: "how to authorize apply" |
| M5 checks | Yes | Implicit | LocalCheckTools/CheckPolicy | Not stated | Thorough | Thorough | Example | Gap: replacement adapter path (needed for B2) |
| Core Agent / model routing (`docs/agent.md`, `docs/model-routing.md`, `docs/model-composition.md`) | Yes | Composition is private | ADR-019 input | Adapters mentioned | Yes | Yes | `examples/agent.py`, private | **GAP**: no application-assembly guide (resolved by B1) |
| Consumer test support | — | — | — | — | — | — | Fakes (`StaticModel`) live in examples, not a supported test-support module | **GAP** |

**Proposed additions (not implemented):**
1. `packages/legoai-engineering/docs/CONSUMING.md`: a supported-import table
   (Ports, values and local adapters; `_composition` marked private or promoted);
   per module: configuration values, effects, concurrency statement, unsupported
   behavior, and how to write an alternative adapter for its Port.
2. A short "Assembling a governed Agent" section in `docs/agent.md`, written
   against the ADR-014 facade once it exists.
3. A decision on whether a minimal public fake `ModelPort` / fake Agent runtime
   should ship for consumer tests. Promote only if ForgeAI plus one other consumer need it.

## 13. Smallest ForgeAI executable vertical slice

One worker, one run, one model call, zero rework loops:

1. **Accept:** validate `TaskRequest`; build a fresh `ExecutionContext` (new
   `ExecutionId`, deadline from config); acquire the `WorkspaceLease`.
2. **Before:** `GitRepositoryPort.inspect()` gives `head.commit` as the *inspected
   revision*. If `require_clean_start` is set and entries are non-empty, reject.
3. **Propose:** `CodingAgent.propose(CodingRequest(objective, targets, constraints, context))`.
   This covers authorized bounded reads plus one governed model call and a validated M4 changeset.
4. **Apply:** authorized `RepositoryMutationPort.apply(proposal.changeset)`.
5. **Verify:** for each configured `CheckRequest`, call the sandboxed `EngineeringCheckPort.check`.
6. **After:** `GitRepositoryPort.inspect()` gives the final status.
7. **Report:** `TaskResult(disposition, evidence)`, where evidence is: before
   HEAD commit; `AgentResult` attribution (agent id/version, route binding, model
   `ExecutionResult`); proposal summary/reasons/risks/unknowns; applied
   `FileChangeResult`s (before/after digests); `CheckResult`s (kind, outcome, exit
   code, bounded output); final `GitRepositoryState`; a changed-file summary. An
   optional unified diff is computed purely from evidence text and proposal text.
   M3 provides no diff, and none is required.

Fixture: a tiny stdlib-only Python project with one function and one test,
checked into ForgeAI's tests and copied into a fresh temporary directory per run
by the **test harness**, not by ForgeAI.

## 14. ForgeAI-1 acceptance criteria

1. A valid `TaskRequest` against a provisioned clean fixture produces `COMPLETED_VERIFIED` with a fake model returning a correct edit.
2. Repository reads occur only through `AuthorizedCodingEvidence` → M2. An architecture test shows ForgeAI imports no filesystem, `subprocess` or `*.local` modules outside `forgeai.composition`.
3. The model is reached only through `AgentRuntimePort` composed via the **supported** facade (B1). There is no `ModelPort` import in domain or application code.
4. Files change only via an authorized `RepositoryMutationPort.apply`. A denied authorization produces `DENIED` with byte-identical files.
5. Verification uses only the closed `CheckKind` set through `EngineeringCheckPort`. Model-generated code executes only inside the B2 adapter.
6. No ForgeAI API accepts argv, shell text, executables or paths outside `RepositoryPath` grammar (static and negative tests).
7. Out-of-target, `.git`, dot-path and DELETE proposals are rejected before any write.
8. Two concurrent runs on distinct workspaces produce results carrying only their own `ExecutionId`, files, status and check output. A second run on the same binding is refused.
9. Failure at every step leaves unrelated fixture files byte-identical. A partial apply reports `completed`/`uncertain` exactly.
10. `TaskResult` contains the inspected revision, changed files with digests, check results, final Git status and model attribution.
11. Switching `model.binding` between two supported contributions (offline fake ↔ Ollama with mocked transport) requires no ForgeAI code change.
12. Every step is substitutable with fakes implementing LegoAI Ports. The full suite runs offline without Docker, except the explicitly marked B2 qualification tests.

## 15. Tests needed for ForgeAI-1

| Category | Tests |
|---|---|
| Contract | `TaskRequest` bounds/types/duplicates; `TaskResult` disposition/evidence invariants |
| Happy path | Fake Agent runtime → real M2/M3/M4 on the temp fixture → fake check Port PASSED |
| Substitution | Fake vs real Git/mutation adapters; fake Agent runtime vs governed runtime with fake `ModelPort`; ADR-019 binding switch |
| Config | Changed binding or limits with no code change; invalid, unknown-field and over-deadline configs rejected; Secret-looking fields rejected |
| Isolation | Two simultaneous runs (threads) on two fixtures; same-binding lease refusal; no shared evidence |
| Containment | Proposal outside targets, `.git`, dot-path, traversal, symlinked target → no write |
| Preconditions | Dirty start rejected; stale digest (file edited between propose and apply) → `MUTATION_CONFLICT` |
| Timeouts | Check timeout → `VERIFICATION_ERROR`; model `ModelResponseUncertainError` → `MODEL_FAILURE` with UNKNOWN preserved; deadline exhausted between steps |
| Cancellation | Before propose (no model call), after apply (`CANCELLED_AFTER_EFFECTS`), during sandbox check (B2 signal) |
| Partial failure | Injected `MutationApplyError` → exact prefix reported, no retry |
| Failed tests | Correct apply plus failing pytest → `CHECKS_FAILED`, changes retained and reported |
| Authorization | Denied read, model, mutation and check actions each stop before their effect |
| No shell | Static AST test for `subprocess`/`os.system`/`shell=True` absence in ForgeAI |
| Evidence attribution | Every evidence item's `ExecutionId`/agent version matches the run |
| Model effects | Exactly one model invocation per run (call counter) |

## 16. Operational / scalability limitations (current semantics only)

- **Measured:** nothing about ForgeAI throughput. Existing LegoAI evidence is local-Windows functional qualification only.
- **Architectural replaceability** (not scale): model provider (ADR-019), check execution adapter (host vs sandbox, same Port), workspace/Git/mutation adapters behind Ports, and evidence custody behind `evidence.ports`.
- **Concurrent runs:** bounded by host CPU/RAM/disk and by local Ollama, which typically serializes generation. No admission control across runs. The Docker sandbox is per-execution confinement *without* aggregate host budgeting.
- **Model work:** accepted output is bounded (32 KiB for Coding). Tokens, generation time and cost are **not** bounded. The provider timeout is adapter configuration.
- **Workspace:** M2 limits of 4096 entries per directory and depth 32; M3 admission walk of at most 65,536 entries. Larger repositories fail admission explicitly.
- **State:** volatile. No durable run records, evidence or resumption. A process crash loses the report, and the workspace keeps whatever effects completed.
- **Platform:** Windows plus Docker Desktop Linux is the only qualified sandbox backend. POSIX behavior is unqualified for M6.

## 17. Explicit non-goals for ForgeAI-1

Multi-agent coordination; task decomposition; Reviewer or Test Agent loops;
rework iterations; GitHub/Jira/Slack/email; commits, branches, PRs; browser
automation; package publication; deployment; long-term memory; vector database
or semantic index; web UI; CLI beyond an example script; distributed or remote
workers; microservices; queues; generic shell; arbitrary commands; workspace
cloning or provisioning; credentialed hosted model providers; self-modifying LegoAI.

## 18. Recommended implementation sequence

| Step | Owner | Scope |
|---|---|---|
| 0 | legoai-engineering | Close **M8.3 local validation** (the Coding Agent is the core reused part) |
| 1 (B1) | Core runtime / ADR-014 | Allocate and decide ADR-014 narrowly. Implement the thin public facade *only* for what ForgeAI-1 exercises: build a governed `AgentRuntimePort` from validated model-selection data plus explicit principal/grant/policy/tenant values; construct `ExecutionContext`. Promote or re-export the engineering `Authorized*Evidence` wiring as supported. Include an integration example |
| 2 (B2) | legoai-engineering | Sandboxed adapter implementing the existing `EngineeringCheckPort`: pinned image containing pinned pytest/Ruff/mypy; inputs acquired via `RepositoryWorkspacePort`; M6 controls; cancellation mapping; qualification tests |
| 3 (EXTEND) | legoai-engineering | Authorized wrappers for mutation apply, Git observation and checks, following ADR-018 (action names, per-call current authorization, approvals fail closed); plus `CONSUMING.md` (§12) |
| 4 | ForgeAI | ForgeAI-1 per §§6–15, as a separate application package (DocuMind precedent: separate `pyproject.toml`, pinned LegoAI revision), with architecture tests from §5 |
| 5 | ForgeAI | Measure concepts/imports/config fields needed (readiness §12) and feed the Phase G/H promotion decision |

Steps 1 and 2 are independent and can proceed in either order. Step 3 is small and can follow either.

## 19. CORE CONTRACT GAP / PLATFORM GAP register

| ID | Class | Gap | Owner | Blocks ForgeAI-1? |
|---|---|---|---|---|
| B1 | CORE CONTRACT / PLATFORM | No supported application composition facade; governed Agent/Model and engineering evidence wiring are private (ADR-014 unallocated; Gate 3 items 2 and 4) | Core runtime (ADR-014) | **Yes** |
| B2 | PLATFORM (security) | No isolated execution for pytest/Ruff/mypy over model-generated code | legoai-engineering (M5 × M6) | **Yes** |
| G3 | PLATFORM | No authorized wrappers or action vocabulary for M4 apply, M3 inspect, M5 checks | legoai-engineering (ADR-018 pattern) | Small EXTEND; not foundational |
| G4 | PLATFORM | No end-to-end deadline or cancellation across sync steps; no public thread bridge | Core execution (ADR-015) | No; per-step bounds suffice for one run |
| G5 | PLATFORM | No token/cost/generation budget on model calls | Core model/resources | No; documented limitation |
| G6 | PLATFORM | Volatile evidence and run state only | Core evidence/state (ADR-004/009) | No; report-only result declared |
| G7 | PLATFORM | No per-run workspace provisioning (clone/copy); linked worktrees unsupported by M3 | legoai-engineering, on proven need | No; operator/harness provisions |
| G8 | PLATFORM | Credentialed providers unsupported (adapter plus ADR-010 Secret use) | Core model adapters | No; ForgeAI-1 is credential-free |
| G9 | DOCUMENTATION | §12 | Module owners | No |

## 20. GO / BLOCKED decision

### 20.1 Decision

**FORGEAI-1 BLOCKED.**

### 20.2 Blockers

| | Missing capability | Correct owner | Why ForgeAI cannot own it | Smallest prerequisite slice |
|---|---|---|---|---|
| B1 | Supported, versioned entry point to build a governed Agent runtime (config-selected model, authorization, Coordinator, `ExecutionContext`) plus supported engineering evidence wiring | Core runtime, via ADR-014 | Gate 3 forbids consumers importing private wiring. Reassembling Catalog/arbiter/Coordinator in ForgeAI would duplicate governance and create a second composition root | ADR-014 scoped to one factory surface exercised by ForgeAI-1, with an integration example and a clean-install test |
| B2 | Isolated execution of known checks over untrusted (model-generated) code | legoai-engineering | Execution isolation and check semantics are reusable engineering capabilities. A ForgeAI-owned runner would duplicate M5/M6 and bypass their qualification | New adapter for the existing `EngineeringCheckPort` built on M6 controls, with a pinned tool image and a qualification suite |

### 20.3 Alternative requiring an explicit maintainer decision (not made here)

The maintainer may record scoped exceptions, in an ADR or scope amendment, that
would make ForgeAI-1 **READY WITH CONDITIONS** now:

- **(a)** Allow `forgeai.composition` alone to import the named private
  composition modules, pinned to one LegoAI revision and confined by an
  architecture test, as DocuMind does today. Downside: this is private-API coupling,
  and B1 debt is paid later.
- **(b)** Declare ForgeAI-1's trust scope as *disposable local fixture
  repositories on a developer machine*. The operator accepts that model-generated
  test code runs on the host through M5, matching M5's own trusted-local statement.
  Downside: there is no isolation claim, and it must never be exposed to
  untrusted repositories or operators.

Without both recorded decisions, implementation must wait for B1 and B2.

## 21. "If ForgeAI disappeared tomorrow, which proposed changes would still belong in LegoAI?"

- **B1 — ADR-014 supported composition facade.** Yes. Gate 3 requires it for
  *any* consumer, and DocuMind and the assessment app already show the need.
- **B2 — sandboxed `EngineeringCheckPort` adapter.** Yes. The M6 report already
  records the missing composition, and roadmap Phases D/H need it regardless.
- **G3 — authorized mutation/Git/check wrappers.** Yes. The M8.3 README already
  requires "separately authorized external code" before M4 apply, and any
  proposal-applying consumer (Phase H workflow) needs it.
- **§12 documentation.** Yes.

Everything else stays in ForgeAI: `TaskRequest`/`TaskResult`/dispositions, the
step order, the clean-start policy, the in-process workspace lease, operator
config capture for engineering policies, and diff/summary presentation. The step
sequence overlaps roadmap Phase H ("intake → plan → patch → tests → review").
Under readiness §12 it is implemented in ForgeAI first and promoted only with
second-consumer or Phase H evidence, and never as ForgeAI vocabulary.
