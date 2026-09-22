# Python-first direction: repository impact assessment

Date: 2026-09-22. Scope: maintainer-requested strategic amendment and the
first engineering foundation milestone. This is a source/document inspection,
not a new execution or release qualification record.

## Current architecture and preserved baseline

`legoai-reference` distributes `src/legoai` on CPython 3.14. ADR-001 already
selects Python; ADR-002 separates Kernel, owner values/Ports, reference
implementations and private runtime composition. The root has no runtime
dependencies. Catalog discovery, resolution, authorization, dispatch and
execution are separate responsibilities. ADR-003 through ADR-011 and ADR-015
retain configuration, state, security, admission, resource, replay, evidence,
Secret, release and supervision responsibilities.

`legoai.intelligence.model` owns typed chat/embedding contracts and ModelPort.
`legoai.reference.model` supplies Ollama; private `model_governed` wiring binds
the selected offer and maps provider failures to execution/effect results.
`packages/legoai-document` implements parsing, chunking, embedding, retrieval,
rerank, ingestion and answering. `examples/documind` wires the runtime and
injects governed model calls into that pack. Core never imports the application.

[V0.1 release readiness](V0.1-RELEASE-READINESS.md) records user-confirmed
1362 Core tests, Document Pack 295 passed/64 skipped, DocuMind 15 tests,
typing/lint, wheels and clean-installed live Ollama use. These are historical
results, not results rerun for this change. Its qualified local single-operator
scope remains valid; it does not establish distributed replay, hostile Plugin
isolation, durable operation history, or general production readiness.

## Impact classification

| Item | Classification | Exact disposition / reason |
|---|---|---|
| `intent.md` §§1, 4, 24, 39, 43, 49, 55 | AMEND | Preserve 1.0 body; link a versioned amendment distinguishing implementation priority from semantic neutrality. Python reuse becomes the delivery policy beyond the first runtime; no mirrored language implementations are required. §55 supplies the change process. |
| `SPEC.md` §§1, 4.2, 4.5, 4.6 | NO_CHANGE | Independent Capability use, Agent, Skill and Workflow already have canonical meaning. No Python syntax becomes a canonical contract. |
| `architecture/ARCHITECTURE.md` AR-01–08, §§4–5 | NO_CHANGE | Existing owners/dependency matrix already support capability packs and replaceable adapters. Do not turn the composition hierarchy into mandatory imports. |
| `contracts/CONTRACTS.md` CTR-001–004, §§5–6 | NO_CHANGE | Operational envelopes, authority, effect and replay rules remain binding. Pure preparatory data values are not an operational envelope. |
| `adrs/ADR-INDEX.md` | AMEND | Add ADR-016 to the living register and correct current counts. Keep historical backlog/acceptance records; ADR-014 remains unallocated, ADR-012/013 Proposed. |
| `adrs/ADR-016.md` | NEW_ADR | Establish ongoing Python-first component delivery and incremental external pack strategy, distinct from ADR-001's initial runtime choice. Record alternatives, burdens, migration and upstream amendment; an ADR alone cannot amend intent. |
| Forward planning | AMEND | Add dependency-ordered plan and current pointer in `NEXT-CORE-IMPLEMENTATION-BATCH.md`; old Gate and v0.1 plans remain historical evidence. |
| `README.md` | CLARIFY | State current product direction, actual implemented packages, next milestone and limitations without claiming Agents/Teams exist. |
| Package structure / root `pyproject.toml` | NO_CHANGE | Keep coordinated Core distribution and current Python baseline. Do not rename or split existing packages. New engineering pack is additive and contains an actual pure implementation and intake consumer. |
| Model implementation | NO_CHANGE | Existing ModelPort/Ollama remains. A separate provider package is triggered by an actual new provider consumer, not relocation for appearance. |
| Document Pack / DocuMind | NO_CHANGE | Preserve capability names, behavior, reusable/application separation and existing validation history. |
| Runtime composition | DEFER | Private wiring is not a supported third-party facade. ADR-014 authoring/composition decision and qualification precede supported engineering/ForgeAI runtime APIs. |
| SECURITY / CONFORMANCE / EVALUATION / Plugin Spec | NO_CHANGE | External enforcement, scoped evidence, admitted contributions and evaluation separation remain mandatory. No new supported operational profile is claimed. |
| Skill implementation | DEFER | SPEC §4.5 already defines a versioned expertise asset; Capability + Workflow composition suffices until a consumer needs reusable expertise content/versioning. Do not redefine Skill as merely a procedure. |
| Agent / Workflow / Team implementation | DEFER | Add minimum canonical subsets only after engineering dependencies and consuming scenarios are demonstrated. |
| MCP / A2A / framework integration | DEFER | Protocol/framework adapters require actual consumers and security/failure qualification; no core protocol fields now. |

## Canonical tension and resolution record

| Document/section | Current rule | Proposed rule | Reason / migration impact |
|---|---|---|---|
| Intent 1.0 §1 | Language-neutral platform vision | Semantics remain neutral; primary maintained reusable implementation is Python | Corrected product scope, no code/data migration |
| Intent §4 | No conceptual language/framework dependence | Keep rule; Python-first is an implementation investment policy | No framework or language type becomes semantic authority |
| Intent §§24, 39 | Multiple reuse boundaries; language-neutral contracts; illustrative future SDKs | Python components once, adapters/protocols for other consumers; SDKs only on demonstrated demand | No obligation to port each capability; existing contracts unchanged |
| Intent §43 | Lego AI is not a Python-only library | Retain cross-language interoperability and independent conforming implementations while prioritizing the Python ecosystem | Python-first must not be interpreted as Python-exclusive |
| Intent §49 | First slice proves architecture; eventual alternate Port implementations | Retain replacement tests; real consumers drive alternate production implementations | No speculative production provider or mirrored language work |

The maintainer's request explicitly authorizes the corrected direction, an
appropriate amendment, and the first dependency-ordered milestone. Resolve
the tension through intent §55: this assessment, ADR-016, recorded static
alignment review, and `intent-amendments/IA-001.md`, linked from intent.
The amendment is issued under that maintainer direction, not authority
invented by an implementation ADR. No remaining conflicting canonical behavior
is needed for the selected milestone. Historical version references retain
their meaning; future work reads intent 1.0 together with IA-001.

## Selected first milestone and risks

M1 implements bounded literal inspection of caller-supplied repository text
and a small repository-intake example consuming it. This is preparatory
engineering functionality, not a registered/live `repo.inspect` invocation,
repository acquisition adapter, or general Agent foundation. It comes first
because typed bounded inputs and deterministic results can be established
without unsafe host access or premature public runtime authoring semantics.

The next consumer is repository analysis inside the engineering workflow;
the included intake example provides the first concrete consumer. Do not add
universal Repository/Artifact/Agent base types. Input text is untrusted data;
path labels are never dereferenced or treated as authority or provenance.
The result is a coordinate report over supplied content, not a canonical
Snapshot, Artifact, Evidence record, test verdict, or authorized action.

Risks: new package coordination; limits that later consumers may outgrow;
mistaking input labels for filesystem security; conflating deterministic
inspection with semantic review; expanding private runtime use. Mitigations:
small explicit contract, independent installation/boundary tests, no I/O,
documented limits, no runtime-private imports and explicit later gates.

Expected changes: this assessment; IA-001 and intent pointer; ADR-016 and
index; forward plan and next-work pointer; README; engineering pack metadata,
pure source, intake example and requirement-derived tests. No baseline
runtime, document code, canonical entity definition or lockfile is rewritten.
