# LEGOAI-ARCHITECTURE-DESIGN-CONFORMANCE-AUDIT-1

Status: IMPLEMENTED — LOCAL VALIDATION PENDING. Static audit, 2026-10-11.
This record is not an ADR, release qualification or authorization to execute live work.

## 1. Executive conclusion

The inspected implementation has substantial real boundary enforcement, particularly
the public governed Model host, ForgeAI's supervised worker, current authorization
wrappers and explicit media effect results. This conclusion comes from source and
test inspection, not diagrams. It does **not** establish repository-wide conformance.

There are unresolved production private dependencies in Generative Media and the
assessment starter, concrete storage coupling in DocuMind, and a high-severity
Secret-use conformance gap in credentialed media. Remote VTO construction with
automatic discovery also has a narrower no-I/O guarantee than its later transfer
refusal; see M-04. No personal-image upload bypass was demonstrated.

Implemented corrections are intentionally small: one shared agent policy/workflow,
an AST fitness ratchet with negative/positive controls, correction of stale active
guidance, an import evidence inventory and an offline maintainer validator. Runtime
executable behavior, public APIs, dependencies and canonical documents are unchanged.
No generic host, storage Port, provider registry, workflow or Team was invented.

## 2. Scope, revision and method

- Baseline HEAD: `25f847cae3961f63372391072695d919e3ad1927`.
- Branch: `br-LegoAIPyLLMComfyCR-ForgeAI-KISSKIColabKagHF`.
- Initial working tree: clean; no pre-existing changes were overwritten.
- Repository inventory: 783 tracked Python files parsed as source, without importing
  or running repository code. Static import evidence is in the companion
  [TSV](LEGOAI-ARCHITECTURE-DESIGN-CONFORMANCE-AUDIT-1-private-imports.tsv).
- Focused control-flow review: Core local host, governed Model/disclosure paths,
  Engineering authorized mutation/checks and sandbox boundary, ForgeAI task values,
  composition and worker, DocuMind application/composition/document operations,
  media service/composition/driver discovery/try-on path. Adjacent collation and
  browser contract/frame-pump sources were also inspected.
- Examples reviewed separately from production APIs: assessment starter, historical
  Model/Agent examples, VTO CLI, and Engineering consumer examples. Evaluation and
  frozen experiment sources are not promoted into production APIs.
- This is repository-wide structural coverage plus targeted behavioral inspection,
  **not** exhaustive line-by-line verification of every implementation or a security
  penetration test. The Python inventory does not analyze TypeScript imports.

No pytest, mypy, Ruff, validation script or live runtime was executed by the audit
agent. The static source inventory is analysis, not passing conformance evidence.
Maintainer execution is reserved under the standing task workflow. Prior supplied
validation logs are historical evidence for their subjects, not fresh results for
this patch. In particular, the previous 365 architecture tests and 48 Kaggle quality
harness tests do not measure model quality or qualify this audit's additions.

## 3. Evidence hierarchy and authority reviewed

| Layer | Inspected authority/evidence | Interpretation |
| --- | --- | --- |
| Canonical intent | `intent.md`, `intent-amendments/IA-001.md` | Independent capability use, Python-first investment, real-consumer-driven extraction; not a mandate to build every planned abstraction |
| Canonical semantics | `SPEC.md`, `architecture/ARCHITECTURE.md` §5 dependency matrix and authority/effect boundaries | Application meaning stays outside infrastructure; Ports separate owners; selection is not authorization |
| Contracts | `contracts/CONTRACTS.md` §§2,4–6 and recovery distinctions | References, Grants, evidence and effects are different facts; unknown is not none or success |
| Security | `security/SECURITY.md`, especially Secret, disclosure and effect obligations | Explicit purpose/authority; no model-produced authority; truthful named effects |
| Evaluation/conformance | `evaluation/EVALUATION.md` §§1–3, `conformance/CONFORMANCE.md` §§1–5,8,17,25 | Missing evidence is not PASS; test results are not admission or certification |
| Plugins | `plugin-spec/PLUGIN-SPEC.md`, admission/configuration and §§16–18 | Installation/configuration do not grant authority; no blind retry after unknown effects |
| Accepted mechanisms | ADR-001–011, 014–016, 020–024 | Runtime/package mapping, owner-local state, authorization/dispatch/evidence/Secret boundaries, public host, personal-image policy and remote disclosure |
| Scoped implementation records | ADR-017/018/019; ADR-025 | 017/018/019 still say Proposed with scoped implementation authority. 025 says Implemented for review. None is silently relabeled Accepted |
| Consumption guidance | `docs/ASSEMBLING-APPLICATIONS.md`, `docs/modules/MODULE-CATALOG.md`, `packages/legoai-engineering/docs/CONSUMING.md`, package and consumer READMEs | Useful public entry and maturity guidance; stale snapshots cannot override current code or accepted decisions |
| Current/historical closure | `planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md` §§2–3 and stale-guidance register; `planning/LEGOAI-CONSUMER-READINESS-PLAN.md`; ForgeAI README qualification records | Scope-specific local/replay/remote-profile evidence; CR-1c media migration remains debt |
| Implementation and tests | Exact paths below and TSV | Concrete source supports findings; unexecuted tests indicate intended coverage, not observed success |

ADR-014's description of the old missing `runtime.api` is historical context, not a
claim that the facade is absent today. Its accepted public-host decision governs.
Likewise, older ADR-index allocation totals and module-catalog REMOTE/LQ1 status
sentences do not supersede later source and closure records. No material canonical
semantic contradiction requiring an intent amendment was established in this review.

## 4. Architecture conformance matrix

These are source-level assessments with the stated scope, not release statuses.

| Boundary | Implementation evidence | Assessment / limit |
| --- | --- | --- |
| Kernel/domain independence | `src/legoai/kernel/{context,effects,errors,versions}.py`; Core AST matrix | Stable values, not provider SDK objects; matrix/cycle checks exist but await fresh execution |
| Public composition | `src/legoai/runtime/local.py:open_local_host`; `runtime/api.py` | Core-owned internals are legitimate here; facade returns public contracts; no provider call merely to open the Model host |
| Owner dependency direction | `tests/architecture/test_import_boundaries.py:violations`, cycle traversal and known-bad fixtures | Existing detailed matrix is reused; this audit adds cross-distribution coverage rather than replacing it |
| Model/provider separation | `intelligence/model/ports.py:ModelPort`; `reference/model.py`; `reference/model_openai_compatible.py` | Provider protocols stay in adapters; closed host-selection branches are supported composition, not automatic OCP violations |
| Authority before remote effects | `runtime/_composition/model_governed.py:_invoke_chat`; `disclosure.py:DisclosureCheck` | Invocation claim, explicit disclosure decision, then remote call; preflight/rejection/uncertainty have distinct settlement paths |
| Model result is data | ForgeAI `worker.py:_attempt`, `review.py`; Engineering mutation/check wrappers | Exact proposal approval and current effect authorization precede apply/check; opinion never grants permission |
| Configuration | `runtime/local.py`; media `discovery.py:DRIVERS`; ForgeAI `composition.py` | Closed settings/bindings; no data-provided import path. Media env Secret resolution is an exception to complete governance, H-01 |
| Public/private consumer APIs | Inventory and new AST ratchet | FAIL for the known media/assessment edges; valid Core internals are not rewritten |
| Storage abstraction | DocuMind `app.py`; document `answering/api.py`, `ingestion/api.py`, `retrieval/api.py` | Concrete SQLite signatures are an acknowledged limited profile, not interchangeable storage; M-02 |
| Explicit failure/effect state | Kernel `EffectExtent`; governed Model settlement; media `GenerationResult`; ForgeAI task dispositions | Unknown/partial retained on reviewed paths; cancellation is not proof of external cessation |
| Optional packages | Document and media architecture tests; collation pure `collation.py` | Core does not need these application packs. Collation's precedence is not authorization |
| Browser package | `packages/legoai-browser-hand-landmarks/src/contract.ts`, `frame-pump.ts` | Browser-local contract, injected adapter, bounded busy/generation state and frame cleanup; full TypeScript/runtime conformance NOT_PROVEN here |

## 5. Consumer conformance matrix

| Consumer | Ownership and reuse | Effect/configuration evidence | Findings / qualification limits |
| --- | --- | --- | --- |
| ForgeAI | `domain.py:TaskRequest/TaskResult` own intent/acceptance; worker owns fixed application sequence; repository, Git, checks, CodingAgent and IndependentReviewer are reused | `composition.py:prepare_run` selects adapters/host/sandbox and wraps effects; `worker.py` validates proposal, exact operator decision and guarded apply, then bounded checks/review | No concrete provider SDK in inner modules observed. One rework, no retry loop. Runtime/model quality and Docker readiness are not proven by this audit |
| DocuMind | `app.py` owns extension mapping, ingress and document Q&A; optional document pack owns deterministic processing and answering composition | `composition.py:DocuMindRuntime` uses `open_local_host`, governed chat/embed; no current private Core import | Public host migration observed. Application constructs SQLite and traverses `runtime.config`; M-02. No RAG-specific changes to generic Core Retrieval/Memory observed |
| VTO / Generative Media | CLI acquires local PNGs; public `VirtualTryOnPort` and request values keep provider objects/host paths out of task inputs | `virtual_try_on.py:ComfyVirtualTryOnAdapter.try_on` checks local deployment before uploads, preflights nodes, then two uploads and one submission; reconciliation never resubmits | M-01 private host debt; H-01 credentialed-media Secret gap; M-04 constructor discovery. Image disclosure is separate from job effect; no remote personal-image support or CUDA qualification established |

ForgeAI remains a supervised bounded engineering application, not an autonomous
engineering organization. `MAX_ATTEMPTS = 2` represents the initial attempt and one
rework. `_attempt` approves the exact proposal identity before mutation; denial or
approver error stops. `_review` cannot apply/check/propose. Infrastructure failures
are not rework triggers. `TaskRequest.context` is read-only disclosure, not write
scope. `remote.py` and composition own deployment/disclosure settings. The worker's
workspace string is a lock/scope key, not a task-supplied host filesystem capability.
Autonomous RepositoryAnalyst work is not a ForgeAI v0.1 blocker.

DocuMind directly composes document functions; it does not need an Agent/Team simply
because it uses a model. A local operator tenant string is not production IAM.
`governed_chat`/`governed_embed` translate host errors into application exceptions;
this is a small CLI error surface, not a full reusable diagnostic envelope.

VTO validates/minimizes PNG metadata, reports `input_disclosure` separately, and
keeps completed generation effects even if output retrieval fails. Local ComfyUI
retention is not physical deletion, and environmental unavailability is not evidence
that the application code is incorrect. ADR-020's remote personal-image restriction
remains in force. Provider/job/workflow references in result values are attribution,
not authority or provider SDK leakage.

## 6. SOLID assessment

| Principle | Source evidence | Assessment |
| --- | --- | --- |
| SRP | Core `reference/application/codec.py` is large but serializes one owner; ForgeAI worker stages one bounded task; CLI renders/parses, composition binds infrastructure | PASS_WITH_FINDINGS: size alone is not unrelated responsibility. DocuMind app owns both task coordination and storage construction (M-02); hotspot review below |
| OCP | ModelPort, repository/mutation/check/sandbox Ports, media driver contract and injected document model callables | PASS_WITH_FINDINGS: existing substitutions are explicit. Local-host provider branches and the closed two-family media registry are intentional supported variation, not reasons for a generic plugin loader |
| LSP | Model preflight/uncertain/rejected exception categories; authorized wrappers pass through result/effect semantics; media lost-ack/retrieval tests | NOT_PROVEN for all implementations/environments. Existing offline contract tests are evidence designs; neither structural typing nor this review proves every provider preserves behavioral contracts |
| ISP | Small repository/check Ports and governed document callables; ModelPort exposes chat and embed | PASS_WITH_FINDINGS: the assessment factory supplies an unused embedding setting for a chat-only use (O-02). No demonstrated need to split the accepted ModelPort in this audit |
| DIP | ForgeAI worker imports Ports; Core public facade selects adapters; media package imports Core reference internals; document APIs explicitly type SQLite | FAIL for universal current-consumer conformity: M-01/M-02/M-03. No automatic API redesign performed |

## 7. DRY, KISS, YAGNI, SoC and Law of Demeter

| Principle | Assessment and concrete reasoning |
| --- | --- |
| DRY | PASS_WITH_FINDINGS. Root AGENTS/CLAUDE and the two full skills duplicated policy/workflow; L-01 corrects this. Media local-host wiring repeats Core host knowledge (M-01). Frozen evaluation contracts, replay cases and independent expected results are deliberate independence, not deduplication candidates |
| KISS | PASS_WITH_FINDINGS. Closed worker stages, direct document functions and closed provider-family selection are simpler than an invented workflow engine. Authorization/Secret/evidence wrappers protect distinct boundaries and are not redundant merely because there are several. See measured hotspots, O-01 |
| YAGNI | PASS_WITH_FINDINGS. No new platform abstractions justified by this audit. Existing foundational identities, effects and owner Ports are accepted semantics even where a single current consumer exercises them; no deletion justified solely by use counts |
| SoC | FAIL for a universal claim. Most reviewed effect/configuration paths separate concerns; concrete document storage and package-local host/Secret wiring are exceptions. CLI acquisition and presentation are legitimate outer concerns |
| Law of Demeter | PASS_WITH_FINDINGS. `documind_app/app.py:DocuMindApplication.__init__` reaches through runtime configuration to create parent directories and choose a store (M-02). This couples application lifetime to host/config structure. Immutable `revision.configuration.application.scope.tenant_id` comparisons in media composition are value validation, not an object-service navigation defect |

## 8. Findings by severity

Severity describes the affected scope and required response, not a claim that an
exploit or live failure was reproduced. Locations refer to the inspected baseline;
functions remain stable anchors after editorial changes.

### CRITICAL

None established in the reviewed paths. This is not proof that none exists elsewhere.

### HIGH

**H-01 — Credentialed media has no purpose-bound Secret-use enforcement. OPEN.**

- Location: `packages/legoai-generative-media/src/legoai_generative_media/config.py:370`
  (`resolve_secret`), `service.py:probe_provider/_driver`, `http.py:RemoteHTTPS`.
- Evidence: `env:NAME` resolves to a raw string; `_driver` and `probe_provider`
  pass it directly to a transport factory. There is no Secret-use decision/Grant,
  purpose-bound current-use check or Core Secret participant in these paths.
  The module explicitly calls this an adapter-local resolver. The master roadmap
  already records this qualification gap; newer Model SRCP-1 does not close it.
- Rule: ADR-010 §§1–2 and Security Secret-use obligations: possession/reference
  resolution is not permission for a use; capability invocation and Secret use
  are distinct. ADR-023's bounded Model profile is not blanket media permission.
- Impact: credentialed media cannot be claimed conformant to that security
  mechanism. Scope is credentialed media, not credential-free local VTO; no token
  leak or unauthorized live call was reproduced.
- Smallest correct remediation: keep credentialed-media conformance unproven;
  obtain a reviewed media Secret-use/host integration decision, then bind the
  actual credentialed acceptance boundary to it. Do not add a cosmetic SecretRef
  wrapper or extend Model authority by analogy.
- Owner: **governance + composition root + adapter**. Design change stopped here;
  it exceeds the permitted narrow audit fixes.

### MEDIUM

**M-01 — Generative Media consumes private Core host implementation. OPEN.**

- Location: `packages/legoai-generative-media/src/legoai_generative_media/composition.py:24–25`
  and `local_host.py:36–49`; every imported name is listed in the TSV.
- Evidence: 16 imported-name occurrences across seven module edges. `LocalSession`
  stores concrete Coordinator/Catalog objects; `prepare_local` reconstructs
  authority and lifecycle machinery outside the Core public host.
- Rule: ADR-002 §11, ADR-014 public composition and public-consumer boundaries;
  DRY for authority/host ownership. Existing CR-1c deferral explains, not removes,
  the debt. Same-distribution Core private use is a different case.
- Impact: Core internal changes can break a shipped optional package; duplicated
  composition must track control semantics. A Model-only host cannot safely be
  relabeled a generic media host just to eliminate imports.
- Remediation: review the media host capability boundary and migrate against an
  approved public surface, preserving media effect/retention semantics. The new
  fitness check prevents growth but is not a waiver or migration.
- Owner: **composition root / LegoAI capability**. Public API decision required.

**M-02 — Document storage and application wiring have concrete coupling. OPEN.**

- Location: `examples/documind/src/documind_app/app.py:DocuMindApplication`,
  `packages/legoai-document/src/legoai_document/{answering,ingestion,retrieval}/api.py`.
- Evidence: the application constructs `SQLiteRetrievalStore` and creates its
  parent directory via `runtime.config.index_path`; capability signatures name
  that store. `hybrid_search` calls its two concrete search methods.
- Rule/principle: composition ownership, DIP and SoC; LoD here has a concrete
  configuration/lifetime coupling consequence. Current documentation/roadmap
  acknowledges a local SQLite profile, not a storage-neutral Port.
- Impact: changing storage requires application/capability edits; it cannot be
  advertised as transparent adapter substitution. This is not RAG leaking into
  Core, nor evidence that the bounded local application is unusable.
- Remediation: first isolate store construction at the application composition
  boundary if needed. Introduce a storage Port only after a real second-store
  substitution requirement and compatible owner/failure semantics are established.
  Do not widen a generic Core Retrieval contract to fit this one application.
- Owner: **application composition + document capability**. API changes deferred.

**M-03 — Maintained assessment example still consumes private adapters. OPEN.**

- Location: `examples/assessment_starter/backend/src/assessment_starter/fixtures.py:4`,
  `model.py:15`, `model_factory.py:4`.
- Evidence: four imported names: FixedModel twice and Ollama adapter/config.
  `make_model` returns the raw Ollama adapter for the non-fixed branch; the app's
  old explicit direct-Model profile is not a governed public-host composition.
- Rule: public/private consumer boundary and current assembly guidance.
- Impact: copying this as the current recipe propagates private consumption and
  obscures the difference between direct fixture use and governed model effects.
- Remediation: README now labels the boundary and links the current public-host
  guide. Retain existing behavior; migrate the optional provider path through a
  separately reviewed composition change, not a public alias for private classes.
- Owner: **application composition + documentation**. Code migration deferred.

**M-04 — Remote VTO construction can discover before the local-only gate. OPEN.**

- Location: media `service.py:open_virtual_try_on/_driver`,
  `discovery.py:discover`, `config.py:ProviderConfig.api_family`,
  `tests/test_tryon_reuse.py:test_remote_config_builds_but_never_transfers`.
- Evidence: default family is `auto`; opening calls `_driver`, which resolves a
  token and awaits discovery. The auto branch probes both families. The local-only
  image refusal is later in `ComfyVirtualTryOnAdapter.try_on`. The existing remote
  construction test uses a fixture pinned to `legacy`, where discover does no I/O.
  `preflight_virtual_try_on` has an earlier guard, but is a separate entry point.
- Rule/principle: precise I/O/authority boundaries and ADR-020 fail-closed scope.
  The strong interpretation "remote VTO configuration causes no I/O" is not
  supported for direct construction. The trace does **not** show image upload
  before the guard; metadata discovery and personal-image disclosure differ.
- Impact: callers can contact a remote endpoint/use a credential while expecting
  refusal of an unsupported deployment to be entirely inert.
- Remediation: decide whether remote VTO construction must refuse immediately or
  build an inert refusal object; add an `auto` fixture with a fail-on-I/O transport.
  Preserve existing typed refusal semantics and no-upload guarantee. This changes
  an observable construction contract, so it is recorded rather than guessed.
- Owner: **composition root + governance + test only** for regression evidence.

### LOW

**L-01 — Agent policy/workflow had duplicate authorities. CORRECTED, validation pending.**

- Location: `AGENTS.md`, `CLAUDE.md`, both engineering-implementation `SKILL.md` files.
- Evidence: the root policy and full implementation workflow were duplicated
  between tools; they did not explicitly enumerate all requested ownership checks.
- Rule: DRY for normative knowledge and task §9 shared agent governance.
- Impact: tools can diverge on security, abstraction and validation instructions.
- Remediation implemented: shared policy in AGENTS, existing workflow in `.agents`,
  thin Claude references; explicit semantic-owner, Port justification, effect,
  reuse and design review rules. No new tool integration added.
- Owner: **documentation / agent governance**.

**L-02 — Active implementation guidance was stale. PARTIALLY CORRECTED.**

- Location: `packages/legoai-document/README.md:Current capabilities` and
  `src/legoai/runtime/_composition/disclosure.py` module docstring; also
  `docs/modules/MODULE-CATALOG.md` and older `adrs/ADR-INDEX.md` status snapshots.
- Evidence: document README said nothing beyond parsing/chunking was implemented;
  disclosure docstring said no public host constructed a gate. Current source
  contradicts those statements. Historical index/catalog status is already
  identified by the master roadmap's stale-guidance register.
- Rule: accurate implementation/evidence separation; no status from stale text.
- Impact: consumers can choose old composition paths or assume mechanisms absent.
- Remediation implemented: correct those two active descriptions and assessment
  warning, without changing runtime behavior. Historical/canonical index records
  are not rewritten or promoted by this audit.
- Owner: **documentation**.

**L-03 — Cross-distribution import coverage was fragmented. CORRECTED, validation pending.**

- Location: existing Core `tests/architecture/test_import_boundaries.py`, ForgeAI
  architecture tests and Document architecture tests; new
  `tests/architecture/test_consumer_private_boundaries.py`.
- Evidence: existing tests protect individual owners/apps; some inspect only the
  `ImportFrom.module`, so a parent import of a private child is not equivalent
  coverage. No unified exact-debt ratchet covered these production consumers.
- Rule: testable public boundaries and meaningful negative controls.
- Impact: growing legacy private consumption could escape otherwise green suites.
- Remediation: AST resolver handles parent imports, relative imports and imported
  module aliases/attributes, compares exact debt edges, and rejects reusable
  package imports of the three Python consumer applications. Positive and negative
  fixtures exercise the detection mechanism. No global static-analysis framework.
- Owner: **test only**.

### OBSERVATION

**O-01 — Complexity hotspots warrant scoped review, not automatic decomposition.**

- Location/evidence: static baseline measurements in §10. ForgeAI worker has 15
  declared constructor fields, including value/policy/callback fields, not 15
  independent infrastructure services. Its longest stage is `_attempt` (167 lines).
- Principle: SRP/KISS/operability; size/fan-out are signals, not violated limits.
- Impact: review cost and difficulty following effect order can grow.
- Remediation: when behavior changes, review stage boundaries and keep ordering
  explicit. Do not add a service locator or generic workflow just to shorten it.
- Owner: **application / composition / owner implementation**, depending on file.

**O-02 — Chat-only consumer exposes breadth of Model configuration.**

- Location: assessment `model_factory.py:make_model`; Core
  `intelligence/model/ports.py:ModelPort`.
- Evidence: `embedding_model="unused-by-assessment-starter"`; ModelPort has both
  chat and embed, while public host purposes distinguish them.
- Principle: ISP friction, not a proved LSP failure or mandate for another Port.
- Impact: direct-adapter recipes expose unused configuration to consumers.
- Remediation: prefer existing public purpose-bound host usage during M-03
  migration; require real substitution evidence before splitting interfaces.
- Owner: **application composition**, not a speculative new capability.

**O-03 — Local checks cannot settle all effect or quality claims.**

- Location: ForgeAI `domain.py:LIMITATIONS`, media `values.py:GenerationResult`,
  experiment `experiments/kaggle/forgeai_model_quality_1`, existing qualification logs.
- Evidence: check results are observations, review is model opinion, media stores
  job facts in memory, and the supplied quality-harness log says quality unmeasured.
- Rule: EVAL-002 and CONF evidence scope; missing evidence never becomes PASS.
- Impact: misreading fixture success as production correctness or model quality.
- Remediation: preserve the existing qualifications/unknowns; no blanket promotion.
- Owner: **evaluation / documentation / deployment**.

## 9. Cross-application reuse assessment

| Candidate | Independent consumers / semantic comparison | Decision |
| --- | --- | --- |
| Public governed Model invocation | ForgeAI and DocuMind: same Model operation/host authority and failure plane, different application content | Correctly reused already; no new provider-specific application Port |
| General public media host composition | Model consumers plus media repeat catalog/admission/dispatch mechanics, but media adds separate image disclosure, job effects and reconciliation | Real reuse pressure exists (ADR-014 historical comparison); M-01 still needs an approved public capability shape. Similar construction alone does not prove identical whole-operation semantics |
| Generic rework/workflow abstraction | ForgeAI rework, DocuMind ingest/answer and VTO upload/job ordering | Reject: different acceptance, effect and recovery semantics; application sequencing remains local |
| Secret-use mechanism | Credentialed Model and credentialed media both handle sensitive credentials | Reuse governance semantics, not Model-only SRCP-1 implementation authority. H-01 requires purpose/participant/acceptance-boundary decision |
| Shared path validator | ForgeAI repository-relative paths vs DocuMind local ingress vs VTO local PNG ingress | Reject: different traversal, symlink, acquisition/disclosure and write semantics |
| Shared result/error schema | ForgeAI patch/check/review, document citation quality and media job/disclosure | Reuse canonical effect/error vocabulary where applicable; keep owner-specific result facts |
| SQLite store interface | Only one demonstrated document store realization | No second independent storage requirement established; defer new Port pending M-02 evidence |
| Frozen evaluation contracts | Production contracts and isolated Kaggle quality fixtures | Deliberate independence. Do not import live production definitions just to remove duplicate text |

No application-specific ForgeAI task orchestration was found in Core along the
reviewed paths. Document answering inside an optional document capability pack is
not the same as placing DocuMind's CLI/extension mapping in generic Core.

## 10. Overengineering review and measured hotspots

Metrics are baseline physical source lines (including comments/docstrings) and
distinct imported targets, **not** cyclomatic complexity, runtime cost or a limit.
The inventory parser measured tracked Python source without executing it.

| File | Lines | Imported targets | Longest function (lines) |
| --- | ---: | ---: | --- |
| `src/legoai/reference/application/codec.py` | 1148 | 39 | `decode_publication_result` (77) |
| `src/legoai/runtime/local.py` | 949 | 108 | `open_local_host` (180) |
| `examples/forgeai/src/forgeai/cli.py` | 808 | 57 | `main` (108) |
| `src/legoai/governance/disclosure.py` | 799 | 9 | `evaluate_disclosure` (75) |
| `src/legoai/reference/execution.py` | 780 | 32 | `coordinate` (76) |
| `examples/forgeai/src/forgeai/composition.py` | 704 | 85 | `prepare_run` (189) |
| `src/legoai/reference/_remote_attempts.py` | 696 | 29 | `_decode_control` (50) |
| `examples/forgeai/src/forgeai/domain.py` | 663 | 27 | `__post_init__` (66) |
| `src/legoai/reference/_secret_ledger.py` | 593 | 29 | `accept` (90) |
| `examples/forgeai/src/forgeai/worker.py` | 590 | 57 | `_attempt` (167) |

High fan-out is expected at composition roots. Codec length reflects explicit
representations, not necessarily many unrelated responsibilities. Authorization
decorators, disclosure checks, custody and attempt state cover separate failure
boundaries; collapsing them would erase control/effect distinctions. No dead
production abstraction was proven by use-count analysis, and no speculative
abstraction was removed. Full fan-in, strongly connected component and cyclomatic
analysis was not performed; existing Core cycle fitness tests remain the executable
evidence mechanism. No arbitrary numeric rule was added.

## 11. Agent instruction assessment

Discovered repository instruction surfaces: root AGENTS/CLAUDE and the two existing
engineering-implementation skills. No additional tool entry point was needed.
Before the patch, their hierarchy was semantically consistent but duplicated;
there was no unresolved policy conflict requiring a guessed precedence decision.

The shared policy now explicitly addresses all requested review topics: reuse
before creation, minimum deterministic behavior, public consumption, adapter
isolation, no SDK in domain code, no model authority, truthful effects/retries,
configuration versus authorization, application ownership, all named design
principles, meaningful tests and no security weakening. A new Port must identify
its owner, independent consumers, expected implementations and substitution need.
Fix placement is by semantic owner. Skills remain workflow guidance under the
canonical specifications and accepted ADRs, not a replacement architecture.

## 12. Exact changes

| File | Change |
| --- | --- |
| `AGENTS.md` | Single shared policy; adds focused architecture/ownership review requirements |
| `CLAUDE.md` | Thin references to shared policy and existing workflow |
| `.agents/skills/engineering-implementation/SKILL.md` | Retains existing workflow, links policy and clarifies maintainer-run verification |
| `.claude/skills/engineering-implementation/SKILL.md` | Retains tool skill metadata; replaces duplicate workflow with shared-file references |
| `packages/legoai-document/README.md` | Corrects current capability/storage inventory without qualification claims |
| `examples/assessment_starter/README.md` | Marks legacy private adapter consumption and points to supported assembly |
| `src/legoai/runtime/_composition/disclosure.py` | Module docstring only: current public host does construct remote gates |
| `tests/architecture/test_consumer_private_boundaries.py` | Cross-distribution AST ratchet and meaningful controls |
| `tests/architecture/test_package_install.py` | Adds the new architecture test to the exact source-distribution manifest; retains strict equality and wheel isolation checks |
| `validate_architecture_design_conformance_audit_1.py` | Offline, fail-fast maintainer checks; scope guard and unchanged runtime AST comparison |
| This report and companion TSV | Findings, exact snapshot import occurrences and scoped classification |

No dependency, public API, canonical semantic record or executable runtime logic
changed. No commit was made. The source docstring correction is explicitly guarded
by comparing the baseline/current module AST with the module docstring removed.

## 13. Fitness functions, evidence inventory and validation

Existing checks retained:

- Core `tests/architecture/test_import_boundaries.py`: owner matrix, inert exports,
  forbidden adapter edges, transitive restrictions, cycles and known-bad fixtures.
- Core host, remote disclosure/Secret/custody/attempt architecture files: public
  composition and closed security ownership.
- ForgeAI `tests/test_architecture.py`: inner-layer restrictions, public imports,
  effect/Grant creation restrictions, composition-only adapters, one rework and
  non-effectful review; runtime behavior has separate worker tests.
- Engineering `tests/test_architecture.py`, `test_authorized_effects.py`,
  `test_consumer_readiness.py`: public consumption and current denial before effects.
- Document `tests/architecture`; DocuMind `test_public_composition.py`: public
  host and provider-free construction, safe refusal without retry.
- Media `test_architecture.py`, `test_tryon_composition.py`: no Core dependency on
  the pack, provider-free task values, upload/submission ordering and effect truth.

New fitness functions use ordinary `ast`, following the existing tests' style:

1. Resolve normal, aliased, parent and relative import spellings without loading code.
2. Ratchet exact existing private consumer edges across Core, Python package `src`
   trees, current example `src` trees, assessment backend and root Python examples.
   A removed edge also forces retirement of its debt entry. There is no broad
   whole-package waiver. This check does not call the known debt conformant.
3. Reject imports from reusable Python packages into ForgeAI, DocuMind and the
   assessment application, including imported child names.
4. Positive/negative controls cover public Ports, legitimate owner-internal access,
   `from legoai import reference`, aliased private imports, imported private symbols,
   imported-module private attribute access, and relative resolution.

Static limitations: this is not a Python sandbox or general data-flow analysis.
Reflective access, alias reassignment, arbitrary dynamic import strings and private
members reached through returned objects need owner-specific review. Tests/evaluation
trees are outside the production ratchet but included in the baseline inventory.

The TSV records **773 imported-name occurrences**: 275 valid owner-internal,
456 test-only/qualification-fixture uses, 22 historical-example uses, and 20
cross-owner production violations. Each row supplies exact file, line and target.
Test classification permits focused mechanism/negative fixtures and qualification
tools; it does not make private APIs public or approve live execution. Historical
`examples/{agent,model_port,model_routing}.py` demonstrate old offline technical
composition; assessment is separately flagged because its maintained application
and optional provider path are active consumption. Same-owner private helpers in
Engineering, Collation and Core remain internal implementation. Here, the inventory's
owner classification is at the distribution boundary: for example Core's shared
`kernel.identity._validate` is not a public extension API. This classification
alone does not prove every internal logical-owner edge; the Core dependency matrix
and its separate tests remain necessary. Public names whose
privacy is only implicit in prose, and runtime object member accesses, are not an
exhaustive part of this syntactic inventory; the targeted findings cover the
concrete Coordinator/Catalog and SQLite coupling observed in source.

Maintainer command from the repository root (existing locked environment only):

Prerequisites: the existing root environment and
`packages/legoai-engineering/.venv`. Engineering's isolated-import tests use its
own installed package environment because Python `-I` ignores `PYTHONPATH`.
The validator refuses a missing environment and does not create or synchronize it.

```powershell
uv run --locked --offline --no-sync python .\validate_architecture_design_conformance_audit_1.py
if ($LASTEXITCODE -ne 0) { throw 'Architecture conformance audit validation failed' }
```

The script checks exact audit scope and shared instruction links, runs Core and
consumer architecture checks plus selected deterministic authorization/public-host/
VTO effect regressions, then mypy, Ruff lint/format and working/staged whitespace.
It installs nothing, makes no live provider requests and performs no Docker
acquisition. Existing wheel-isolation tests may build/install the local wheel into
a temporary environment. The chosen deterministic tests use fixtures/spies rather
than a live provider. Offline environment flags prevent dependency acquisition;
they are not a general network sandbox. No broad runtime regression is claimed:
the only runtime source edit is a docstring, guarded by AST equality. Full model
quality, Docker, GPU, live provider and browser camera suites are not part of this
validator. Its scope guard intentionally refuses unrelated edits from this baseline.

Required outcome: all listed local phases pass. The final message must still retain
the recorded debt and state that neither live nor global conformance is qualified.
Do not mark the audit locally validated until the maintainer supplies the log.

## 14. Claims still not proven

- Universal implementation or consumer conformance: known violations remain.
- Credentialed media purpose-bound Secret compliance; no exception inferred from
  Model-only SRCP-1 or from credential possession.
- Remote VTO constructor inertness with automatic discovery; M-04 is a static trace,
  not a reproduced live call or personal-image exfiltration claim.
- All adapter LSP obligations across providers, network failures and cancellation;
  static typing and selected fake transports are not sufficient proof.
- Distributed recovery, hostile plugin isolation, multi-tenant production IAM,
  durable whole-host execution, universal exactly-once or physical provider deletion.
- Live ForgeAI coding quality, model quality on Kaggle/Colab, or current GPU/VTO
  availability. Successful synthetic/no-provider harness checks prove none of these.
- Complete Python dynamic dependency or TypeScript/browser conformance, or that no
  vulnerability exists outside the reviewed control-flow paths.
- Complete local validation after the formatting correction; the latest supplied
  log passes tests, typing and lint, but stops at format before whitespace checks.

### Maintainer validation follow-up

The supplied audit-validator log reports **422 passed, 1 failed** in the Core and
consumer architecture phase. The sole failure is
`test_package_install.py::test_build_and_fresh_wheel`: the source archive correctly
contains `tests/architecture/test_consumer_private_boundaries.py`, but the exact
expected manifest omitted that newly added file. The new fitness tests passed in
this run. Engineering, deterministic consumer regressions, typing, lint, format
and whitespace phases were not reached.

Correction: add only that expected archive member, allow the packaging test in the
audit validator's change scope, and include it in typing/lint/format checks. The
manifest equality assertion remains strict; no packaging check is skipped or
relaxed. The correction has not been executed internally. Rerun the same full
maintainer command in §13; overall local validation remains pending.

The subsequent maintainer run reports **423 Core/consumer architecture tests,
133 Engineering tests and 16 public-host/VTO tests passed** (572 total), plus
successful typing of four files and lint. Formatting alone stopped this run:
Ruff requires `[: -node.level]` for the relative-import slice. That exact spacing
correction is applied without behavioral changes. Working/staged whitespace
checks were not reached. No checks were run internally; overall validation remains
pending the maintainer's rerun.

## 15. Separate audit verdicts

These are limited static audit conclusions, not canonical status promotions. FAIL
means a known scoped mismatch prevents a universal current-implementation claim;
NOT_PROVEN is not silently converted into FAIL or PASS.

| Dimension | Verdict | Basis |
| --- | --- | --- |
| ARCHITECTURE | PASS_WITH_FINDINGS | Accepted owner/effect model is coherent; media/public host and credential profile decisions remain necessary |
| IMPLEMENTATION | FAIL | H-01 and M-01/M-03 prevent all-path conformance; fresh checks pending |
| SOLID | FAIL | Known DIP mismatches prevent all-principle conformance; SRP/OCP/ISP retain scoped findings and LSP breadth is unproven |
| DRY | PASS_WITH_FINDINGS | Instruction duplication corrected; host knowledge duplication remains |
| KISS | PASS_WITH_FINDINGS | Bounded consumers, no speculative framework; measured hotspots need scoped review |
| YAGNI | PASS_WITH_FINDINGS | No new abstraction justified; current foundational semantics retained, dead-code absence unproven |
| SOC | FAIL | Concrete storage/application coupling and media host/Secret integration gaps |
| LAW_OF_DEMETER | PASS_WITH_FINDINGS | Concrete DocuMind runtime/configuration reach-through; immutable value navigation not penalized |
| CONSUMER_CONFORMANCE | FAIL | ForgeAI's reviewed shape is sound; DocuMind storage limitation and media/assessment private consumption remain |
| AGENT_SKILL_GOVERNANCE | PASS_WITH_FINDINGS | One policy/workflow with tool wrappers implemented; local link/scope validation pending |

Canonical decision: no change to intent/SPEC/Architecture/Contracts is proposed to
excuse these findings. H-01 and M-01 need accountable mechanism/public-host design
review before implementation; M-04 needs a precise construction contract decision.
None is made implicitly by this audit. Await the maintainer's validation results;
this report does not authorize or recommend execution of a new implementation slice.

Proposed commit message:

```text
test(architecture): audit consumer boundaries and unify agent guidance
```
