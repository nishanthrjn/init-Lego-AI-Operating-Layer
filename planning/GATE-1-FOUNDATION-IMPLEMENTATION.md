# Gate-1 Foundation Implementation Plan

**Status:** PROPOSED — FOR IMPLEMENTATION REVIEW

**Date:** 2026-09-20

**Artifact:** Bounded development plan and implementation-local tooling recommendations.

**Owner:** Reference-runtime maintainer, with security, persistence and release review responsibilities retained by their accepted owners.

**Verdict:** READY WITH CONDITIONS for the first bounded foundation source task. The architectural source-start prerequisites are satisfied; no implementation or executable-runtime gate has passed as a consequence of this plan.

**Deliverable boundary:** This document is the only deliverable. No source, dependency installation, database, migration, test suite, ADR, ADR-index amendment, public API or release is created by this task. Commands and source paths below describe subsequent authorized work.

## 1. Authority and current state

This plan is subordinate to [intent](../intent.md), [SPEC](../SPEC.md), [Architecture](../architecture/ARCHITECTURE.md), [Contracts](../contracts/CONTRACTS.md), [Plugin Specification](../plugin-spec/PLUGIN-SPEC.md), [Security](../security/SECURITY.md), [Evaluation](../evaluation/EVALUATION.md), [Conformance](../conformance/CONFORMANCE.md), the [ADR index](../adrs/ADR-INDEX.md), accepted decisions and the [implementation-readiness plan](IMPLEMENTATION-READINESS.md). It applies the repository's [engineering principles](../AGENTS.md). Python representations and tooling never override canonical meaning.

| Accepted source | Binding implementation consequence |
| --- | --- |
| [ADR-001](../adrs/ADR-001.md) | Conventional GIL-enabled CPython 3.14; strict static checking plus runtime validation; optional AI remains optional. |
| [ADR-002](../adrs/ADR-002.md) | One initial `legoai-reference` distribution, regular `legoai` packages, `src/` layout, small Kernel, owner contracts, inward dependencies and private technical composition. |
| [ADR-003](../adrs/ADR-003.md) | Captured configuration sources, bounded composition, immutable effective revisions and exact historical interpretation. |
| [ADR-004](../adrs/ADR-004.md) | Owner-local guarded atomic state/history/result/obligation commits; qualified durability and conservative recovery. |
| [ADR-005](../adrs/ADR-005.md) | Explicit Principal/Tenant and current externally enforced authority; constructing context confers no authority. |
| [ADR-006](../adrs/ADR-006.md) | Inert declaration inspection, independently established finite roots, separate validation/admission/init/activation/publication. |
| [ADR-007](../adrs/ADR-007.md) | Final participating ordering, authoritative resource and Approval claims, actual bounded protected acceptance. |
| [ADR-008](../adrs/ADR-008.md) | Scoped operation equivalence, retained outcomes, coverage-aware status and reconciliation; no blind replay of uncertainty. |
| [ADR-009](../adrs/ADR-009.md) | Source facts and obligations are separate from Evidence custody and its durable acknowledgment. |
| [ADR-010](../adrs/ADR-010.md) | Accepted mechanism, conditionally implemented before any real Secret acquisition/use; no configuration shortcut. |
| [ADR-011](../adrs/ADR-011.md) | Exact release subject, requirement-derived proof, compatibility assessment and separately governed release/publication. |
| [ADR-015](../adrs/ADR-015.md) | Accepted structured asyncio supervision with bounded blocking-worker bridge, explicit ownership, conservative cancellation and restart. |

The current repository has architectural and planning artifacts, not an implemented reference runtime. Foundational architecture is **frozen against speculative expansion**. ADR-015 is **Accepted**. Gate 2 is **not passed**; ForgeAI runtime consumption is **not authorized**; supported release and production are **not ready**.

The readiness document's earlier recommendation to write ADR-015 is historical sequencing. Its question is now decided by accepted ADR-015. Likewise, historical closing instructions in accepted ADRs do not override their current acceptance headers and index. No semantic reopening is needed to select a formatter, local datastore driver or test runner.

Terminology: the readiness plan's **Gate 1 — Source Start** is permission to begin bounded source work. This document also defines **Gate-1 foundation exit**, the evidence required after those increments. Source-start readiness does not assert that foundation exit, Gate 2 or release has passed.

## 2. Goals, exclusions and implementation discipline

The first objective is an installable, typed, tested foundation with immutable configuration, one owner-specific durable storage realization under qualification, inert contribution metadata and a private deterministic composition experiment. Every new module must have a current consumer, invariant and executable test, or an explicit accepted requirement that requires it in that increment.

The direct path excludes live protected external effects, real provider credentials, Secret resolution, Model/Agent/Team/Multi-Agent runtimes, Workflow engines, RAG, persistent Memory, vector stores, brokers, distributed services, hostile Plugin execution, production exporters, a stable public authoring API, ForgeAI integration and registry publication. No optional feature is made a base dependency.

No generic repository, UnitOfWork, service container, service locator, command bus, mediator, universal event bus, global transaction manager, event-sourcing system, scheduler entity or Job entity is introduced. Explicit constructors/functions suffice. No `utils`, `common`, `base` or `manager` dumping ground. A reserved package is not a task to create it. A Protocol is justified by an actual replaceable boundary and consumer, not by a desire to wrap every function.

Storage qualification performs real local filesystem writes in isolated test directories. It is not advertised as a complete governed configuration service: the corresponding authorization, root, resource and mandatory custody enforcement is still Gate-2 work. There is no public write endpoint, `skip_authorization` switch or fake trusted runtime mode. Pure composition and direct storage tests remain visibly separate.

## 3. Concrete reference tooling selections

These are implementation-local selections for the proposed work, not new canonical requirements. At F0, choose reviewed releases compatible with CPython 3.14, pin their actual resolved versions and record the exact interpreter/tool versions used. This planning task does not invent a tested lockfile or claim package installation succeeded.

| Concern | Selected approach | Alternatives and reason | Location; replacement cost |
| --- | --- | --- | --- |
| Project/environment | **uv** | `venv` + pip + pip-tools is viable but separates resolution, environment and execution steps; Poetry adds a second project convention without a present benefit. uv gives one local project loop. | Development/build tooling; low-to-moderate lock/command migration, no runtime contract change. |
| Build backend | **Hatchling** | Setuptools is viable but its broader extension surface is unnecessary for a pure-Python distribution; no compiled extension or custom build hooks are needed. | `pyproject.toml`; low replacement cost after wheel/sdist content tests. |
| Dependencies | **PEP 621 metadata, development dependency group, committed `uv.lock`, reviewed updates** | Unlocked installs permit drift; hand-maintained transitive pins duplicate resolver work. | Repository tooling; runtime dependencies initially empty. |
| Tests | **pytest** | `unittest` is sufficient for small units, but parameterized contract vectors, fixture isolation and subprocess fault cases justify pytest. No plugin collection. | Tests only; moderate fixture conversion cost. |
| Type checker | **mypy, strict** | Pyright is a credible alternative; one checker avoids two suppression/configuration policies. mypy integrates with the Python tool environment. | Source/tests checking; low contract cost, moderate diagnostic migration. |
| Lint and formatting | **Ruff check + Ruff format** | Separate Flake8/isort/Black installations overlap. Start with explicit `E4`, `E7`, `E9`, `F`, `I`, `B`, `UP` rules and no preview rules. | Development only; low mechanical migration. |
| Values/validation | **stdlib frozen dataclasses, enums, Protocols and explicit validators** | Pydantic and attrs add useful features but no first-slice need outweighs the dependency/coercion review; TypedDict alone does not validate input or provide immutable runtime values. | Kernel/owner representations; representation changes must preserve observable contracts. |
| Coverage | **coverage.py**, introduced with configuration branches | Direct `coverage run -m pytest` avoids adding pytest-cov solely as a wrapper. Coverage guides missing-case review, never proves correctness. | Tests only; low replacement cost. |
| Command runner | **None beyond uv** | Make, Just, Nox and task-framework configuration add a second command layer before a matrix exists. Document the small command list. | Developer guide; trivial replacement if repetition later justifies it. |
| Local observation | **stdlib logging with an explicit bounded JSON formatter/sink** | structlog/OpenTelemetry/exporter stacks are unnecessary for local diagnostic records. No global `basicConfig` on import. | `reference.observation`, injected through Observation contracts; low sink replacement cost. |

uv documents editable project installation, committed locks and `--locked` failure on drift; these support the chosen development workflow. The repository still owns dependency review. [uv project workflow](https://docs.astral.sh/uv/guides/projects/), [locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/).

Hatchling supports explicit build inclusion, including `src/` package selection. F0 must check actual wheel/sdist contents and clean installation; selecting a backend alone proves neither. [Hatch build configuration](https://hatch.pypa.io/latest/config/build/).

Tool compatibility must be checked for the **locked releases**, not inferred from the product name. pytest's support policy covers maintained Python versions; Ruff exposes a `py314` target; mypy supplies Python-version and strict-check configuration; coverage.py documents its supported interpreters. Use these primary references at lock creation, then execute the actual checks on the selected CPython build. No future/free-threaded Python claim follows. [pytest support policy](https://docs.pytest.org/en/stable/backwards-compatibility.html), [Ruff settings](https://docs.astral.sh/ruff/settings/), [mypy configuration](https://mypy.readthedocs.io/en/stable/config_file.html), [coverage.py](https://coverage.readthedocs.io/en/latest/).

### 3.1 Build, version and dependency discipline

- Initial package metadata declares `requires-python = ">=3.14,<3.15"`, conventional CPython support, an internal development distribution version such as `0.1.0.dev0`, and no external runtime dependency. This is a reference support bound, not canonical version semantics. Record and pin the actual qualified 3.14 patch in `.python-version` at F0.
- Declare pytest, mypy and Ruff in the development group; add coverage.py when F2 introduces meaningful branch reporting. Pin Hatchling in build requirements and include it in the locked development/build environment. Pin the uv executable separately in developer setup records; uv is not a runtime dependency.
- A project lock alone is not proof that an isolated build used locked build dependencies. For the first reproducible local recipe, install the locked build group before building without isolation. Bootstrap with `uv sync --locked --group dev --no-install-project`, then install the project with `uv sync --locked --group dev --no-build-isolation`. Run the local build against that same prepared environment. Review the initial editable-install/build path too. uv explicitly requires preinstalled build dependencies when isolation is disabled. [uv build isolation](https://docs.astral.sh/uv/concepts/projects/config/).
- Review the complete resolved dependency graph, artifact sources/hashes, license compatibility, maintainer/publisher provenance and known security findings before accepting a new dependency or lock update. No unrestricted alternate indexes, hidden URL/editable dependencies, executable build hooks or automatic upgrades. The standard-library SQLite engine is also a material dependency: record its runtime version and distributor.
- A dependency proposal states purpose, owning layer, why stdlib is inadequate, version/update policy, review evidence, replacement boundary and tests. Preserve lock diffs. Build dependencies can execute code; developer-only does not mean trusted by default.
- ADR-006 owns executable contribution provenance/admission; ADR-011 owns material dependency inventory, exact artifact provenance, security findings and release evidence. Full SBOM/signing/attestation infrastructure is deferred to their actual release scope, not assigned a new ADR. Gate 1 retains enough inventory to support that work.
- No AI SDK, provider SDK, database service, ORM or logging vendor enters the base path. Security updates are reviewed and revalidated, not indefinitely blocked by pinning.

## 4. Incremental packages and dependency enforcement

### 4.1 Smallest subset

**F0 creates only `legoai` and `legoai.kernel`, with `kernel.identity`.** Later Gate-1 tasks add Application, Governance values, Capability/Plugin values, Evidence values, Observation contracts, private Runtime composition and the specific Reference realizations used by the harness. Every parent `__init__.py` is inert; an empty initializer required for a regular package is legitimate, unlike an unused placeholder subsystem.

| Package/module added when consumed | Owner and purpose | Allowed imports | Forbidden imports | First consumer / first proof |
| --- | --- | --- | --- | --- |
| `kernel.identity` | Canonical identity distinction, no identity service | stdlib | All owners, reference, SDKs | F1 context; cross-kind equality/type rejection, immutability. |
| `kernel.references`, `versions`, `context`, `errors`, `effects`, `configuration`, `provenance` | Only shared anchors needed by the selected owner contracts | Acyclic lower Kernel primitives, stdlib | Owner values/Ports, stores, runtime | Configuration and operation records; scope/version/error and deep-immutability tests. Add each with its consumer. |
| `application.values`, `application.ports` | Application/configuration representation and owner-specific storage boundary | Values: Kernel and same-owner pure helpers. Ports: own values, Kernel and explicitly allowed foreign leaf values. | Reference/SDK imports; values importing foreign owners; foreign Port imports | Captured configuration and store contract vectors. |
| `governance.values` | Principal/Tenant and policy/decision data actually referenced by contexts/operations | Kernel and same-owner pure helpers | Policy engine, Resources implementation, foreign values | Explicit fixture context; wrong/missing scope, no authority-from-construction. |
| `capabilities.values` | Inert requirement, offer and resolution findings | Kernel | Plugin implementation, callable providers | Descriptor compatibility analysis; unsatisfied/conflicting/ambiguous cases. |
| `plugins.values` | Exact Plugin/release/contribution/dependency descriptors | Kernel | Capability values or executable contributions | Non-executing descriptor checks; malformed refs, candidate code never imported. |
| `evidence.values` | Requirement/source/custody reference meanings needed by owner obligations | Kernel | Application records, storage, logging backend | Configuration source duty; wrong-subject and scope mismatch tests. |
| `observability.values`, `observability.ports` | Bounded safe diagnostic records and sink boundary | Kernel; Ports may use permitted G leaf values if needed | Custody/state implementation | Capturing and failing sinks; no payload leakage. |
| `reference.application` | Pure configuration composition; owner-specific encoding/store/migration modules | Application contracts, Kernel and permitted peer contracts only | Peer reference implementations, technical root | Configuration and SQLite qualification tests. |
| `reference.declarations` | Fixed inert test/reference descriptors | Kernel, Plugin values | Importing executable provider code | Import-side-effect and declaration tests. |
| `reference.resolution` | Pure compatibility/inspection analysis used by internal harness | Capability contracts, permitted Plugin/G/R/O contracts when actually required | Plugin/Catalog private stores; invocation | Deterministic non-executable findings. No live Catalog yet. |
| `reference.deterministic` | Pure typed normalization function used in the experiment | Its bounded input/output definitions and Kernel | I/O, SDKs, authority checks replaced by flags | Functional vectors and a test-local replacement. No operational Provider activation. |
| `reference.observation` | Explicit local safe formatter and sink | Observation contracts, permitted G contracts, stdlib | Source owner state; custody implementation | Size bounds, sink failure and redaction tests. |
| `runtime._composition.direct` | Private assembly of the internal experiment | Selected contracts and selected Reference implementations | Provider SDK calls, test support imports, new domain state | End-to-end inert harness; no public authoring promise. |

Do not create `execution`, `resources`, `tools`, `runtime.api`, `plugins.spi`, operating Governance realizations, Catalog, Evidence custodian, Secret resolver or any optional AI/information/coordination package just to complete a diagram. Their first real consumers arrive in Gate-2 work or later. If the internal experiment would need a fake Execution or live Tool Port to run, simplify the experiment.

### 4.2 Enforceable matrix

ADR-002 §9 remains the exact maximum. The implementation starts with a stricter allowlist containing only real imports:

| Importing layer | Kernel | Own values/Ports | Foreign values | Foreign Ports | Reference implementation | Technical root / external SDK |
| --- | --- | --- | --- | --- | --- | --- |
| Kernel | Acyclic only | No | No | No | No | No |
| Owner values | Yes | Own lower pure values only | No | No | No | No |
| Owner Ports | Yes | Yes, acyclic | Only allowed semantic peers | No | No | No |
| Reference owner | Yes | Yes | Allowed peers | Allowed peers | Own helpers only | No root; driver only in its named Adapter boundary |
| Runtime private composition | Yes | Needed slice | Needed slice | Needed slice | Selected implementations | No direct provider I/O |
| Later application domain | Yes | Supported contracts | Supported contracts | Supported contracts | No | Supported facade only; own Adapter is a separate boundary |

For selected planes, permitted peers are: Application → the accepted Application row; Capabilities → G/R/O/X; Governance → R/O; Observation/Evidence → G; Plugins → C/G/R/Q/O/V. K is allowed as above. These are maximum permissions, not required packages. Reference location does not relax a logical owner's row. Owner `values.py` still cannot import foreign values even when the plane could otherwise interact.

Start an AST-based architecture test in F0. Resolve absolute/relative imports, parent initializers and re-exports; include `TYPE_CHECKING` imports and transitive cycles. Reject star imports and dynamic import/loading in foundation modules unless an explicitly reviewed boundary has a tested allowlist. Test the checker against synthetic forbidden graphs, including a reference import hidden behind a re-export. Scan production paths for imports from `tests` and test-support modules. Check third-party imports separately from the stdlib allowlist.

An AST check does not prove arbitrary Python cannot load code. Combine it with inert-import subprocess tests, dependency inventory and review. Do not invent a security sandbox from package rules. All Gate-1 executable test code is trusted first-party code; installed Python packages provide no hostile-code isolation.

## 5. Values, context, versions and errors

### 5.1 Representation rules

Use nominal frozen, slotted dataclasses for identity and reference values; immutable tuples/frozensets or purpose-specific immutable records for nested data. Frozen outer objects containing caller-owned dictionaries are insufficient. Copy and validate inputs at capture. No implicit string/int/bool coercion. A TypedDict can describe a decoder's intermediate shape but remains mutable and is not runtime validation. Protocols express behavior at selected Ports; runtime attribute checks do not establish trust.

Each parser accepts untrusted `object`, narrows explicitly and returns a validated value or a safe structured failure. Use bounded input length/depth/collection counts at actual external/record boundaries. Limits are declared local fixture/implementation parameters, not invented canonical resource entitlements. No framework decorator, serializer or JSON schema becomes canonical meaning.

### 5.2 Types introduced with consumers

| Increment | Types and use |
| --- | --- |
| F0 | `TenantId`, `PrincipalId`: distinct nominal opaque identity values. Preserve exact supplied meaning; no UUID format or case normalization invented. Validate nonempty bounded representations according to the documented reference input contract. |
| F1 | `ApplicationId`, `OperationId`, `RequestId`, `CorrelationId`, `TraceId`, scoped/pinned reference primitives, canonical `Version`, `OwnerRevision`, configuration revision reference; consumed by F2 configuration and later owner operation envelopes. |
| F2 | Configuration-instance identity, captured source/version/provenance references, immutable effective configuration representation and selector-only Secret reference values where the configuration contract requires them. |
| F4/F6 | Exact source-fact, obligation and evidence requirement references; produced owner revisions and retained operation-result values. No fake Evidence-owner-issued receipt. |
| F7 | `CapabilityId`, Plugin identity/release and contribution/Provider references, version constraints; consumed by inert descriptor matching. |
| Later | `ExecutionId`, `EffectId`, activation refs and actual resource/Approval claims when Gate-2 owners first consume them. No empty Agent/Team/Model IDs. |

References retain concept kind, issuing/owning scope, explicit tenant where operational, identity and exact revision/version where required. Equal text in different identity kinds is not interchangeable. Owner revisions are scoped equality guards, not global clocks. Configuration revision is not the mutable owner-head revision or a Plugin release version. IDs are not credentials or permission.

Implement the version subset actually used by declarations from Contracts CTR-064: major/minor/patch and explicit prerelease interpretation; reject unsupported constraints. Do not reuse PEP 440 package-version parsing as canonical compatibility semantics. No assumed compatibility across initial 0.x changes, ambiguous ranges or implicit prerelease acceptance. Distribution versioning remains a separate packaging concern.

### 5.3 Explicit context without a security bypass

F1 introduces immutable Principal and TenantContext representation and an operation-context value sufficient for configuration-owner requests: request/operation identity, correlation/trace and root-or-causation reference, explicit tenant, acting Principal, originating requester and delegation refs where applicable, contract/version and governing configuration/Application revisions when relevant. Deadlines and the time basis are explicit when a boundary can wait; absent Execution identity is allowed for non-Execution administrative mechanics, not synthesized from an OperationId.

Do not publish a partly populated object called canonical `ExecutionContext`. The full accepted Execution context arrives with its first actual Execution consumer, including pinned Application/configuration, inherited deadlines and resource/evidence applicability. Resource/evidence/Policy omissions must be explicit contract-permitted non-applicability, never an empty list interpreted as approval.

Gate-1 test contexts are synthetic representation inputs. They do not claim verified identity, live Grants or current Policy. No `trusted=True`, constructor token, `allow_all` fallback, ambient `current_user`, thread-local authority or mutable global context. F0/F1 tests prove representation and scope handling only; external enforcement belongs to Gate 2. Diagnostic context variables may later copy safe correlation, never establish authority.

### 5.4 First error/effect vocabulary

Use only the initially consumed canonical categories: `ValidationError`, `VersionMismatch`, `TenantViolation`, `Conflict`, `DependencyFailure`; add `CapabilityResolutionError` when its actual boundary requires an error, distinguishing a successfully assessed unsatisfied/ambiguous finding. Add `AuthorizationDenied`, `PolicyViolation`, `BudgetExceeded` and `DeadlineExceeded` only with actual checks that can establish those causes. No speculative Model/Agent error classes.

Effect extent remains exactly **none / partial / completed / unknown** for each named effect. Recoverability remains **terminal / potentially retryable / requires intervention / unknown**. Error/cause, operation result, Execution lifecycle and effects are separate fields/meanings. Timeout alone cannot select `none`; a failed observation can coexist with a committed local mutation.

Retain safe cause category/reference and material secondary causes. Internal Python exceptions may chain with `raise ... from ...`, but their class, raw message, path and traceback are not a public semantic envelope. Pure local constructors can raise documented validation exceptions internally; boundary adapters translate them into the canonical result contract. Do not swallow errors or convert every failure into a misleading denial.

## 6. First Ports and deferred Ports

| Boundary | Gate-1 decision | Reason and consumer |
| --- | --- | --- |
| Configuration owner storage | **Implement an owner-specific Protocol**, privately supported, declared in `application.ports` | Pure owner logic plus SQLite and a test substitute need conditional publication, exact revision read, retained operation status and bounded obligation listing. Model those operations, not generic CRUD. This is an internal realization boundary, not an unauthenticated service API. |
| Observation sink | **Implement minimal selected Observation boundary** | Internal harness emits bounded diagnostic records; a capture sink and failing sink demonstrate substitution and failure behavior. |
| Capability resolution/access | **Defer operational access Port; implement pure declaration-analysis function/results** | Gate 1 has no live Catalog/eligibility owner. Offline compatibility findings must not be executable bindings. Add the real Port when current eligibility can actually be established. |
| Authorization / Policy | **Values only where consumed; operating Port implementation deferred** | Do not create an always-allow checker to make storage or a harness look governed. |
| Evidence custody | **Source/requirement/reference values now; operating custody Port deferred** | Configuration tests exercise a pending custody duty, not fabricated acknowledgment. |
| Tool | **Defer** | The pure test function is not a protected Tool; Action Mediation and actual effect acceptance are Gate 2. |
| Model, AgentRuntime, Workflow, Memory, Retrieval, Event | **Defer** | No current consumer; optional future capability cannot become a foundation dependency. |

At the storage boundary, command/result types preserve scope, semantic descriptor, original expected revision/absence and retained outcome. A stale guard is not silently replaced with the latest value. Production callers eventually reach this storage adapter only through the responsible owner with full enforcement. Raw adapter access is internal trusted-host mechanics, not an authorization boundary.

## 7. Configuration realization

Implement ADR-003 in two separable increments: pure capture/composition first, then owner-issued durable publication and historical lookup.

1. Accept explicit programmatic candidate values. Do not select an application manifest, YAML loader, `.env` loader or environment-watching service.
2. Capture source identities/versions and bounded source data exactly once. Record provenance and interpretation versions; later mutation of input objects or environment changes cannot alter that captured candidate.
3. Validate each section against its owning contract. Distinguish absent, null and empty; reject unknown mandatory semantics, illegal fields and unsupported interpretation. Optional extension metadata is inert only where the contract explicitly permits it.
4. Apply ADR-003's declared defaults, one base source per section and one authorized tenant override. Realization settings occupy their declared separate area. Conflicting base ownership or unauthorized overrides fail. Use **whole-field replacement**, including collections; no recursive merge, append-by-guessing or order-dependent precedence.
5. Produce an immutable candidate interpretation. Equal captured inputs and interpretation rules yield equal effective meaning, not necessarily the same owner-issued revision identity for separate publications.
6. The Application Composition configuration owner publishes under expected head revision/absence, allocates an exact configuration revision and retains the captured provenance/interpretation. A pure candidate does not mint an authoritative published revision.
7. Exact lookup retrieves the old revision and its reader meaning. Never rebuild it from current defaults, return latest, or silently migrate its original meaning. Binding to an actual Plugin activation remains Gate 2.

The first fixture uses a small text-normalization configuration with explicit maximum input size and a declared normalization mode. These are fixture parameters with tests, not universal platform defaults. Include a permitted synthetic tenant override and a rejected override of a protected field.

Secret reference representation contains only identity/scope, selection rule and intended purpose/consumer/target meaning required by ADR-003/010. No bytes, credentials, resolver callbacks, SDK default credential discovery or secret-dependent hashing. Reject raw credential fields at the declared schema boundary. Do not claim arbitrary secret detection inside every string: minimize accepted fields and never log values.

Required tests: source-order-independent interpretation where order has no meaning; conflicting sources; missing/null/empty; whole-list replacement; allowed and forbidden tenant override; unknown required extension; mutation after capture; changed environment after capture; exact old revision after a new publication; unsupported reader; raw material rejection; config changes never activating a Plugin or issuing authority.

## 8. Persistence candidate analysis and decision route

### 8.1 Recommendation

**Recommend local SQLite through standard-library `sqlite3`, synchronous owner-specific operations, one qualified local file and separate logical owner transactions.** For the first owner choose rollback-journal **DELETE** mode with **synchronous=EXTRA**, explicitly checked at connection setup. This conservative starting configuration avoids WAL/checkpoint operating work before reader concurrency requires it. It is a recommendation to qualify, not a claim that the current host/disk already satisfies ADR-004.

SQLite is available through CPython's optional `sqlite3` module without a database server. F0/F3 must verify the chosen CPython distribution includes it and record the actual SQLite library version. [CPython 3.14 sqlite3](https://docs.python.org/3.14/library/sqlite3.html).

SQLite documents additional rollback-journal durability for EXTRA synchronization and explains the filesystem/flush assumptions behind atomic commit. These establish a plausible mechanism, not test evidence for this repository's OS, VFS, filesystem, drive or failure model. [SQLite synchronization](https://www.sqlite.org/pragma.html#synchronous), [SQLite atomic commit assumptions](https://www.sqlite.org/atomiccommit.html).

| Candidate | Strength | Cost / weakness | Disposition |
| --- | --- | --- | --- |
| `sqlite3`, synchronous bounded transactions | Atomic multi-row owner updates, constraints, exact reads, local setup, inspectable format; no new Python runtime package | Blocking I/O, real flush/locking qualification, SQL/migration discipline and trusted-host access required | **Recommended initial realization.** |
| Same SQLite via bounded runtime worker bridge | Preserves storage semantics without running blocking commits on the event-loop thread | Cancellation cannot prove commit stopped; connection affinity, bounded submissions and retained worker ownership required | **Later integration strategy under ADR-015**, not a different database. |
| `aiosqlite` | Convenient async facade for SQLite | Does not itself implement ADR-015 ownership, deadline or capacity guarantees; adds a dependency and queue/thread behavior to qualify | Defer; use the accepted explicit bridge unless measured evidence favors it. |
| Embedded transactional key/value engine | Can support conditional state if a suitable engine/transaction model is qualified | Adds native packaging, secondary-index/history/obligation query and migration work with no present need | Not justified now; revisit only with a workload that SQLite cannot meet. |
| JSON/files with replacement/rename | Easy inspection and useful immutable fixtures | A single rename is not the full guarded state/history/result/obligation transaction, operation uniqueness or robust concurrent recovery; would rebuild database machinery | Reject as authoritative owner store; keep JSON for versioned record payloads/fixtures. |
| In-memory owner fake / SQLite `:memory:` | Fast semantic tests or SQL-specific unit checks | Neither proves durable acknowledgment, disk-full, flush or restart recovery | Test only. |
| PostgreSQL, Redis, event store, Kafka/cloud database | Additional service/distribution capabilities | No current requirement; more deployment, credentials, recovery and solo burden | Reject for this scope. |

### 8.2 Separate lower-level record before durable code

Recommend the next persistence artifact:

- **Title:** Reference Local Persistence Realization and Qualification.
- **Path:** `planning/runtime/LOCAL-PERSISTENCE-REALIZATION.md`.
- **Initial status:** `PROPOSED — FOR IMPLEMENTATION REVIEW`.
- **Decision owner:** Reference-runtime maintainer acting as persistence owner; security/recovery reviewer checks assumptions.
- **Dependencies:** ADR-001/002/003/004/005/008/009/015 and this plan; ADR-011 governs later support claims and change impact.
- **Decision:** Select the concrete SQLite settings, transaction API, scoped schema, record/reader versions, bounds, failure environment and qualification checklist recommended here, or reject the candidate with concrete evidence.
- **Why recorded:** On-disk meaning and durability have migration/recovery costs. Driver syntax can change locally, but an undocumented durable-write contract cannot.
- **Timing:** F3, before F6 writes a durable owner format. F0–F2 stateless work can proceed independently. The record becomes accepted through maintainer review of the concrete recommendation and proof plan; implementation qualification is then completed and recorded by F6/F9 before support claims.

Do not allocate an ADR number or modify ADR-INDEX. This document makes a concrete recommendation; the separate lower-level record is still the durable-code decision gate. It is **not created by this task**. Failure of SQLite qualification blocks the affected store/claim; it does not silently relax ADR-004 or force a canonical product-choice ADR.

### 8.3 ADR-004 qualification mapping

| Required behavior | Concrete strategy to implement | Minimum proof and limitation |
| --- | --- | --- |
| Owner-local atomic commit | Explicit short transaction over only the configuration owner's tables | Inject failure after every component write; observe complete old or complete new set after reopen. |
| Expected revision/absence | Guard head mutation and scoped insertion inside the transaction; check affected rows | Two contenders on same head: one new mutation; loser receives conflict or the same equivalent prior outcome. |
| State + history + result + obligation | Commit all four, with interpretation metadata, as one owner-local set | No published head without history/result/duty; no result falsely acknowledging an uncommitted head. |
| Uniqueness and invariants | Composite tenant/owner/subject/operation and revision uniqueness, foreign-key/check constraints plus owner validation | Collision/conflicting meaning cannot overwrite; complete multi-record invariant checked atomically. |
| Durable acknowledgment | Explicit checked commit before returning committed stage | Kill after commit before response; reopen recovers exact set. Qualify machine interruption separately. |
| Historical lookup | Immutable revision payload and reader version; append successor history | New head and migration do not change old interpretation. |
| Retained operation status | Store exact descriptor, original guard, result stage/revisions and coverage | Equivalent retry checks prior outcome before treating original guard as stale. Conflicting reuse fails. |
| Obligation discovery | Owner-scoped indexed pending/failed/intervention queries with stable bounded pagination | Restart discovers duties without relying on a queue or logs; no silent omission on page boundaries. |
| Tenant/owner scope | Explicit scoped keys/predicates in every read/write/status query; no implicit tenant default | Same opaque ID in synthetic tenants remains separated; wrong scope does not disclose existence. Full live authorization is separate Gate-2 work. |
| Restart | Reopen existing identity without create-if-missing; verify metadata/readers/integrity and recover committed records | Lost-ack and process-kill suite; missing/unreadable store yields unavailable, never fresh empty owner. |
| Migration | Versioned owner schema/readers, explicit reviewed transition and transaction | Interruption gives old supported or complete new version; no half-migrated advertised state. |
| Corruption | Parse/constraint/integrity checks appropriate to scope; fail affected reads and retain safe failure context | Alter/truncate record/database; never return corrupt history as valid or automatically reset store. |
| Bounded access | Small bounded requests/results, parameterized SQL, finite lock wait, explicit connection ownership | Contention refuses/returns uncertainty truthfully; no unbounded busy retry or pool. OS I/O duration is not a hard real-time promise. |
| Runtime exclusivity | One admitted process/owner realization; no supported live takeover; verify predecessor termination before replacement | Second-runtime/startup refusal and operator procedure later under ADR-015. SQLite writer locking alone does not fence external effects. |
| Restore limits | Exact store identity and lineage; known restored images open in reconciliation-only mode | A stale snapshot cannot authorize new work or prove absence. No claim to detect malicious full-store rollback from that same store. |
| Disk full / write error | Preserve failed/unknown commit truth; inspect same operation after reopen | SQL-full/write-fault tests and actual constrained-volume qualification where supported; no false durable acknowledgment. |

Use `autocommit=True` with explicit SQL `BEGIN IMMEDIATE`, `COMMIT` and `ROLLBACK` for this adapter, avoiding accidental legacy implicit transactions. Do not rely on `Connection.commit()` in that mode. Set and verify connection pragmas before transactions; disable extension loading; use parameterized values and fixed reviewed SQL identifiers. Keep connections thread-affine. Do not invoke arbitrary callbacks while a transaction is held. The exact transaction mode is tested against the documented Python behavior. [sqlite3 transaction control](https://docs.python.org/3.14/library/sqlite3.html#transaction-control).

Use one connection at a time in the synchronous Gate-1 harness; contention tests deliberately open separate connections in isolated processes/threads. A later worker bridge owns its connections in the worker and bounds pending work. Cancelling a waiter does not release connection ownership, erase an operation or prove a commit failed. No hidden SQLite retry loop or async library substitutes for ADR-015.

**Durability boundary:** process termination tests are necessary but insufficient for ADR-004's admitted machine termination/restart with intact qualified storage. Record OS, filesystem, SQLite/VFS, drive/flush assumptions and perform the appropriate power/interruption qualification or document the exact still-unqualified boundary. If that proof is unavailable at foundation exit, the adapter remains a tested candidate and machine-durable use remains blocked. Do not claim production durability, device-loss recovery, offsite disaster tolerance or malicious-host rollback resistance.

## 9. First durable owner, serialization and migration

### 9.1 First owner selection

**Select the Application Composition configuration-revision owner.** It has a real consumer and proves exact history without Plugin activation or external Tool dispatch. A free-standing “operation/result owner” would invent ownership for mechanics; a Plugin admission record would drag finite roots, evidence and lifecycle enforcement into Gate 1.

| Element | Exact first record meaning |
| --- | --- |
| State | Current head for `(tenant, application, configuration instance)` pointing to one published effective revision. |
| Revision | Owner-issued head revision H for conditional mutation; separate immutable configuration revision R for exact meaning. |
| History | Captured effective configuration, exact source provenance/interpretation, predecessor relationship and publication operation. Never overwrite old R. |
| Result | Small retained envelope for operation O: original descriptor/expected H or absence, committed stage, resulting H/R, effects, errors if any, duty refs and coverage. |
| Obligation | If the synthetic qualification case requires post-commit source custody, a real pending **source submission duty** describing exact R/source fact, responsible synthetic Principal/tenant, evidence requirement, due/retention bounds and next safe action. No custody receipt or successful end-to-end publication claim is fabricated. |
| Conditional write | Under scoped O uniqueness, first compare retained semantic equivalence, then guard original expected H/absence for genuinely new O; commit head/history/result/duty together. |
| Lost acknowledgment | Suppress response after successful durable commit. Same O/descriptor/original H returns the original committed R; it must not create R2 or fail only because H advanced. |
| Restart | Fresh process reopens the same owner identity, reads R and retained O, enumerates the pending duty; no source reread or custody fiction. |

The first storage operation acknowledgment promises **owner commit only**. It does not promise Evidence custody, activation, current authorization or completion of parent postconditions. Distinguish a successfully committed source fact from its pending duty. Do not invent an artificial obligation merely to fill a table: the qualification vector explicitly selects the canonical post-commit custody requirement. Live service admission of that requirement is deferred until its actual controls/custodian exist.

The test-only direct adapter fixture has temporary storage, synthetic non-sensitive data and no production entrypoint. It cannot be wired as the operational configuration owner until Gate-2 checks are implemented. The storage Port does not offer an “already authorized” boolean as a substitute for owner enforcement.

Use a small test-only in-memory implementation of the same owner storage Protocol for isolated semantic tests. It uses the same scoped revision/equivalence/obligation vectors and atomic all-or-nothing test behavior. Put it in `tests/support`, never ship it as a runtime fallback. SQLite `:memory:` may additionally test SQL, but neither substitute counts as crash/durability evidence.

### 9.2 Serialization

Choose **explicit owner-local JSON record payloads plus typed SQL key/index columns**, using stdlib `json` and explicit encoders/decoders. SQL structure enforces storage scope and constraints; JSON holds bounded immutable meaning. This is not a universal wire protocol or public JSON API.

Each record includes record kind, schema version, interpretation/reader requirement, owner/tenant/subject identity and exact revision links. Keep schema version distinct from canonical contract version, configuration revision and package version. Decode only known record types. Reject duplicate object keys, non-finite numbers, invalid field types (including bool-as-int), excessive size/depth, missing mandatory fields and unknown mandatory semantics. Optional metadata is accepted only under the record's explicitly versioned extension rule; it cannot change execution behavior.

Use explicit stable encoder rules for tests, including key ordering where semantically irrelevant. Do not use serialized byte equality as the sole operation-equivalence proof, or a digest as identity/authority. Preserve missing/null/empty and ordered collections as defined. No pickle, arbitrary object hooks/class loading, executable YAML, eval, SDK objects, dataclass repr persistence or raw Secret material. MessagePack/CBOR/protobuf and an ORM add machinery without a present interoperability or volume requirement.

### 9.3 Minimum migration discipline

Keep migration code owner-local, with a short explicit registry of supported numbered transitions. No Alembic or generic platform migration framework initially. Before the first on-disk format, record:

| Field / rule | Required treatment |
| --- | --- |
| Schema and reader version | Store metadata separately from each retained record's interpretation version; declare supported source/target ranges. |
| Migration identity | Immutable reviewed identifier and content fingerprint, owner, source and target versions; changed code requires a new identity. |
| Preconditions | Correct store identity, supported source reader, current authorized maintenance context for live use, exclusive/quiescent owner access, adequate capacity and qualified backup strategy. |
| Execution | Explicit invocation; no migration on package import. Transactional schema/data change and success marker. No `executescript` shortcut that accidentally changes transaction boundaries. |
| Failure / interruption | Roll back uncommitted transition; reopen and validate actual metadata. Unknown commit is inspected, not repeated blindly. Unsupported/inconsistent state fails closed. |
| Historical meaning | Keep old revision interpretation available or a reviewed meaning-preserving representation with exact lineage. Do not rewrite old outcomes into current defaults. |
| Restore / downgrade | No automatic downgrade. An old backup may erase revocation/operation knowledge; restore is not safe runtime rollback. |

Test schema creation and unsupported versions immediately with F5/F6. Use a clearly synthetic predecessor fixture to exercise interrupted migration before a real upgrade exists; do not invent a historical supported release. Once an actual format changes, require real old-format fixtures and exact compatibility evidence. A migration test is not authorization to run it against user data.

## 10. Governance, Plugin, Capability and Evidence foundations

### 10.1 Governance

Implement Principal/TenantContext values and only bounded Grant/Policy/decision input representations that a current configuration/descriptor contract consumes. These reference their entitled owners and declared scope; no enterprise IAM, remote verifier, Policy DSL or authorization cache. Decision values distinguish established deny from dependency unavailable. They cannot be constructed by an application and accepted as an owner-issued grant merely because their type matches.

Before Gate 2, actual local trust establishment, independently designated roots, current policy/deputy intersection and enforcement at each owner/Port must be implemented. A single explicit local administration Principal is sufficient only with a qualified trust basis. Gate-1 representation tests do not establish that basis.

### 10.2 Plugin metadata

Implement exact identity/release, declaration/contract versions, contribution ownership, dependencies, configuration requirements and trust/effect declarations as inert data. Descriptor checks do not import candidate modules, enumerate executable entry points or invoke validation hooks. Built-in provenance still requires exact attribution and eventual admission.

Pure transition-table validation may be added with its actual descriptor/lifecycle test consumer. Preserve discovered, validated, initialized, active, degraded, stopping, stopped, failed, retired and the accepted transitions. `validate_plugin` findings do not commit `validated`; admission does. There is no `configured`, `admitted`, `bootstrapping` or `quarantined` lifecycle state. Operating admission records, root graph and init/activation remain Gate 2.

### 10.3 Capability declarations

Implement requirement identity, compatible versions/constraints, exact declared offers and Provider/Adapter/Plugin attribution. Pure analysis reports invalid, unsatisfied, conflicting or ambiguous declarations and a uniquely compatible candidate where established. Deterministic ordering improves diagnostics; it must not arbitrarily break an ambiguity that the contract requires the caller to resolve.

Call these **inspection/compatibility findings**, not authoritative executable CapabilityResolution bindings. Full resolution later consumes current Catalog/Lifecycle and governing constraints. Declared or validated inactive offers never become callable because the metadata matches. Selection is not Permission, activation, Approval or a resource grant.

### 10.4 Evidence and provenance

Add exact Evidence/source fact/requirement/provenance reference values required by configuration results and duties. Source provenance says how a candidate was obtained and interpreted; it is not custody. Receipt representation may be added only when a test genuinely consumes its validation, and a test fixture must be explicitly synthetic. It cannot issue an Evidence-owner identity or satisfy a runtime barrier.

Logs, owner history, provenance and Evidence remain separate even if all eventually use the same physical disk. No Evidence custodian, root audit recursion, signing infrastructure or complete proof ledger is implemented to make Gate 1 look complete. ADR-009 source obligations are preserved for later qualified custody/repair.

## 11. Local structured observation

Select an explicit injected sink implemented with stdlib logging and a bounded JSON formatter. Configure handlers only in the private harness; no global root logger mutation at import. Start with a local stream and a test capture sink; no background exporter, unbounded queue, telemetry service or production retention promise.

Allowlisted fields: record schema version, safe event code, owner/module, trace/correlation/causation, operation/request refs, approved tenant-safe identity token, configuration revision, relevant Plugin/Provider/Adapter versions, stage/transition observation, canonical error category and safe cause ref, latency and bounded size/usage observations. Include Execution ID, authorization decision ref and Tool/effect status **when real**, not fake placeholders for the inert harness. Measurements are observations, not authoritative Resource balances.

Declare finite record/string/collection sizes and bounded output behavior in the local fixture configuration. On overflow, emit an explicit permitted truncation/gap indicator without dumping the original. Optional diagnostics failure is surfaced to the harness as a diagnostic gap; it cannot rewrite a committed owner result, close a mandatory obligation or falsely establish recovery state. Avoid recursive logging on sink failure. No guarantee of bounded OS stream write latency is inferred from a bounded record.

Prohibit ordinary logging of raw Secrets, credentials, authentication assertions, unrestricted input/output payloads, private chain-of-thought, SQL parameters, environment dumps and raw exception messages. Hashing a sensitive low-entropy ID is not automatically safe anonymization. Use approved opaque aliases or omit the field. Test canary values through validation, corruption, migration and sink-error paths; assert no canary reaches emitted records or repr-based fallback.

ADR-013 may defer production exporters, correlation with external systems, sampling/retention policy, volume qualification, dashboards, alert routing and operational service targets. It cannot defer the local safe diagnostic baseline or mandatory Evidence semantics.

## 12. Tests, fault seams and static verification

### 12.1 Test families and timing

Tests arrive with their behavior, never as a late Gate-2 phase. F0 cannot honestly test unimplemented persistence; it establishes the required test discipline and real identity/import/package checks, without skipped placeholders for later families.

| Family / location | Begins | Requirement-derived cases |
| --- | --- | --- |
| `tests/unit/kernel` | F0/F1 | Nominal identity, immutability, scoped refs, version interpretation, errors/effects separation. |
| `tests/architecture` | F0 | Forbidden/transitive/type-only imports, cycles, inert parents, dependency inventory, no test support shipped. Test the checker itself with bad graphs. |
| Static typing | F0 | Strict source and tests; misuse fixtures prove cross-kind IDs cannot be passed interchangeably. |
| `tests/unit/application` | F2 | Capture/composition/replacement/tenant override/unknown semantics; no environment reread. |
| `tests/contract` | F4–F6 | Same configuration-store vectors against test fake and SQLite; exact old revisions, equivalent/conflicting operation reuse and obligation paging. |
| `tests/integration/persistence` | F5/F6 | Real file commit/reopen, scoped uniqueness, actual contention, disk-full/write failures and unsupported schema. |
| `tests/migration` | F5/F6 | Reader/version rejection, synthetic transition interruption; real upgrade history when it exists. |
| `tests/security` | F1 onward | Wrong/missing scope, ID mixups, unsafe decoding, raw material/diagnostic leakage, forged authority value never becoming an operating decision. |
| `tests/unit/plugins`, `capabilities` | F7 | Non-executing inspection, exact attribution, incompatible and ambiguous offers; inactive offers not callable. |
| `tests/unit/observability` | F8 | Allowlist, bounded output, failing sink, no payload/repr leakage. |
| `tests/integration/composition` | F8 | Fixed input/config → fixed typed result, independent test substitute, no I/O/provider/runtime activation. |
| `tests/failure` | F6/F9 | Lost ack, process kill, partial transaction, stale writer, corruption and recovery gaps. |
| Supervision/concurrency/effect families | Gate-2 implementation | Real task/worker cancellation, saturation, handoff races, orphan ownership, partial completion, external uncertainty and custody repair. |

Use fixed contract vectors first. Add Hypothesis only when generated source permutations, serialization structures or revision schedules expose meaningful additional cases; do not add it to F0 for unused capability. Use coverage.py branch reporting from F2 to inspect omitted negative paths, with justified exclusions. No arbitrary 100% target or line-count proxy for contract proof.

Every test or case group cites the governing requirement/ADR section and observable pass/fail proposition. Keep expected outcomes derived from requirements, not copied from implementation. A fake that shares the implementation's bug is not an independent oracle. Include independent expected-value vectors and real backend failure tests. Development reports are **not formal Conformance evidence** until exact subject/scope, applicability, method, limitations and custody meet Conformance/ADR-009/011.

### 12.2 Fault injection

Prefer narrow test-owned adapters/wrappers and subprocess coordination at named boundaries: before transaction; after each staged row; before commit; after commit before response; before reopen/read; during migration; before diagnostic delivery. Never add a public production failpoint registry or a switch that disables authorization/durability.

Use handshakes/barriers and bounded parent watchdogs to kill a child at a known stage. Avoid sleep-based guesses. A wrapper dropping an acknowledgment proves client reconciliation logic; a terminated child using a real file proves process recovery; neither simulates an actual machine power loss. Keep these evidence classes distinct.

| Threat case | Expected observation / next safe action |
| --- | --- |
| Lost commit acknowledgment | Original operation recovers one exact retained result; no second mutation. |
| Stale writer | New operation with old expected head conflicts; no overwritten history. |
| Concurrent duplicate | Same scoped meaning yields one commit/prior outcome; conflicting meaning fails. |
| Partial transaction attempt | Reopen sees complete old or complete new set, never orphan result/head/history/duty. |
| Crash after durable commit | Exact R/O/duty survives; acknowledgment loss is not commit loss. |
| Corrupt record/database | Explicit dependency/interpretation failure; no fabricated valid value or auto-reset. |
| Unsupported schema | Fail before mutation, retain bytes for entitled inspection; no best-effort reinterpretation. |
| Disk full / write failure | No premature success; status resolves committed versus unknown where possible. SQLite page-limit tests exercise a full condition; actual I/O failure scope needs separate qualification. |
| Restored stale copy | Known restore blocks live mutation pending lineage/currentness reconciliation; store-local metadata cannot prove no rollback. |
| Migration interruption | Old complete version or new complete version with valid marker; inconsistent state unavailable. |

### 12.3 Strict typing and lint

Set mypy `python_version = "3.14"`, strict mode, unused-ignore checking and explicit package discovery for `src/legoai` and tests. Use `object` at untrusted decoder boundaries and narrow it; do not spread `Any` through contracts. If a later SDK lacks types, contain it inside its Adapter with narrow checked conversion and documented local suppressions. No global `ignore_missing_imports`, blanket ignores or checking only Kernel while leaving the real store unchecked.

Negative static fixtures are run by a test that requires the expected diagnostic; they are not accidentally included in the normal all-green source set. Bound the subprocess and assert the expected failure rather than treating any checker crash as a success.

Ruff targets `py314`, uses one formatter and explicit stable rules. Suppress a rule locally only with a technical reason. No duplicate formatter/linter stack or unsafe bulk autofix mixed with unrelated behavior.

### 12.4 Local developer commands

After reviewed tool installation and initial lock creation, document this internal loop. Commands are proposed, not executed by this planning task:

```text
uv sync --locked --group dev --no-install-project
uv sync --locked --group dev --no-build-isolation
uv run --locked --no-sync python -m pytest
uv run --locked --no-sync python -m mypy src tests
uv run --locked --no-sync ruff check .
uv run --locked --no-sync ruff format --check .
uv build --no-build-isolation
git diff --check
```

Setup fixes the reviewed uv and CPython patch. `uv lock` is an intentional dependency-change command, not part of ordinary checking. `check` means the test/type/lint/format/build commands above; no extra task runner is required. F2 adds `uv run --locked --no-sync coverage run --branch -m pytest` and `coverage report` through the same environment.

The build smoke test installs the exact wheel into a fresh environment outside the repository, imports the declared package from that installation, checks metadata and verifies tests/source checkout are not supplying imports. Build the sdist and verify it contains required source/typing metadata and excludes local state, credentials, caches and test-only runtime dependencies. Do not fix import failures with `sys.path` injection. No registry publication, public CLI or production deployment is part of these commands.

## 13. Gate-1 internal walking skeleton

Choose **bounded ASCII whitespace normalization**: a typed input string and a declared normalization mode produce a typed normalized result. Specify exact whitespace characters, preservation rules and maximum input length in the fixture contract; include empty input, multiple separators, non-ASCII preservation and limit rejection. No network, credential, filesystem output, Model, Tool or ForgeAI domain logic is involved.

The private experiment has two clearly separated components:

1. **Composition experiment:** synthetic Application declaration → explicit synthetic Principal/Tenant values → captured immutable configuration fixture → Capability requirement and inert Plugin/Provider/Adapter metadata → non-executable compatibility findings → explicitly injected pure trusted normalization function → typed result → safe local diagnostic record.
2. **Storage qualification experiment:** the configuration-owner adapter publishes/reads revisions in an isolated test directory and proves compound commit/recovery. The composition experiment may consume an exact fixture revision produced there, but this does not turn direct adapter tests into a governed configuration service.

The root chooses the pure function explicitly. It does not invoke an inactive Plugin, accept candidate-loaded code or treat descriptor resolution as runtime permission. Its reference declaration records the future owning Plugin/Provider/Adapter association without claiming lifecycle activation. A test-local alternative function implements the same small callable contract to demonstrate substitution; do not ship an extra product Provider merely to count two implementations.

Use ordinary synchronous calls. There is no canonical Execution, durable submission acknowledgment, live Tool/effect dispatch, scheduler or cancellation promise. Do not add asyncio just to make a pure unit test look like a runtime. Error propagation and diagnostic failure are still tested.

**Why this is not Gate 2:** finite trusted roots, current authorization enforcement, authoritative Resources/Approval, executable Plugin admission/activation, Evidence custody, actual protected Adapter acceptance, full ADR-015 and cross-owner retry/reconciliation are absent. A successful pure result proves composition and value behavior only. Local persistence mutation tests do not establish the missing governance chain.

## 14. Dependency-ordered implementation work

All source work below requires the subsequent bounded task instruction. Each work item inherits the definition of done in §16. Paths are allowlists; new files outside them require a scoped rationale, not an unrelated rewrite. Parent package initializers and directly corresponding tests are included only when needed.

| Work | Goal; authority / owner | Allowed files | Dependencies | Observable / negative behavior and tests | Stop condition / non-goals |
| --- | --- | --- | --- | --- | --- |
| **F0** | Installable identity foundation; ADR-001/002, SPEC identity/scope; Kernel | Root packaging/lock/python pin, `src/legoai/{__init__.py,py.typed}`, `kernel/{__init__.py,identity.py}`, identity/architecture/package tests, `docs/development.md` | Accepted plan and bounded source authorization | Two nominal IDs work; cross-kind use fails; installed imports and architecture checker pass | Exact first-task DoD in §21; no contexts, storage, runtime or reserved packages. |
| **F1** | Scoped refs, required versions/context/errors/effects; Contracts common rules, ADR-002/003/005; Kernel/Governance | Needed Kernel modules, `governance/values.py`, their tests and guide | F0 | Explicit context and exact refs; wrong tenant/type/version/unknown meaning rejected; independent effect/error axes | F2 can consume values; no verifier, Grants engine or authority flags. |
| **F2** | Pure configuration capture/composition; ADR-003; Application | `application/values.py`, `reference/application/configuration.py`, config/security tests, coverage config, guide | F1 | Deterministic immutable meaning, proper replacement, safe source provenance; conflicting/raw/unknown input rejected | Pure candidate tests pass; no published owner revision, database or environment loader. |
| **F3** | Record concrete persistence decision; ADR-004/008/009/015; persistence maintainer | Proposed `planning/runtime/LOCAL-PERSISTENCE-REALIZATION.md` only | Can start alongside F0; reconcile with F1/F2 types before acceptance | Review settings, schema boundary, failure qualification and migration plan against §8 | Accepted lower-level decision before F6; no database/source implementation in this work item. |
| **F4** | Owner operation/result/duty and storage Port; ADR-003/004/008/009; Application plus Evidence values | `application/values.py`, `application/ports.py`, needed `kernel/provenance.py`, `evidence/values.py`, test fake and contract vectors | F1/F2, F3 boundary agreed | Expected revision/absence, exact duplicate descriptor, pending source duty and bounded query semantics | Same vectors run against test fake; no custody service or generic repository. |
| **F5** | Versioned owner codecs and migration mechanics; ADR-004/008/011; Application | `reference/application/records.py`, `migrations.py`, serialization/migration/security fixtures/tests | F3 accepted, F4 | Safe round-trip and old-meaning readers; duplicate keys/unsupported/corrupt input fail; migration preconditions tested | Format/reader and transition discipline executable; no real upgrade claim or arbitrary object loading. |
| **F6a** | First SQLite compound owner commit; ADR-003/004/008/009; Application | `reference/application/sqlite_store.py`, owner-local schema definitions, real store contract/integration tests | F3 accepted, F4/F5 | Scoped publish/read/status/duty, atomic guard and retained duplicate outcome | Normal/conflict/duplicate/transaction-failure vectors pass; no operating configuration service. |
| **F6b** | Actual recovery and failure qualification; same owners | F6a files only as defects require; `tests/failure`, persistence/migration tests, decision qualification results | F6a | Real child kill/lost ack/reopen/contention, corrupt/full/interrupted cases; identify machine-durability gap explicitly | Supported proof and remaining qualification boundary documented; no device-loss/external-effect claim. |
| **F7** | Inert Plugin/Capability declarations and analysis; ADR-002/006, Plugin contracts; X/C | `plugins/values.py`, `capabilities/values.py`, `reference/declarations.py`, `reference/resolution.py`, unit/architecture tests | F1/F2; F4 refs if actually used | Static metadata interpreted; no executable import, ambiguous/inactive offers never grant invocation | Internal experiment has inspected candidates; no Catalog, admission/init/activation/SPI callbacks. |
| **F8a** | Safe local observation; Contracts §25, ADR-009 baseline; O | `observability/{values,ports}.py`, `reference/observation.py`, observation/security tests | F1 | Bounded allowlisted records and explicit sink failure; no secret/payload leakage | Capturing/failing sink vectors pass; no exporter or custody. |
| **F8b** | Private deterministic composition; ADR-002; technical root | `reference/deterministic.py`, `runtime/_composition/direct.py`, needed inert parents, composition tests, guide/evidence notes | F2/F7/F8a; F6 only for storage-backed fixture variant | Typed normalization, explicit inputs and substitute, deterministic diagnostics | §13 works without external effects/AI; no supported authoring API or fake live runtime. |
| **F9** | Foundation exit review and handoff; ADR-011 evidence discipline | Relevant tests/docs; source only for bounded identified fixes | F0–F8 complete | Clean install, checks, failure reports, gap list and scope evidence | §18 met or exact failed criterion reported; no Gate-2 or production claim. |

Do not combine F6a/F6b or F8a/F8b merely because an assistant can generate them together. If a work item grows beyond one understandable behavior/proof boundary, split it while preserving dependencies. A split does not require another canonical ADR.

### 14.1 Critical path

```text
F0 → F1 → F2 → F4 → F5 → F6a → F6b → F9
             F3 ────┘     └──── required accepted decision
       F1/F2 → F7 ──────────────┐
          F1 → F8a ───────────→ F8b → F9
```

The table is authoritative where the compact diagram omits prerequisites. F3 research can overlap F0–F2, but durable source cannot precede its accepted record. F8b's pure variant does not depend on SQLite; this prevents persistence qualification from blocking all developer-flow evidence. Foundation exit still accounts for storage results and remaining failure qualification.

### 14.2 Safe parallel work

For a solo maintainer using assistants, prefer one source implementer at a time for shared foundational files. Safe independent tracks are: A, F0 package/tooling; B, F3 persistence record research; D, authoring-evidence checklist and ForgeAI brief preparation in separate notes. Track C, values/contracts, begins after F0 and owns its files exclusively. F7 and F8a can run independently once the shared F1 types are stable.

Assign an explicit file allowlist and pinned contract/source revision to each assistant. Only one task edits `pyproject.toml`, the lockfile, `kernel` or a given `values.py` at a time. Use isolated branches/worktrees where appropriate; review and integrate in dependency order, then rerun affected checks. Research output is a proposal, not an automatic source merge. This plan does not dispatch parallel agents or authorize broad automated changes.

## 15. ADR-015 placement and Gate-2 work

Supervision implementation begins **after the foundation values/configuration/owner-state contract is usable**, as the first Gate-2 implementation track. It does not block F0–F2 and does not belong inside every synchronous test.

Implement accepted ADR-015's complete subset necessary for the claimed deterministic path before live/effectful execution: one runtime-owned asyncio lifecycle; owned structured child scopes; finite outstanding acceptance/queue/active/child/result bounds; durable scheduling responsibility; explicit context; backpressure; deadline/cancellation truth; bounded repair capacity; lock ordering; shutdown; restart/exclusivity and orphan detection. Use the explicit bounded thread bridge only for the blocking operations the path actually needs, including storage; no incidental default executor or unbounded submissions.

Tests must use actual selected primitives, not only mocks: queued expiry/cancellation; overlapping admitted work before advertising concurrency greater than one; ordinary child failure versus supervisor invariant failure; non-cooperative worker retention; cancellation without proof of stop; shutdown saturation; lost scheduling ack; restart from owner duties; stale predecessor; missing custody/store. A semaphore does not own resource entitlement, a queue is not durable acceptance and `TaskGroup` is not a hard shutdown guarantee.

The initial synchronous store can be integrated behind this accepted bridge. Its connection ownership and uncertain commit behavior must survive caller cancellation. If its storage latency cannot meet a required ADR-007 final-section bound, that protected path remains unsupported pending a qualified mechanism. No Python no-await/GIL argument supplies a hard timing proof.

## 16. AI-assisted SDLC and per-increment definition of done

| Role | Required behavior |
| --- | --- |
| Architect | Bind one behavior to exact governing clauses, owner, allowed files, observable/forbidden results and stop condition. No new concepts hidden in a task. |
| Implementer | Read those sources; implement the bounded task; report dependency and format changes explicitly; keep changes reviewable. |
| Reviewer | Independently read governing sources and the actual diff, not just the implementer's summary; challenge boundary and failure assumptions. If the same assistant/person reviews, disclose that limitation. |
| Adversarial tester | Derive counterexamples from scope, revisions, corruption, unknown outcomes and negative authority requirements; check the oracle and real substrate. |
| Human maintainer | Accept/reject consequential architecture, persistence format, dependency, migration, integration and release changes against executable evidence. Ordinary authorized edits do not require repeated permission. |

Model agreement is not proof. Two assistants repeating the same invented contract is one shared error. Require source citations, independent expected outcomes and actual command output bound to the reviewed diff. Do not describe repeated prompting of the same assumptions as independent review.

Each increment is complete only when implementation exists, relevant positive/negative tests pass, strict typing/lint/format/import/build checks applicable to that change pass, requirement mapping is present, dependencies are reviewed, documentation is updated and known limitations are explicit. Rerun affected checks after fixes. Do not claim checks ran if tools were unavailable; do not replace a failing test with a skipped marker to pass the gate.

Source rules: no hidden upstream semantic edits; no unrelated rewrites; no temporary trust bypass; no real Secret; no live provider SDK; no unexplained dependency; no unreviewed generated migration; no broad generated commit across unrelated owners. Tests must challenge behavior, not mirror private branches. No automated migration of existing user data or publication based solely on model approval.

## 17. Security risks and solo-developer burden

### 17.1 Preventative controls

| Risk | Preventative test/control | Owner / release of restriction |
| --- | --- | --- |
| Ambient tenant or identity mixup | Nominal IDs, explicit contexts, same-ID/different-tenant vectors, no global authority | Kernel/Governance; real enforcement still Gate 2. |
| Unsafe deserialization | Unknown kind/version/duplicate-key/deep-payload tests; no dynamic classes/pickle | Application storage; admit only supported readers. |
| Raw Secret or debug leakage | Schema exclusion and canary tests for logs/repr/errors/migration paths | Security/Observation; real material only after qualified ADR-010. |
| Dependency compromise | Reviewed source/artifact/lock inventory, no hidden execution hooks, clean install | Maintainer/ADR-011; unresolved mandatory security finding blocks affected use. |
| Stale revision or operation identity misuse | Actual contending commits and conflicting semantic descriptors | Owner; no overwrite/latest-precondition shortcut. |
| Rollback/restored state | Known-restore reconciliation gate and explicit inability to self-prove freshness | Persistence/runtime; no automatic live restart from stale backup. |
| Cross-owner coupling | Import checks; owner-scoped SQL; separate duties/custody; no global transaction | Architecture/owner reviewers. |
| Test bypass becomes runtime path | Production import/export inventory and absence of allow-all/skip flags; harness private | Runtime/security; Gate-2 owner enforcement before exposure. |
| False Plugin isolation | Only trusted first-party tests; no dynamic candidate imports | Plugin owner; ADR-012 before unsupported semi-trusted/untrusted execution. |
| False runtime/production readiness | Explicit gate ledger and exact evidence limitations | Maintainer; no supported claim from a green pure harness. |

Before **any** real credential/Secret is stored, resolved or consumed by Lego AI, implement and qualify ADR-010 and all prerequisites. This includes database/cloud/GitHub/OAuth/Model/Tool credentials. `.env` may later be an input to the governed mechanism; it cannot bypass it. Local SQLite uses no database credential for this scope. OS file protection is still required and is not replaced by credential absence.

Initial tests and built-in code are trusted first-party code. Future initial runtime Plugins are explicitly admitted trusted local code under ADR-006, not arbitrary hostile packages. **Python package isolation is not security isolation.** Bringing code whose behavior cannot be trusted within the host assumptions activates ADR-012 before execution; changing labels does not prove containment.

### 17.2 Seven burdens for selected mechanisms

Ratings below describe relative local burden and obligations, not measured scores. I = implementation; O = operations; M = maintenance; T = testing; L = local development; D = deployment; K = learning.

| Mechanism | I | O | M | T | L | D | K |
| --- | --- | --- | --- | --- | --- | --- | --- |
| uv/lock + Hatchling | Small metadata/setup | Pin tool/interpreter | Review locks/backend | Clean wheel/sdist check | One environment | One distribution | Learn lock vs build boundary |
| pytest/mypy/Ruff/coverage | Small configs | No service | Review tool upgrades | Test architecture oracle too | Fast selected checks | Dev-only tools | Typing and fixture discipline |
| Frozen values/explicit validation | More explicit code than coercing library | None | Versioned validators | Negative/nested mutation cases | Plain Python debugging | No runtime package | Canonical meaning, not framework APIs |
| Owner-specific Ports/test fake | Small and scoped | No service | Keep vector parity | Real backend still mandatory | Fast isolated tests | Fake excluded | Distinguish contract from authority |
| SQLite synchronous store | Moderate transactions/schema | File/permissions/space | SQLite/format qualification | High failure/restart burden | Easy local inspection | No server; qualified storage | Flush/locking/uncertain commit |
| JSON codec + explicit migrations | Moderate exact decoding | Explicit maintenance window | Preserve old readers | High malformed/interruption burden | Inspectable records | Backup/restore procedure | Version/lineage discipline |
| Inert declarations/pure matching | Small scoped records | No loader/service | Contract/version rules | Ambiguity/inactive tests | Direct fixtures | No marketplace | Eligibility differs from declaration |
| stdlib diagnostic sink | Small formatter | Bounded local output | Allowlist/version review | Leakage/failure cases | Capture/debug locally | No exporter | Logs differ from facts/custody |
| Private synchronous composition | Small explicit wiring | No scheduler | Keep scope private | Substitution/end-to-end | One test entry | No deployed service | No public API promise |
| Later ADR-015 bridge/supervisor | Significant but accepted | Owned lifetime/capacity | Primitive/failure review | High race/worker proof | Deterministic barriers | One process/fail-stop rules | Cancellation is not termination |

SQLite and recovery tests are the largest justified Gate-1 burden because ADR-004 requires them. Removing those tests would simplify the wrong thing. Additional services, generic frameworks and parallel runtimes add burden without a current proof need.

## 18. Gate-1 foundation exit and Gate-2 handoff

### 18.1 Foundation exit checklist

The maintainer can accept foundation exit only with a report bound to the source revision, locked tools, CPython/SQLite versions and tested environment showing:

1. Local installable distribution and clean wheel/sdist smoke test.
2. Reproducible documented local test/type/lint/format/build loop.
3. Minimal nominal values and safe explicit contexts with negative tests.
4. Enforced import/dependency direction and inert package parents.
5. Immutable candidate composition and exact published revision behavior in isolated owner tests.
6. SQLite owner boundary selected/recorded, compound guards/results/duties implemented and tested; any unqualified durability environment explicitly blocks durable runtime use. The exact remaining boundary may be carried forward as allowed by the readiness gate, never described as qualified.
7. Safe versioned serialization and supported-reader rejection.
8. Revision/conflict/duplicate/lost-ack/process-restart and migration-interruption evidence for the selected owner.
9. Inert Plugin/Capability declarations, no executable inactive binding.
10. Explicit Principal/Tenant inputs, no ambient or fake authority.
11. Safe source/Evidence/provenance references; source duty not mistaken for custody.
12. Bounded safe local diagnostics with failure tests.
13. Deterministic internal non-effectful composition and substitution test.
14. No real Secret/provider dependency.
15. No optional AI dependency or unnecessary service.
16. Applicable tests/static/package checks pass; counterevidence and limitations remain visible.
17. Gate-2 blockers below have named owners and are not relabeled optional to claim progress.

No implementation exists from this planning task; **foundation exit is not passed**.

### 18.2 Remaining Gate-2 blockers

| Blocker | Owner and accepted basis | Required handoff evidence |
| --- | --- | --- |
| Qualified persistence for actual runtime failure scope | State owners; ADR-004/008/009 | Exact stack, machine/process durability, migration, missing/corrupt/restore handling and bounded access. |
| Finite independent roots | Governance/Plugin Lifecycle; ADR-005/006/009 | Exact independent designations, qualified trusted loading, no self-admission or recursive duties. |
| Current owner-boundary enforcement | Governance and each protected owner; ADR-005 | Principal/Tenant/deputy/Policy checks on reads, mutations and result disclosure; negative bypass tests. |
| Resources and Approval | Resource/Approval owners; ADR-007 | Explicit units/bounds/retention, invariant conservation, competing consumption, partial acquisition and no false refunds. |
| Real Plugin lifecycle and Catalog | Lifecycle/Catalog/Resolution; ADR-006 | Admission/config/init/activation/publication and stop races; exact usable dependency closure. |
| Evidence custody | Evidence plus source owners; ADR-009 | Durable receipt, pre-effect barrier, post-effect duties, lost ack and repair without repeating action. |
| Supervision | Execution Coordination; ADR-015 | Actual owned tasks/bridge/queues, bounded acceptance, cancellation/shutdown/restart/orphan proof. |
| Protected Tool/Adapter | Action Mediation and selected Adapter | One exact protected deterministic target, real acceptance boundary and truthful effect status. |
| Final arbitration | Participating owners; ADR-007 | All invalidation paths participate; actual exclusivity, non-reentrancy and timing/currentness proof. Strict unprovable timing scopes stay unsupported. |
| Retry/reconciliation | Invoking and state owners; ADR-008 | Finite equivalence/coverage, status/absence semantics, uncertainty/partial completion; no blind replay. |
| Composed crash/restart proof | Runtime and all relevant owners | Successful/denied/timed-out/lost-ack/partial/cancelled/restarted scenarios on actual path. |
| Conditional features | Secret/isolation/observation owners | ADR-010 before real material; ADR-012 before hostile trust scope; ADR-013 before its production observation claims. |

ForgeAI additionally needs Gate 2 and its recovery evidence, accepted/implemented ADR-014, a real brief and a pinned supported consumer boundary. Release additionally needs ADR-011 exact candidate/applicability/evidence/compatibility/current approval and publication proof. Production adds actual workload/deployment/operating qualification. None follows from foundation exit.

## 19. Developer-experience evidence and ForgeAI brief

Do not create ADR-014 now. Record observations while implementing F8b, then extend them with a governed Gate-2 probe:

- Actual application-facing imports, constructed objects and knowledge of internal owner names.
- Configuration capture, validation errors, revision selection and repeatability.
- Private wiring needed to substitute a dependency in tests.
- Number and purpose of setup calls; hidden state or order sensitivity.
- Error/result ergonomics and ability to diagnose a failure from safe correlation.
- Real startup, submit, status/result, cancel and shutdown sequence once ADR-015/Gate 2 exists. Mark these **not observed** during the synchronous Gate-1 experiment.
- Comparison of a direct Python surface, builder, declaration file and hybrid using actual call-flow evidence; do not choose merely from syntax preference.
- At least the deterministic use case and a concrete ForgeAI brief, with evidence that a thin supported boundary can hide private wiring without hiding authority or lifetime.

Before drafting ADR-014, obtain ForgeAI's first real use case, inputs/outputs, Tools and effects, Model/Secret/Artifact needs, identity/authority boundaries, failure/retry/cancellation expectations, latency/throughput workload, deployment assumptions and domain evaluation criteria. Do not invent those answers. ForgeAI may do independent domain discovery now; runtime consumption remains gated.

**ForgeAI requirement ≠ Lego AI requirement.** Keep CodeAgent, repository workflows, issue planning, pull-request generation, UI, prompts and domain acceptance in ForgeAI. Promotion requires a canonical requirement, two independent real uses, demonstrated duplication/provider replacement or a security/correctness need, plus evidence that a smaller application-local solution is insufficient.

## 20. Proposed near-term repository tree

Legend: **NOW** = the only file created in this documentation task; **F0** = create in the first subsequently authorized coding task; **LATER** = create only in its named Gate-1 increment; **RESERVED** = do not create through Gate 1. Existing canonical files remain unchanged. Regular-package initializers are added with their first real module; omitted below for readability.

```text
planning/
  GATE-1-FOUNDATION-IMPLEMENTATION.md              NOW
  runtime/LOCAL-PERSISTENCE-REALIZATION.md        LATER F3, separate review
  authoring-evidence.md                          LATER F8b/F9, actual observations
docs/
  development.md                                F0, updated only as needed
pyproject.toml                                  F0
uv.lock                                         F0, resolver-generated/reviewed
.python-version                                 F0, actual 3.14 patch
src/legoai/
  __init__.py                                   F0, inert
  py.typed                                      F0
  kernel/
    __init__.py                                 F0, inert
    identity.py                                 F0
    references.py                               LATER F1
    versions.py                                 LATER F1
    context.py                                  LATER F1
    errors.py                                   LATER F1
    effects.py                                  LATER F1
    configuration.py                            LATER F2, shared anchors only
    provenance.py                               LATER F2/F4, shared anchors only
  governance/values.py                          LATER F1
  application/
    values.py                                   LATER F2/F4
    ports.py                                    LATER F4
  evidence/values.py                            LATER F4
  capabilities/values.py                        LATER F7
  plugins/values.py                             LATER F7
  observability/
    values.py                                   LATER F8a
    ports.py                                    LATER F8a
  reference/
    application/
      configuration.py                          LATER F2
      records.py                                LATER F5
      migrations.py                             LATER F5
      sqlite_store.py                           LATER F6a
    declarations.py                             LATER F7
    resolution.py                               LATER F7, inspection only
    deterministic.py                            LATER F8b
    observation.py                              LATER F8a
  runtime/_composition/direct.py                LATER F8b, private
tests/
  unit/kernel/test_identity.py                  F0
  architecture/test_import_boundaries.py        F0
  architecture/test_package_install.py          F0
  typing/                                       LATER F1, bounded negative cases
  unit/{application,plugins,capabilities}/       LATER respective increments
  unit/observability/                           LATER F8a
  contract/test_configuration_store.py          LATER F4/F6
  support/configuration_store.py                LATER F4, test fake only
  support/persistence_child.py                  LATER F6b, fault subprocess
  integration/persistence/                      LATER F6
  integration/composition/                      LATER F8b
  security/                                     LATER F1 onward
  migration/                                    LATER F5/F6
  failure/                                      LATER F6b/F9
```

Reserved only: `kernel.lifecycle/capabilities/ports/extensions/events` until actual shared consumers require them; `execution`, `resources`, `tools`, `runtime.api`, `plugins.spi`, operating Governance/Catalog/Evidence modules, Agent/Model/Team/Workflow, information/Memory/Retrieval, Artifact, event delivery and release-assessment runtime modules. Reservation does not mean their semantics are optional when a later protected path needs them.

## 21. Exact first coding task

### F0 — Installable nominal identity foundation with enforced package boundaries

**Goal:** Create the smallest useful `legoai-reference` distribution with `TenantId` and `PrincipalId`, strict checks and real package/import tests. This is the single first task Astra should perform after explicit source authorization.

**Authority:** ADR-001; ADR-002 §§5–9 and public/private/import rules; SPEC identity/tenant principles; Contracts identity/reference interpretation; AGENTS engineering rules. No source authority is derived from external repositories.

**Files to create/change:** `pyproject.toml`, `uv.lock`, `.python-version`, `src/legoai/__init__.py`, `src/legoai/py.typed`, `src/legoai/kernel/__init__.py`, `src/legoai/kernel/identity.py`, `tests/unit/kernel/test_identity.py`, `tests/architecture/test_import_boundaries.py`, `tests/architecture/test_package_install.py`, `docs/development.md`. Change `.gitignore` only if actual build/cache outputs are not already covered; no broad ignore rewrite. No accepted document edits.

**Implementation requirements:**

1. Resolve/review/pin the selected F0 tools on an actual conventional CPython 3.14 patch; record the successful versions and artifact sources. Configure the build environment discipline in §3.1.
2. Declare one distribution, explicit `src/legoai` wheel content and no external runtime requirements. Initial package version is development-only. No console-script entrypoint or automatic plugin discovery.
3. Implement two separate immutable nominal ID types with exact opaque text preservation, no implicit coercion and no invented UUID format. Document representation bounds without claiming identifiers establish tenant admission or Principal verification.
4. Reject invalid type/empty representation according to that explicit reference input contract. Distinct classes with identical text are not interchangeable/equal as domain identities. Hash/equality behavior follows immutable value semantics.
5. Keep imports inert and Kernel restricted to needed stdlib. No environment reads, filesystem/network activity, backend initialization, globals or decorators with registration side effects.
6. Configure pytest, strict mypy and Ruff. Implement import-boundary checking over actual source and negative synthetic graphs. Include strict tests and a clean-install package smoke test.

**Tests:** correct construction/equality/hash; mutation rejection; cross-kind identity distinction; wrong Python types and empty value; preservation of opaque spelling; architecture checker rejecting a synthetic forbidden reference import and cycle; inert import; exact distribution metadata/content and clean installed import outside the checkout. Do not test implementation line structure or dataclass internals as the requirement.

**Commands:** initial intentional `uv lock` after dependency review; the full setup/test/type/lint/format/build loop in §12.4; clean wheel install test; `git diff --check`. Capture actual success/failure. No network-dependent test or provider credential is required after setup.

**Non-goals:** reference/context/error catalog, configuration, SQLite, migration, runtime, Capability/Plugin activation, security enforcement, AI, public API or release. Do not create reserved empty directories.

**Definition of done:** F0 commands and positive/negative tests pass on the recorded interpreter/tool lock; clean installed package supplies imports; no forbidden imports/runtime dependencies; only the allowlisted scope changed; developer instructions reproduce it. Stop after F0 for review. A generated diff alone is not completion.

## 22. Second coding task

### F1 — Scoped reference and explicit context foundations

**Dependency:** F0 accepted and its checks green.

**Goal/authority:** Provide the minimum records F2 needs without making a trust decision: ADR-002/003/005, Contracts common reference/version/error rules and SPEC explicit tenant semantics.

**Allowed files:** `kernel/identity.py` only for actually consumed IDs; `kernel/references.py`, `versions.py`, `context.py`, `errors.py`, `effects.py`; `governance/values.py` and inert parents; corresponding `tests/unit/kernel`, `tests/security`, bounded `tests/typing` cases; import allowlist and developer guide. Do not add unrelated owner packages.

**Behavior:** typed Application/configuration/owner revisions, operation/request/correlation references; exact scoped refs; explicit Principal/Tenant/requester context; selected canonical versions/errors/effects with safe causes. Keep cross-owner relationships as scoped refs instead of importing owning object graphs. Do not expose partial ExecutionContext or verify identity merely by constructing a record.

**Tests:** cross-tenant and cross-kind mismatch; pinned ref cannot silently become latest; invalid/unsupported version and initial 0.x/prerelease handling; nested immutability; absent authority cannot be manufactured; effect completed/unknown independent from an error. Static misuse fixtures require the expected checker diagnostic.

**Commands:** §12.4 checks, affected installed-import test and diff check. **Stop:** F2 can express its candidate/provenance/context without bare interchangeable IDs. **Non-goals:** authority engine, durable IDs/state, resource balances, lifecycle runner, all possible future error/ID classes.

## 23. Third coding task

### F2 — Captured configuration to immutable candidate interpretation

**Dependency:** F1 accepted. Persistence decision F3 may proceed separately; it does not block this pure task.

**Goal/authority:** Implement ADR-003's bounded composition semantics and Contracts unknown-semantics/scoping behavior for the selected text fixture.

**Allowed files:** needed shared `kernel/configuration.py` and `provenance.py` anchors, `application/values.py`, `reference/application/configuration.py`, inert parents, configuration/security tests, `pyproject.toml`/lock only to add reviewed coverage.py, developer guide and import allowlist. No storage, root or operating Policy code.

**Behavior:** capture explicit programmatic inputs once; represent source provenance; validate section ownership; apply declared defaults/base/tenant whole-field replacement; produce deeply immutable candidate interpretation and safe validation findings. Secret reference shape only where explicitly exercised, no raw material or resolver. Do not allocate an authoritative published revision in this pure function.

**Tests:** same captured meaning; mutated caller input; changed environment; missing/null/empty; whole-list replacement; conflicting bases; unauthorized tenant override; unknown mandatory semantics; invalid parameter type/range; secret-bearing fields rejected without logging contents. Expected vectors are independent of implementation helpers.

**Commands:** §12.4 plus branch coverage report. **Stop:** all §7 pure tests pass with clear owner boundaries and no I/O. **Non-goals:** configuration file language, `.env`, published revision/head store, Plugin binding, public builder/manifest or live runtime.

## 24. Measurements, replacement and anti-overengineering review

Measure only after runnable components exist: clean/warm test and type-check time, configuration validation by bounded input size, owner commit/read/reopen latency, migration fixture time and local memory footprint. Record source/lock/interpreter/SQLite/OS/storage configuration, sample count, cold/warm condition and measurement method. Include slow/failing cases; do not hide fsync cost with in-memory benchmarks.

These are engineering baselines, not production SLOs. Set workload-derived targets when an actual deterministic/ForgeAI use case and deployment exist. Investigate measured bottlenecks before optimization. **No optimization ADR without measurement.** A correctness defect can be fixed without a performance experiment.

Replacement boundaries are concrete: Hatchling changes package build configuration and artifact tests; uv changes lock/environment recipes; pytest changes test adapters/fixtures; mypy/Ruff change development checks; value-library replacement preserves independent contract vectors; logging replacement implements the same bounded sink; SQLite replacement implements the owner-specific Port and requires history/result/obligation migration plus full failure requalification. No promised zero-cost storage replacement, and no new abstraction is added solely to make replacement sound easy.

| Challenge | Finding / action |
| --- | --- |
| Needed before Gate 2? | Identity/configuration/owner state/metadata/diagnostics/tests are needed; final public API, optional AI, exporters and hostile isolation are not. |
| Accepted requirement or actual consumer? | Every planned module is tied to F0–F9 consumers; reserved anchors stay absent. Remove a proposed module if its task no longer consumes it. |
| Can stdlib suffice? | Values/validation/JSON/logging/SQLite integration can start in stdlib. Tests/type/build tools justify development dependencies. |
| New operating service? | None. SQLite is local; no broker/cache/DB server/telemetry daemon. |
| Solo understand/test/recover? | Small owner-specific operations and explicit migrations are reviewable; actual recovery proof remains the main investment. |
| Domain creep? | Boring normalization fixture, no ForgeAI concepts in Kernel; one application's wish does not create a generic extension. |
| New canonical decision? | None identified. Persistence is implementation-local; supervision is already accepted; authoring awaits evidence. |

Rejected additions: generic Repository/UnitOfWork, ORM/migration framework without a need, DI container, universal bus, event sourcing, distributed scheduler, unbounded executor, AI framework, vector database, automatic plugin marketplace, production telemetry stack and speculative public CLI.

## 25. Final readiness recommendation and completion review

**Gate-1 source-start verdict: READY WITH CONDITIONS.** The next bounded source task can begin when explicitly instructed. This attachment's documentation-only boundary means F0 is specified, not performed.

**Exact recommended next action:** authorize **F0 — Installable nominal identity foundation with enforced package boundaries**, using §21 as its complete task. Separately commission F3's lower-level persistence decision before F6; do not delay F0 for another foundational ADR. Then implement F1 and F2 in order. Stop each increment at its definition of done.

**Persistence next action:** create/review `planning/runtime/LOCAL-PERSISTENCE-REALIZATION.md` separately with the SQLite recommendation and qualification map. Do not implement durable owner code until that decision is accepted. No numbered ADR/index allocation is needed for the recommended form.

**ADR-014 next action:** collect actual internal imports/object construction/config/error/substitution evidence, then real startup/submission/status/cancel/shutdown evidence from the governed probe and ForgeAI's concrete brief. Do not draft its final public API from the inert harness alone.

No unresolved upstream semantic contradiction requiring an amendment was identified for this bounded plan. Historical prospective wording is interpreted against current acceptance records; ADR-015 is consumed as Accepted. Concrete SQLite failure/timing qualification remains an implementation gate, not proof that accepted semantics are achievable on every environment. If an actual experiment demonstrates incompatibility, record the exact failed obligation and route that scope for review without weakening it silently.

Completion review for this document:

- Accepted canonical documents, ADRs, ADR-015 status and ADR-INDEX are unchanged.
- No source, database, dependencies, tests, migration or additional decision document is created here.
- Tooling, representations, first Ports, persistence recommendation/record route and first three coding tasks are concrete.
- No Gate-2, ForgeAI, supported-release, Conformance or production claim is made.
- No real Secret path, optional AI dependency, speculative service or public stable authoring API is introduced.
- Future executable checks are explicitly distinguished from this document's review. This task verifies documentation and change scope; it cannot report runtime tests as passed.

**STOP: no further ADR or source implementation is part of this task.**
