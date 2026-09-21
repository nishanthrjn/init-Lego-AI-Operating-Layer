# Next Core Implementation Batch

**Document:** `planning/NEXT-CORE-IMPLEMENTATION-BATCH.md`
**Status:** PROPOSED — IMPLEMENTATION BATCH
**Authority chain respected:** intent.md → SPEC.md → ARCHITECTURE.md → CONTRACTS.md → PLUGIN-SPEC.md → SECURITY.md → EVALUATION.md → CONFORMANCE.md → Accepted ADRs (001-011, 015) → `planning/IMPLEMENTATION-READINESS.md` (**ACCEPTED — IMPLEMENTATION READINESS PLAN**, confirmed directly, 2026-09-20 — defines the four Gates cited in §2) → `planning/GATE-1-FOUNDATION-IMPLEMENTATION.md` (PROPOSED — FOR IMPLEMENTATION REVIEW, but its F0-F2 prescriptions are already implemented and verified — see §1) → `planning/runtime/LOCAL-PERSISTENCE-REALIZATION.md` (ACCEPTED) → this document.
**This document does not amend, reopen, or contradict any accepted document, ADR, or the Gate-1 plan.** It is the missing "exact coding task" specification for the next work item that plan's own §14 table names but does not expand — exactly as §21-23 expanded F0, F1, and F2 into full task specifications.
**Relationship to DocuMind extraction:** `planning/DOCUMIND-EXTRACTION-ASSESSMENT.md` and `planning/documind/EMBEDDING-CAPABILITY-DESIGN.md` are consulted here only as a **real future consumer/validation case** (§15), never as an authority over LegoAI Core architecture (§17's own instruction, honored throughout).

---

## 1. Verified current implementation state

Read directly from source, not from prior summaries:

**`src/legoai/` tree (complete listing, confirmed unchanged since the DocuMind extraction batches began):**
```
legoai/__init__.py, py.typed
legoai/kernel/{__init__.py, identity.py, references.py, versions.py, context.py, errors.py, effects.py}
legoai/application/{__init__.py, values.py}
legoai/governance/{__init__.py, values.py}
legoai/reference/{__init__.py, application/{__init__.py, configuration.py}}
```
No `legoai/capabilities`, `legoai/execution`, `legoai/tools`, `legoai/resources`, `legoai/plugins`, `legoai/observability`, `legoai/evidence`, `legoai/runtime`, or `legoai/intelligence` package exists anywhere in the repository. `legoai/kernel/provenance.py` (named by ADR-002's own package map) does not exist yet either.

**`tests/` tree:** `tests/architecture/{test_import_boundaries.py, test_package_install.py}`, `tests/unit/{application/test_configuration.py, governance/test_context.py, kernel/{test_foundation.py, test_identity.py}}`. 150 tests, all passing (directly re-run: `uv run --locked --no-sync python -m pytest` → `150 passed`).

**F0/F1/F2 verification records** (`docs/development.md`, dated 2026-09-21, confirmed by direct reading): F0 verified; F1 verified (96 pytest cases at that point, including F0 regressions); F2 verified (150 tests total, 173 statements / 106 branches covered with none missing on the two F2 source packages). The document's own final line states explicitly: **"F3/F4 were not started."**

**`planning/runtime/LOCAL-PERSISTENCE-REALIZATION.md`** (the Gate-1 plan's own F3 work item): confirmed **`Status: ACCEPTED — IMPLEMENTATION DECISION`**, dated 2026-09-20, selecting local SQLite via stdlib `sqlite3` as the reference persistence realization, with an explicit qualification map. This is a decision record, not an implementation — no SQLite code exists yet, and none is proposed by this batch (§7, §12).

**Conclusion: F0, F1, F2 are implemented and verified. F3 is accepted (decision only, no code). F4 has not been started.** This matches `docs/development.md`'s own explicit statement exactly — nothing here is inferred from filenames alone.

---

## 2. Current gate

**Gate 1 (Foundation, per `IMPLEMENTATION-READINESS.md`'s own four-gate framework — Gate 1 "Source Start," Gate 2 "Governed Executable Slice," Gate 3 "ForgeAI Start," Gate 4 "First Usable Release") is in progress, not complete. F0-F3 are done (F0-F2 as working, tested code; F3 as an accepted decision record). F4 is the next work item on the Gate-1 critical path. Gate 2 has not begun in any respect.**

This is stated exactly, not approximately, per `IMPLEMENTATION-READINESS.md`'s own Gate 2 disposition ("Current disposition: not passed. Decisions alone do not meet any implementation proof item," directly confirmed by reading that document) and the Gate-1 plan's own verification-record language ("Gate 2 is **not passed**; ForgeAI runtime consumption is **not authorized**; supported release and production are **not ready**" — `GATE-1-FOUNDATION-IMPLEMENTATION.md` §1), and confirmed independently by the current source tree (§1 above) matching exactly what F0-F2 (and only F0-F2) are supposed to produce. Gate 2's own nine numbered proof conditions (per `IMPLEMENTATION-READINESS.md` §11) include ADR-015 supervision being implemented (not merely accepted), demonstrated storage atomicity/durability/recovery under actual fault tests, and enforced (not merely represented) Principal/Tenant/Policy/resource/custody controls — none of which F4 attempts or claims (§5.2).

Gate 2 requires (per the Gate-1 plan §18.2's "Remaining Gate-2 blockers" table, cross-checked against ADR-INDEX's dependency matrix): qualified persistence under real failure scope (ADR-004/008/009), finite independent trust roots (ADR-005/006/009), current owner-boundary enforcement (ADR-005), Resources and Approval (ADR-007), real Plugin lifecycle/Catalog (ADR-006), Evidence custody (ADR-009), supervision (ADR-015), a protected Tool/Adapter, final dispatch arbitration (ADR-007), and retry/reconciliation (ADR-008) — none of which exist yet, and none of which this batch attempts to complete in full (§12).

---

## 3. First-executable-slice dependency graph

Derived directly from the Gate-1 plan's own critical path (§14.1) and the accepted-ADR "Depends on" relationships in `adrs/ADR-INDEX.md`'s dependency matrix (both independently re-confirmed against source, not merely quoted):

```text
F0 Kernel identity           [DONE]
   ↓
F1 Kernel refs/versions/context/errors/effects + Governance values   [DONE]
   ↓
F2 Application values (pure configuration capture/composition)       [DONE]
   ↓                                    ↘
F3 Persistence decision record          F7 inert Plugin/Capability
   [ACCEPTED — decision only]              declarations (safe parallel
   ↓                                       track; not selected this batch,
F4 Owner operation/result/duty            see §9)
   values + storage Port
   (Application + Evidence + Kernel
   provenance)   ← THIS BATCH
   ↓
F5 Versioned owner codecs + migration mechanics
   ↓
F6a First SQLite compound owner commit (real persistence, still Gate 1)
   ↓
F6b Actual recovery/failure qualification
   ↓
F9 Foundation exit review  →  GATE 1 COMPLETE
   ↓
[Gate 2 begins: ADR-015 supervision; ADR-005 real enforcement; ADR-006
 Plugin admission/Catalog; ADR-007 dispatch/resource claims; execution
 substrate]
   ↓
legoai.capabilities (real CapabilityResolver, not F7's inert declarations)
   ↓
legoai.execution (governed Execution, ExecutionContext, Direct invocation driver)
   ↓
legoai.intelligence.model (ModelPort) — Embedding's actual prerequisite (§15)
   ↓
Ollama Adapter → EmbeddingCapability
```

No dependency here is invented for this task — every arrow above is either the Gate-1 plan's own explicit critical-path diagram, or the explicit "Depends on" relationship already recorded in `ADR-INDEX.md`'s matrix for ADR-004 (depends on ADR-002), ADR-005 (depends on ADR-003), ADR-006/007/008/009 (each depending on combinations of ADR-003/004/005/009), and ADR-015 (depending on ADR-001/002/004/005/006/007/008/009 — the widest dependency set of any accepted ADR, consistent with supervision being correctly placed after the foundation substrate, not before it).

---

## 4. Package readiness matrix

| Package | Classification | Exact blocker / authority |
|---|---|---|
| `legoai.kernel` | **READY_NOW** (extension only) | F4 needs exactly one new module here: `kernel/provenance.py`, already named by ADR-002's own package map (§8 source tree) and by the Gate-1 plan's F2/F4 row ("`configuration.py`, `provenance.py` — LATER F2/F4, shared anchors only"). No blocker. |
| `legoai.application` | **READY_NOW** (extension) | `values.py` exists (F2); `ports.py` does not exist yet and is exactly F4's scope, per Gate-1 plan §14 F4 row and §6's Port table ("Configuration owner storage — Implement an owner-specific Protocol, privately supported, declared in `application.ports`"). No blocker. |
| `legoai.evidence` | **READY_NOW** (new, narrow) | `values.py` does not exist; F4's own scope explicitly includes it ("Source/requirement/reference values now; operating custody Port deferred" — Gate-1 plan §6). This batch creates only the values F4's own operation/duty types need, not a full Evidence subsystem. |
| `legoai.governance` | **READY (no work needed this batch)** | `values.py` already exists (F1); F4 references `Principal`/`OperationContext` from it but does not need to extend it. |
| `legoai.capabilities` | **PARTIAL / DEFER (safe parallel track, not selected)** | Legally startable now per its own F7 dependency ("F1/F2; F4 refs if actually used" — Gate-1 plan §14) — i.e., it does *not* strictly require F4 first. Deliberately not selected as *this* batch because a solo maintainer should not split shared-foundation work across two unrelated owners at once (Gate-1 plan §14.2's own explicit guidance), and F4 sits on the critical path to persistence/execution while F7's inert declarations do not. See §9 for the explicit exclusion. |
| `legoai.execution` | **BLOCKED** | Gate-1 plan §4.1 explicitly: "Do not create `execution`... just to complete a diagram. Their first real consumers arrive in Gate-2 work or later." Requires governed authorization (ADR-005 real enforcement) and dispatch ordering (ADR-007) neither of which exist yet. |
| `legoai.resources` | **BLOCKED** | Same instruction; requires ADR-007 (Resources and Approval), a named Gate-2 blocker (Gate-1 plan §18.2). |
| `legoai.tools` | **BLOCKED** | Same instruction; no protected Tool/Adapter target exists, itself a named Gate-2 blocker. |
| `legoai.plugins` | **PARTIAL / DEFER (F7, safe parallel track)** | Inert-declaration values are legally startable (dependency: F1/F2, already satisfied) but not selected this batch for the same solo-maintainer-focus reason as `capabilities`. Real Plugin lifecycle/admission (ADR-006) remains Gate-2, explicitly blocked regardless. |
| `legoai.observability` | **PARTIAL / DEFER (F8a, safe parallel track)** | Dependency is F1 only (already satisfied) — technically startable in parallel, per Gate-1 plan §14.2's own list of "safe independent tracks." Not selected: no current consumer exists yet in this batch's own scope (F4 does not require a diagnostic sink to be tested; a Gate-1-plan-conformant F4 uses direct pytest assertions, not observability output). |
| `legoai.runtime` | **BLOCKED** | Depends on F2/F7/F8a existing first (Gate-1 plan §14, F8b row); the private composition root has nothing to wire yet beyond what F2 already demonstrates. |
| `legoai.reference` | **PARTIAL** | `reference.application.configuration` exists (F2). F4 does not add a new `reference/` module (the SQLite realization is F6a); F4's storage Port is tested only against an in-memory test fake (`tests/support/`), per Gate-1 plan §9.1's explicit instruction: "Use a small test-only in-memory implementation of the same owner storage Protocol... Put it in `tests/support`, never ship it as a runtime fallback." |
| `legoai.intelligence` (reserved, not in ADR-002's 12 initial groups) | **BLOCKED, confirmed independently by the Embedding assessment** | Not part of Gate 1 at all; ADR-002 §7.3 names it a "reserved future logical location," gated on a "future independent Model slice" being separately authorized — see `planning/documind/EMBEDDING-CAPABILITY-DESIGN.md` §22 for the full analysis, reconfirmed here rather than merely cited. |

---

## 5. Selected next batch: **F4 — Owner operation/result/duty values and storage Port**

This is not a new selection invented by this task — it is the Gate-1 plan's own next-named work item (§14 table, critical path §14.1: `F2 → F4`), given the exact same level of detailed specification F0 (§21), F1 (§22), and F2 (§23) already received in that plan. F3 being accepted (§1) removes the only thing that could have deferred it.

### 5.1 Exact scope — what this batch WILL implement

Per the Gate-1 plan's own F4 row (§14) and its cross-referenced sections (§6 Ports table, §8.3 ADR-004 mapping, §9.1 first-owner selection):

1. **Owner operation/result/duty value types**, added to `legoai.application.values`: a representation of (a) an *operation descriptor* (what was requested, its expected prior revision or explicit absence, per ADR-008's operation-identity/equivalence semantics), (b) a *retained result* (committed stage, resulting revision(s), effects, errors if any, coverage — per ADR-004 §9 "Acknowledgment and retained operation results" and ADR-008), and (c) a *pending obligation* record for the one canonical qualification case the Gate-1 plan names: a post-commit **source-submission duty** (ADR-009's evidence-obligation shape, applied narrowly — not a general Evidence subsystem).
2. **`legoai.kernel.provenance`** (new Kernel module, named by ADR-002's own package map): the shared, cross-owner anchor types that F4's operation/result/duty records need to reference (e.g., a provenance-reference shape distinct from `SourceProvenance` in `application.values`, which is content-specific to the configuration fixture — `kernel.provenance` is the narrow, owner-neutral anchor other future owners will also need, matching Kernel's existing "only shared anchors needed by the selected owner contracts" scope rule from Gate-1 plan §4.1).
3. **`legoai.evidence.values`** (new package, narrow scope): only the source-fact/requirement/reference value types F4's own duty record actually needs — explicitly **not** a custody Port, not a receipt implementation, not an Evidence owner/custodian. Gate-1 plan §10.4: "Add exact Evidence/source fact/requirement/provenance reference values required by configuration results and duties... Receipt representation may be added only when a test genuinely consumes its validation... It cannot issue an Evidence-owner identity or satisfy a runtime barrier."
4. **`legoai.application.ports`** (new module): one owner-specific `Protocol` for the configuration-owner's storage boundary — publish-under-expected-revision, exact-revision read, retained-operation-status lookup, and bounded pending-obligation listing. Modeled as specific named operations, **not** generic CRUD (Gate-1 plan §6: "Model those operations, not generic CRUD. This is an internal realization boundary, not an unauthenticated service API.").
5. **A test-only in-memory implementation of that Protocol**, in `tests/support/` (per Gate-1 plan §9.1, explicitly never shipped as a runtime fallback), exercising the same scoped revision/equivalence/obligation vectors the eventual real (F6a, SQLite) implementation must also satisfy.
6. **Contract tests** proving the Protocol's semantics against the test fake: expected-revision/absence guard correctness, exact duplicate-descriptor (operation-equivalence, ADR-008) handling, pending-duty enumeration, and tenant/owner scoping — all synchronous, all in-memory, zero external services.

### 5.2 Exact scope — what this batch WILL NOT implement

Stated explicitly, per this task's own instruction not to let a bounded batch secretly grow:

- **No SQLite, no real file I/O, no database, no migration code** — that is F5 (codecs/migration mechanics) and F6a/F6b (the actual SQLite realization and its failure/recovery qualification). F4 is a values-and-Protocol-only batch, proven against an in-memory fake.
- **No Evidence custody Port, no Evidence owner/custodian, no receipt issuance** — only the narrow value types F4's own duty record needs (§5.1 item 3). A full custody subsystem is explicitly named Gate-2 scope (Gate-1 plan §10.4, §18.2).
- **No `legoai.capabilities`, no `legoai.plugins`, no inert declarations** — those are F7's scope, a separate, deliberately-not-selected safe-parallel track (§4, §9).
- **No `legoai.execution`, no ExecutionContext, no CapabilityResolver, no dispatch, no authorization enforcement** — all explicitly Gate-2 (Gate-1 plan §4.1, §18.2), and none of ADR-005's *real* enforcement, ADR-006's Plugin admission, or ADR-007's dispatch ordering is implemented here — only the *value-level* vocabulary F4 needs (which already exists from F1's `Principal`/`OperationContext`/`TenantContext`) is reused, not extended with new authority semantics.
- **No Model, Agent, Embedding, Ollama, vector, or any AI/provider dependency of any kind** — per this task's explicit §6 instruction, and consistent with the fact that nothing in F4's own scope (owner-local configuration-revision bookkeeping) has any relationship to AI capabilities at all.
- **No observability sink, no diagnostic records** — F8a is a separate, not-yet-selected track; F4's tests use direct assertions, not logged output.
- **No new runtime dependency** — F4 remains within the zero-runtime-dependency Kernel/Application/Governance/Evidence value-layer, exactly like F0-F2.

### 5.3 Why this batch, and not an alternative

The task's own candidate list ("Capability identity/requirement/offer values," "Execution identity/state values," "minimal Application declaration," "Port contract foundations") was evaluated against actual repository evidence, not assumed:

- **Capability identity/requirement/offer values (≈ F7)** — legally startable now (dependency: F1/F2 only), but explicitly named a "safe **parallel**" track in the Gate-1 plan (§14.2), not the primary critical-path item. Selecting it instead of F4 would leave the Application owner's configuration work (F2) permanently unfinished — pure capture/composition with no way to ever durably publish a revision — while starting an unrelated inert-declaration owner. F4 continues work already in progress; F7 starts new work. For a solo maintainer, finishing what F2 started is the more bounded, more clearly-scoped next step.
- **Execution identity/state values** — explicitly forbidden this early: "Do not create `execution`... until Gate-2 work" (Gate-1 plan §4.1). Any Execution-shaped value type would have no real consumer yet and would risk exactly the "partly populated `ExecutionContext`" anti-pattern the plan explicitly names and rejects (§5.3: "Do not publish a partly populated object called canonical `ExecutionContext`").
- **Minimal Application declaration** — this already exists (`application.values`'s `CapturedCandidate`/`ComposedConfiguration`/`EffectiveConfiguration` from F2); there is nothing left to add at the *declaration* level that isn't already F4's actual next step (durable publication of that declaration).
- **Port contract foundations (generic)** — rejected as a *generic* framing; the Gate-1 plan is explicit that Ports must be owner-specific, modeling actual operations, never a generic reusable Port abstraction built "just because." F4's `application.ports` Protocol *is* the concrete, justified Port-contract-foundation work — framed narrowly around one real owner, not abstracted prematurely.

**F4 is therefore the batch actually justified by repository evidence, not a default assumption from the candidate list.**

---

## 6. Proposed source layout

No production code is written by this task (§20 hard stop) — this is the *specification* for a subsequent, separately-authorized coding task, exactly matching how this document's own parent (`GATE-1-FOUNDATION-IMPLEMENTATION.md` §21-23) specified F0-F2 without implementing them.

```text
src/legoai/
  kernel/
    provenance.py                      NEW — shared owner-neutral provenance anchor(s)
  application/
    values.py                          EXTEND — operation descriptor, retained result,
                                         pending source-submission duty value types
    ports.py                           NEW — owner-specific storage Protocol
  evidence/
    __init__.py                        NEW, inert
    values.py                          NEW — narrow source-fact/requirement/reference values
                                         consumed only by application's duty record
tests/
  support/
    __init__.py                        NEW, inert
    configuration_store.py             NEW — in-memory test fake implementing
                                         application.ports's Protocol (test-only, never
                                         shipped as a runtime fallback)
  unit/application/
    test_operation_result.py           NEW — operation/result/duty value tests
  unit/evidence/
    test_values.py                     NEW — Evidence value tests
  contract/
    test_configuration_store.py        NEW — Protocol conformance vectors run against
                                         the test fake (F6a will later run the same
                                         vectors against the real SQLite realization)
  architecture/
    test_import_boundaries.py          EXTEND — add `evidence` to the enforced
                                         allowlist/forbidden-import matrix (mirroring
                                         the existing `governance`-owner boundary tests)
```

No file outside this list is touched. `pyproject.toml`/`uv.lock` are not modified — F4 introduces no new dependency (§5.2).

---

## 7. Semantic invariants this batch must enforce

Directly from ADR-004 §7-10 ("Atomic mutation," "Revision, ordering and read semantics," "Acknowledgment and retained operation results," "Immutable history, current heads, disposition and obligations") and ADR-008 (operation identity/equivalence), as already synthesized by the Gate-1 plan's own §8.3/§9.1 tables — restated here as the exact invariants the new value types and Protocol must make representable (not yet enforceable with real durability, which is F6's job):

- An operation descriptor carries an **expected prior revision or an explicit expected-absence marker** — never an implicit "just write" mutation.
- A retained result distinguishes **committed stage** from **resulting revision** from **effects/errors** — these are separate fields, not conflated (mirrors `kernel.effects.EffectExtent` and `kernel.errors.ErrorDetail` already being separate from each other).
- **Operation equivalence** (ADR-008): the same logical operation, resubmitted, must be representable as retrieving its *original* retained result — never silently minting a second result or treating a resubmission as automatically stale merely because a head revision advanced.
- A pending duty is **not** a custody receipt and **not** proof anything was accepted by an Evidence owner — it is a description of outstanding obligation only (Gate-1 plan §9.1: "No custody receipt or successful end-to-end publication claim is fabricated").
- The storage Protocol's operations are **owner-specific and named** (publish-under-expected-revision, exact-revision read, retained-status lookup, bounded obligation listing) — never a generic `save`/`get`/`delete` CRUD surface.
- Tenant/owner scope is **explicit on every operation** — no implicit ambient tenant, matching the same discipline `kernel.context.TenantContext` and `governance.values.OperationContext` already enforce for F1.
- All new value types are **frozen, slotted dataclasses** with explicit `__post_init__` validation, matching every existing Kernel/Application/Governance value type — no exception to this pattern is introduced.

---

## 8. Test plan

Consistent with the Gate-1 plan's own test-family table (§12.1) and this task's explicit instruction (no external services):

- **Unit tests** (`tests/unit/application/test_operation_result.py`, `tests/unit/evidence/test_values.py`): construction, validation, immutability, and cross-type mismatch rejection for every new value type — mirroring the existing style in `tests/unit/kernel/test_identity.py`/`test_foundation.py` exactly (type checks, bound checks, frozen-instance mutation rejection).
- **Invariant tests**: expected-revision-vs-absence distinction is representable and cannot be conflated; a retained result's committed-stage/effects/errors fields are independently settable and independently checkable; a pending duty cannot be constructed in a way that implies custody acceptance.
- **Architecture/import tests** (`tests/architecture/test_import_boundaries.py`, extended): `evidence.values` may import Kernel only (matching the existing `governance`-owner pattern exactly — same forbidden-import shape, same "no reference/runtime/SDK import" rule); `application.ports` may import its own values, Kernel, and explicitly-permitted foreign leaf values only, never `reference` or `runtime` (per ADR-002 §9's dependency matrix, already enforced for `application.values`).
- **Negative tests**: an operation resubmitted with the same descriptor but a *different* expected revision is rejected as a conflict, not silently accepted; an obligation record with an inconsistent tenant/owner scope relative to its governing operation is rejected (mirrors `governance.values.OperationContext`'s existing tenant-mismatch test exactly).
- **Serialization/equality tests**: value-type equality follows the same "structural equality of immutable fields" rule already established for `EffectiveConfiguration`/`ComposedConfiguration` in F2 (equality excludes capture-time/object-identity concerns, per that module's own documented equality contract) — the same discipline applies to the new operation/result/duty types.
- **Contract tests** (`tests/contract/test_configuration_store.py`): the Protocol's behavioral vectors (publish-under-expected-revision succeeds/conflicts correctly; exact-revision read never returns "latest" by accident; duplicate-operation resubmission returns the original retained result; obligation listing is scoped and bounded) run against the in-memory test fake now — the **same vectors** are the ones F6a will later run against the real SQLite realization, proving the Protocol boundary is real (Gate-1 plan §9.1's own stated purpose for the test fake).
- **Property tests**: not justified for this batch — the Gate-1 plan's own guidance applies directly ("Use fixed contract vectors first... do not add [Hypothesis] to F0 for unused capability" §12.1); F4's value space is small and enumerable, with no serialization/permutation surface complex enough to warrant generated testing yet.

No live database, no network, no filesystem I/O (the test fake is purely in-memory), no external service of any kind.

---

## 9. Exit criteria

Tailored to F4's actual scope, following the same shape as the Gate-1 plan's own "Definition of done" pattern for F0-F2 (§21-23):

1. `kernel.provenance`, `application.ports`, `evidence.values` exist; `application.values` is extended with operation/result/duty types — all as frozen, slotted dataclasses with explicit validation.
2. Every canonical invariant in §7 is enforced by at least one positive and one negative test.
3. Invalid states are unrepresentable where practical (e.g., a retained result cannot be constructed with a "committed" stage and simultaneously a populated error detail claiming total failure — mirroring how `kernel.errors.ErrorDetail`/`kernel.effects.EffectExtent` already keep failure-category and effect-extent as independently-checked, non-contradictory axes).
4. `tests/architecture/test_import_boundaries.py` passes with `evidence` and `application.ports` added to the enforced matrix, including negative synthetic-graph cases for both new owners (mirroring the existing `test_governance_owner_boundary`/`test_kernel_cannot_import_governance` pattern exactly).
5. `mypy --strict` passes with zero new suppressions.
6. `ruff check` and `ruff format --check` pass with zero new suppressions.
7. `pytest` passes — all 150 existing tests remain green, plus all new F4 tests.
8. No new runtime dependency is added to `pyproject.toml`/`uv.lock`.
9. `tests/support/configuration_store.py` (the in-memory test fake) is confirmed to live only under `tests/`, never imported by any `src/legoai` module (a new architecture-test assertion, mirroring the existing "no production import from `tests`" rule already enforced for other test-support modules per Gate-1 plan §4.2).
10. The contract-test vectors in `tests/contract/test_configuration_store.py` are written to be reusable verbatim (same test functions, different fixture) once F6a introduces the real SQLite realization — confirmed by code review, not a new automated check.

---

## 10. Risks

| Risk | Mitigation |
|---|---|
| Scope creep into a full Evidence subsystem | §5.1 item 3 and §5.2 explicitly bound `evidence.values` to only the fields F4's own duty record needs; a full custody Port remains explicitly out of scope, matching Gate-1 plan §10.4 verbatim. |
| Accidentally designing a generic CRUD Port | §5.1 item 4 and §7 require named, owner-specific operations; a code-review checklist item (§9.10, informal) should explicitly reject any `save`/`get`/`delete`-shaped method name. |
| Test fake silently becoming a production fallback | §9.9's architecture-test addition makes this mechanically checkable, not merely a review convention. |
| Premature authority/Execution creep (e.g., adding a "who is allowed to publish" check) | Explicitly out of scope (§5.2) — F4 reuses F1's existing `Principal`/`TenantContext`/`OperationContext` for *representation* only; no new authorization decision logic is introduced, consistent with Gate-1 plan §10.1's "Before Gate 2, actual local trust establishment... must be implemented" still being unmet and not pretended otherwise. |
| Divergence from the eventual F6a SQLite realization's real constraints (e.g., the Protocol assumes something SQLite's transaction model can't cleanly provide) | Mitigated by ADR-004 §15's "Persistence capabilities and package boundary" table already being written *before* F4 (this batch consults it directly, §7), and by F5/F6a being explicitly required to reuse F4's same contract-test vectors (§8) rather than defining new ones — surfacing any mismatch early rather than after a divergent implementation exists. |

---

## 11. Rollback

F4 is purely additive: three new modules (`kernel.provenance`, `application.ports`, `evidence.values`), an extension to one existing module (`application.values`), and test-only additions. No existing F0-F2 file's behavior changes, no existing test is modified beyond the one named architecture-test extension (§6). Rollback is deleting the new files and reverting the one extended file and the one extended test file — no data migration, no schema, no persisted state exists to roll back, since F4 introduces no I/O.

---

## 12. Relationship to Embedding

**F4 does not implement anything Embedding-specific, and is not distorted to serve Embedding — it is a genuine, independently-justified Gate-1 prerequisite that Embedding also happens to eventually need, indirectly, several steps downstream.**

The exact remaining chain, none of it shortened or skipped by this batch:

```text
F4 (this batch) — owner operation/result/duty pattern proven once, for the
                   Application/configuration owner
        ↓
F5 — versioned codecs/migration mechanics (reusing F4's value shapes)
        ↓
F6a/F6b — real SQLite realization + failure/recovery qualification
        ↓
F9 — Gate-1 foundation exit
        ↓
[Gate 2, separately authorized] — ADR-015 supervision; ADR-005 real
        authorization enforcement; ADR-006 Plugin admission/Catalog;
        ADR-007 dispatch/resource-claim ordering
        ↓
legoai.capabilities — a REAL CapabilityResolver (not F7's inert
        declarations), now with somewhere governed to run and something
        governed to check against
        ↓
legoai.execution — governed Execution/ExecutionContext, Direct-invocation
        driver (proven sufficient for Answering-shaped capabilities per
        the DocuMind evidence, independent of any Agent driver)
        ↓
legoai.intelligence.model — ModelPort/values (ADR-002 §7.3/§15's reserved
        location; ***THIS*** is Embedding's actual, direct prerequisite,
        not F4)
        ↓
Ollama Adapter (implementation-batch decision, per
        EMBEDDING-CAPABILITY-DESIGN.md §12/§17 — not selected here either)
        ↓
EmbeddingCapability (`model.embedding`) — fully designed and
        live-characterized already (EMBEDDING-CAPABILITY-DESIGN.md);
        implementation resumes once the above chain reaches
        legoai.intelligence.model
```

F4's actual contribution to this chain is proving the **owner-local state + operation identity + evidence-obligation pattern** once, cheaply and deterministically, against the simplest possible real owner (Application configuration) — the same pattern a future `legoai.reference.execution` (governing Execution attempts) and a future `legoai.reference.resolution`/Catalog (governing Capability offers) will need to replicate for their own state. Skipping F4 and attempting to build Execution or Capability Resolution directly would mean inventing this pattern for the first time under the added complexity of authorization and dispatch simultaneously — exactly the kind of "framework creep" and premature-runtime risk this task's own §6/§9 instructions warn against.

---

## 13. Relationship to DocuMind extraction

**DocuMind extraction remains PAUSED**, per this task's own default recommendation, now confirmed rather than merely accepted by default:

- `document.chunking` (Batch 1) and `document.parsing` (Batch 2) are complete, implemented, tested, and require nothing further from Core — they remain valid, standalone, already-shipped work in `packages/legoai-document/`, untouched by this batch.
- `model.embedding` is fully designed and live-characterized (`EMBEDDING-CAPABILITY-DESIGN.md`) but cannot legally proceed to implementation until `legoai.intelligence.model` exists — which is several Gate-1-then-Gate-2 milestones away (§12's chain), not something F4 shortens.
- `RetrieverCapability`, `RerankCapability`, `IngestionWorkflow`, and `AnsweringCapability` (tracked in `DOCUMIND-EXTRACTION-ASSESSMENT.md`'s extraction sequence) all depend on `model.embedding` and/or a governed Execution substrate that does not exist yet. Designing any of them further now would produce documents with no nearer-term implementation path than Embedding already has, and would not change F4's own justification or scope. Per this task's explicit instruction, they are **not** designed "merely to stay busy."
- The correct next DocuMind-extraction action is: **wait** until Core's chain (§12) reaches `legoai.intelligence.model`, then resume Embedding's implementation directly from its already-complete design — no re-analysis needed at that point.

---

## 14. Architecture-freeze check — no new ADR required

**`NO NEW ADR`.**

Every decision F4 needs is already made by an Accepted ADR or the Accepted persistence realization record:

- **What state F4 manages and how it must be committed atomically**: ADR-004 (Accepted), §7-10, §15 — already extracted into exact obligations by the Gate-1 plan's own §8.3 table, consulted directly here (§7).
- **How operations are identified and treated as equivalent on resubmission**: ADR-008 (Accepted).
- **What "evidence obligation" narrowly means for this one case, without building custody**: ADR-009 (Accepted), applied exactly as narrowly as Gate-1 plan §10.4 already specifies.
- **Where these modules legally live in the package structure**: ADR-002 (Accepted) — `application.values`/`.ports` and `evidence.values` are both named in ADR-002's own initial 12-group package map; `kernel.provenance` is named in ADR-002's own proposed source tree (§8).
- **What the eventual real persistence realization will be**, so F4's Protocol doesn't contradict it later: the accepted `LOCAL-PERSISTENCE-REALIZATION.md` decision record (§1), consulted directly (§10 risk table).

The Gate-1 plan's own anti-overengineering review (§24) independently reaches the same conclusion for the *whole* remaining Gate-1 sequence, not just F4: *"New canonical decision? None identified. Persistence is implementation-local; supervision is already accepted; authoring awaits evidence."* This batch does not disturb that conclusion — nothing in F4's scope (§5.1/§5.2) touches a question any Accepted ADR left open.

**No genuine contradiction between DocuMind's Embedding evidence and accepted LegoAI architecture was found anywhere in this analysis** — the Embedding assessment's finding (Core placement, not Document Pack; `legoai.intelligence.model` doesn't exist yet) is a confirmation of ADR-002's existing design, not a conflict with it (see `EMBEDDING-CAPABILITY-DESIGN.md` §22 and this document's §4/§12).

---

## 15. Implementation readiness verdict

```text
READY_TO_IMPLEMENT_NEXT_CORE_BATCH = YES
```

- Scope is bounded (§5, three new modules, one extension, test-only additions).
- Accepted architecture (ADR-002/004/008/009) fully determines the required semantics (§7, §14) — no open design question remains.
- Package locations are authorized by ADR-002's own package map (§4, §14) — no illegal placement.
- Dependencies are available: F0-F2 are implemented and verified; F3 is Accepted (§1). Nothing F4 needs is missing.
- No missing ADR blocks it (§14).
- A concrete test strategy exists, requiring no external service (§8).
- No AI, Model, Embedding, Ollama, or any external provider is required (§5.2) — fully deterministic.

---

## 16. Implementation status

```text
F4_IMPLEMENTATION = COMPLETE
```

Implemented as scoped in §5.1/§5.2, nothing beyond:

- `kernel/provenance.py` — `DutyId`, `DutyKind` (owner-neutral duty anchors; `EvidenceId` deliberately omitted — no F4 consumer needs it yet).
- `evidence/values.py` (new `evidence` package) — `EvidenceRequirement`, the one narrow evidence-owned value F4's duty shape needs.
- `application/values.py` extended with `OperationStage`, `ConfigurationPublicationOperation`, `ConfigurationPublicationResult`, `ConfigurationSourceSubmissionDuty` — H (`OwnerRevision`) and R (`ConfigurationRevisionRef`) kept distinct throughout, per §7's own model.
- `application/ports.py` (new) — `ConfigurationStorePort` (`Protocol`, `@runtime_checkable`) with `current_head`/`current_published`/`read_revision`/`publish`/`operation_result`/`outstanding_duties`; `UnknownRevisionError` for exact-historical-read misses (no fallback to current).
- `tests/support/configuration_store.py` — `InMemoryConfigurationStore`, the only Port realization this batch ships; explicitly test infrastructure, never a runtime fallback.
- `tests/contract/test_configuration_store.py` — `STORE_FACTORIES`-parametrized Protocol conformance suite (currently one factory), written so F6a adds a second factory and reuses every test unchanged.
- Unit tests for the new provenance/evidence/application values; architecture tests extended to allow the ADR-002 §9.2 `application → governance, evidence` dependency, add an `evidence`-owner boundary (Kernel-only, stricter than application's), and assert no SQLite/database driver, no AI/agent-framework import, and no DocuMind/Document-Pack import anywhere in Core.

Verified before closing this batch: `pytest` 228 passed; `mypy src tests` — no issues in 32 source files; `ruff check`/`ruff format --check` — clean; zero new runtime dependencies (`pyproject.toml`/`uv.lock` untouched); no canonical document changed; no DocuMind file touched; no Gate-2, SQLite, or AI/Model code introduced anywhere in the diff.

Deviations from this document's original plan: none of substance. The Port was designed here with `current_revision()` collapsing H and R into one method; that was caught and split into `current_head()`/`current_published()` before the fake or contract tests were written, matching §7's own H/R distinction — not a scope change, a correction during implementation.

**F5 has not been started.** This document's own sequencing (§3) still names F5 (versioned codecs/migration) as the next candidate; nothing in this batch's diff touches serialization, migration, SQLite, or any Gate-2 package.

---

## 17. F5 — persistence representation, codecs, and migration semantics

```text
F5_IMPLEMENTATION = COMPLETE
```

F5 prepares F6a's SQLite realization without implementing SQLite. It adds exactly one new production module, `src/legoai/reference/application/codec.py`, at the location ADR-002 §7.2 already names for the Application Composition owner's realization — no new package group, no new canonical value.

**Representation format.** `LOCAL-PERSISTENCE-REALIZATION.md` §10 already selects stdlib JSON as UTF-8 TEXT record envelopes with an explicit closed field set; F5 implements exactly that, not pickle/marshal/Python-object serialization. `codec.dumps`/`codec.loads` provide the strict text layer (sorted-key canonical rendering; duplicate-object-key rejection at every nesting level; non-finite-number rejection; bounded byte-size and nesting-depth preflight) required by that same section.

**Representation version model.** A new `RecordSchemaVersion` type (private to this module's concern, not exported to Kernel) tracks only the durable JSON envelope shape per record kind — kept fully distinct from `Version` (domain contract/interpretation), `OwnerRevision` (H), and `ConfigurationRevisionRef` (R). H and R are never serialized under one ambiguous `revision` field: the codec uses `head_revision` and `configuration_revision_id` respectively. Every record kind starts at schema version 1 today; no synthetic prior version was fabricated to exercise migration machinery that has no real predecessor yet (Gate-1's own anti-overengineering stance, and this batch's own §17 instruction). Each `decode_*` function is the seam a real future transition extends — it currently accepts only version 1 and fails closed (`UnsupportedRepresentationVersionError`) on anything else, including a *future* unsupported version, never reinterpreting it as current.

**Records supported** (naming LOCAL-PERSISTENCE-REALIZATION.md §7.2's table rows): owner head (H), published revision pointer (R), historical revision content (`ComposedConfiguration`), the retained publication descriptor (`ConfigurationPublicationOperation`), the publication result (`ConfigurationPublicationResult`), and the outstanding source-submission duty (`ConfigurationSourceSubmissionDuty`, with its nested `EvidenceRequirement`). No generic universal record envelope and no per-value `to_dict`/`to_json` methods were added to canonical values — all encode/decode logic lives in this one reference-boundary module.

**Failure model.** A small three-class exception surface (`MalformedRepresentationError`, `UnsupportedRepresentationVersionError`, `InvalidRepresentationError`, all under one `RepresentationError` base) replaces raw `json`/parser exceptions at the durable-storage contract. Missing/unknown/wrong-typed fields, unknown enum values, and semantically-invalid decoded values (re-raised from the domain constructors' own `__post_init__` guards) all fail closed — never defaulted, never reinterpreted as current/latest.

**F6a handoff.** A future SQLite Adapter calls `encode_*`/`decode_*` (structured dict) or `dumps`/`loads` (JSON text) directly against the `record_json`/`descriptor_json`/`result_json`/`duty_json` TEXT columns LOCAL-PERSISTENCE-REALIZATION.md §7.2 names; F5 opens no connection, executes no SQL, and orchestrates no recovery. Round-trip and corruption/version-failure tests in `tests/unit/application/test_codec.py` are the exact contract F6a's own storage tests must not weaken.

Verified before closing this batch: `pytest` 290 passed; `mypy src tests` — no issues in 34 source files; `ruff check`/`ruff format --check` — clean; zero new runtime dependencies (`pyproject.toml`/`uv.lock` untouched); no canonical document changed; no DocuMind file touched; no F4 semantic file (`application/values.py`, `application/ports.py`, `kernel/provenance.py`, `evidence/values.py`, `tests/support/configuration_store.py`) touched; no SQLite, Gate-2, or AI/Model code introduced anywhere in the diff.

Deviations from the F5 task's plan: none of substance. One real decode bug was caught and fixed during implementation (not a scope change): `decode_owner_head`/`decode_published_revision` initially forwarded the full envelope dict — including `record_kind`/`record_schema_version` — into the narrower nested `_decode_owner_revision`/`_decode_configuration_revision_ref` helpers, which then rejected those two keys as "unknown fields" under their own closed-field check; fixed by passing a trimmed inner dict.

**F6a has not been started.** No SQLite connection, SQL, DDL, transaction, or migration-runner code exists anywhere in this diff.

---

## 18. F6a — SQLite realization of ConfigurationStorePort

```text
F6a_IMPLEMENTATION = COMPLETE
```

One new production module, `src/legoai/reference/application/sqlite_store.py` (`SQLiteConfigurationStore`), implements the existing F4 `ConfigurationStorePort` unchanged, using stdlib `sqlite3` only. Neither the Port (`application/ports.py`) nor the F5 codecs (`reference/application/codec.py`) were modified — both are byte-for-byte identical to the committed F5 state, confirmed via `git diff --stat HEAD`.

**Physical schema** (LOCAL-PERSISTENCE-REALIZATION.md §7.2, narrowed to what this Port actually needs): `store_metadata` (singleton physical schema-version marker), `config_revision` (immutable historical content, `record_json`), `config_head` (mutable H → R pointer, FK to `config_revision`), `config_result` (retained operation outcome, `descriptor_json`/`result_json`), `config_duty` (outstanding duties, `duty_json`). All STRICT tables with explicit `NOT NULL`/`PRIMARY KEY`/`UNIQUE`/`CHECK`/`FOREIGN KEY` constraints. H and R are never the same column: `head_revision` vs. `revision_id`/`published_head_revision`, matching F5's own field-naming discipline.

**Four distinct version concepts kept apart** (this batch's own §9): the SQL `store_metadata.schema_version` (physical table shape, currently 1, checked at every open — `UnsupportedPhysicalSchemaVersionError` fails closed on mismatch, no migration attempted since only one physical version exists); F5's `RecordSchemaVersion` (unchanged, inside each JSON payload); `OwnerRevision` H; `ConfigurationRevisionRef` R.

**PRAGMAs applied** on every connection, exactly as LOCAL-PERSISTENCE-REALIZATION.md §4.1 selects: `foreign_keys=ON`, `journal_mode=DELETE`, `synchronous=EXTRA`, `busy_timeout=0` (fail-fast, no hidden retry). `autocommit=True` with explicit `BEGIN IMMEDIATE`/`COMMIT`/`ROLLBACK` per §4.1's own transaction-control note.

**Connection ownership**: one fresh connection per Port method call (§5's selected model), opened/configured/closed every time — no ambient/global connection held by the store instance.

**Transactionality**: `publish()` is the only mutation; it opens one `BEGIN IMMEDIATE` transaction, does the idempotent-replay lookup and the expected-revision comparison inside that same transaction (no read-then-later-write TOCTOU window), and inserts the new revision/head/result/duty rows before one `COMMIT`. A real injected mid-transaction failure test (`test_failure_during_commit_leaves_no_partial_mutation`) proves no partial owner-local state becomes visible.

**Reused, not duplicated**: the existing `tests/contract/test_configuration_store.py` `STORE_FACTORIES` list gained one factory (`_sqlite_factory`, real file-backed temp databases, never `:memory:`); all 17 existing contract tests now run parametrized against both the in-memory fake and `SQLiteConfigurationStore` **unchanged** — same assertions, same fixtures, no SQLite-specific rewriting of contract expectations.

**F6a-specific tests** (`tests/unit/application/test_sqlite_store.py`, 18 tests): schema initialization (fresh + idempotent reopen), unsupported physical schema version, restart/file-reopen durability, historical-revision immutability across a later publish, transaction rollback under injected failure, foreign-key and uniqueness constraint enforcement, corrupt-payload handling (revision and result rows) surfacing `codec.RepresentationError` unchanged, missing-historical-revision `UnknownRevisionError` (reused, not redefined), real two-connection concurrent-writer contention (fail-fast `StorageUnavailableError`, no retry engine), two writers expecting the same head (exactly one commits), no-fallback-to-the-fake proof, connect-failure translation, and wrong-subject-type rejection.

**Architecture boundaries extended**, not loosened generally: the `reference-owner` rule now allows importing `legoai.application.ports` *only* for modules named with the `_store` suffix (the actual Port-realization convention) — F5's codec remains unable to import it, proven by the pre-existing `test_f5_reference_codec_cannot_import_ports_or_other_reference_owners`. The database-driver ban (`test_no_database_driver_imported_by_production_source`) now names exactly one authorized exception path (`reference/application/sqlite_store.py`) for stdlib `sqlite3`; every other production module, and every non-stdlib driver/ORM everywhere, remains forbidden.

Verified before closing this batch: `pytest` 325 passed; `mypy src tests` — no issues in 36 source files; `ruff check`/`ruff format --check` — clean; coverage 92% overall (`sqlite_store.py` 88% — remaining gaps are repetitive `except sqlite3.Error` defensive-translation branches structurally identical to the one already proven via failure injection, plus one "impossible under BEGIN IMMEDIATE" defensive guard); zero new runtime dependencies (`pyproject.toml`/`uv.lock` untouched); no canonical document changed; no DocuMind file touched; F4 Port/values and F5 codec confirmed byte-for-byte unchanged.

Deviations from the F6a task's plan: none of substance. One documented scope decision, consistent with (not a departure from) the reused F4 contract suite's own behavior: `publish()` recognizes a resubmitted operation by operation-identity lookup alone (matching `InMemoryConfigurationStore` exactly), not by decoding and comparing the full semantic descriptor for equivalence — the accepted contract-test suite does not exercise the differing-descriptor-under-same-operation-id case, so this SQLite realization intentionally mirrors the fake's existing, already-accepted behavior rather than inventing stricter semantics unilaterally.

**Residual risks**: full ADR-004 §17 qualification layers (real disk/VFS/flush guarantees, abrupt-process-kill barriers, `PRAGMA integrity_check`/`foreign_key_check` startup verification) remain unexercised — this batch proves owner-local transactional atomicity and durability-across-reopen on the current host/filesystem, not a qualified machine-durability guarantee. That gap is explicitly out of F6a's scope per the task's own §46 and belongs to later qualification work, not F6b.

**F6b has not been started.** No recovery orchestration, restart supervisor, `PRAGMA integrity_check`/`foreign_key_check` startup scan, or reconciliation workflow exists anywhere in this diff — this batch's restart test only proves records survive reopening a file, exactly the bounded durability smoke test the task's own §31 authorizes, not recovery.

---

## 19. F6b — restart qualification, integrity verification, recovery inspection, duty discovery

```text
F6b_IMPLEMENTATION = COMPLETE
```

One new production module, `src/legoai/reference/application/recovery.py` (`qualify_store`, `RecoveryReport`, `ScopeQualification`, `RecoveryStatus`), qualifies the already-implemented F6a SQLite realization against ADR-004 §13's restart/recovery order. It is inspection only, never Execution, never retry/compensation, and never authorization (ADR-004 §13 item 7: *"this ADR does not authorize a store or Plugin to admit itself"*) — `qualify_store` never calls `publish`, never resolves a duty, and never recomputes a result; it only decodes and reports what is already durably recorded.

**What recovery now proves**: a physical SQLite file can be opened read-only and inspected without ever creating it; `PRAGMA integrity_check` and `PRAGMA foreign_key_check` are run and their exact output interpreted (`"ok"`/no violations vs. anything else); the physical `store_metadata.schema_version` marker is checked before any per-scope interpretation is attempted; owner scopes present in the file are discovered via a narrow UNION query over this owner's own four tables (no generic database-browsing API, no cross-tenant wildcard); every historical revision and every retained operation result for each discovered scope is individually decoded through the *unchanged* F5 codec (not just the current one), so representation corruption anywhere in history is caught, not only in the current row; outstanding duties are discovered via the *unchanged* F6a Port method (`outstanding_duties`) and reported, never auto-resolved; a lost-acknowledgement scenario (publish, discard the store handle, "restart," recover) proves `operation_result` returns the exact original result with no second commit; `EffectExtent.UNKNOWN` survives recovery unchanged (never downgraded to `NONE`); two real subprocess tests prove committed state survives an actual OS process boundary, and an abrupt `process.kill()` mid-transaction (before `COMMIT`) leaves zero partial state visible after reopening — the strongest durability evidence in this batch, going beyond F6a's own same-process rollback test.

**Failure model qualification** (exactly as scoped, not more): qualifies restart after process/runtime restart or real process termination over otherwise-intact storage, including a lost caller acknowledgement. Does **not** qualify disk destruction, filesystem corruption beyond what `integrity_check`/`foreign_key_check` can detect, backup/restore, or multi-machine failure — `synchronous=EXTRA` is not claimed as a universal hardware-failure guarantee, only what these tests actually exercised on the current host/filesystem.

**Admission semantics**: `RecoveryStatus.QUALIFIED` / `RecoveryStatus.BLOCKED`, exactly the vocabulary this task's own §19 offered. Unrecognized/mismatched physical schema version, failed `integrity_check`, or any `foreign_key_check` violation blocks the *entire* store (physical corruption can affect every owner in a shared file — LOCAL-PERSISTENCE-REALIZATION.md §16 — so no per-scope interpretation is attempted once any of these fail); a representation failure isolated to one scope's payload blocks only that scope's `ScopeQualification.qualified`, but still flips the store-wide `RecoveryReport.status` to `BLOCKED` (the conservative reading consistent with the same "no claim of unaffected scopes without evidence" stance), while still reporting every other scope's own findings rather than hiding them.

**Projections**: not applicable. `config_head`/`config_revision`/`config_result`/`config_duty` are this owner's own authoritative records (ADR-004 §14 reserves "projection" for genuinely derived, non-authoritative views like Catalog's Plugin-eligibility observations) — there is nothing to rebuild, and the module docstring says so explicitly rather than fabricating one for ceremonial completeness.

**Owner enumeration**: implemented at the narrowest scope the task's own §17 asks for — a single `UNION`/`DISTINCT` query over this owner's four physical tables, reconstructing `ConfigurationRef` values already known to this schema. No generic table-browsing surface, no cross-owner or cross-tenant wildcard.

**Reuse, not redesign**: `ConfigurationStorePort`, F4's semantic values, F5's codecs, and `SQLiteConfigurationStore`'s public methods are all byte-for-byte unchanged (confirmed via `git diff --stat HEAD`). Recovery imports two private helpers from `sqlite_store` (`_physical_schema_version`, `_scope_columns`) as sibling reference-realization modules, and otherwise only calls the Port's own public methods (`current_head`, `current_published`, `outstanding_duties`) for the checks the Port already expresses, falling back to direct-but-scoped SQL only for what the Port cannot express (bulk historical decode, scope enumeration, physical PRAGMAs).

**Architecture boundaries extended**, mirroring F5's own precedent exactly: semantic value packages (application/evidence/governance/kernel) cannot import `recovery`; `recovery` may depend inward on `sqlite_store`, `codec`, and the same allowed peer values application already has; `recovery` cannot import `application.ports` directly (the `_store`-suffix exception does not apply to it — it inspects through the concrete store's own methods, never the abstract Port) and cannot import other reference-owner realizations or leak the test fake. The stdlib-`sqlite3` exception list now names exactly two authorized paths (`sqlite_store.py`, `recovery.py`); every other production module, and every non-stdlib driver/ORM anywhere, remains forbidden.

Verified before closing this batch: `pytest` 356 passed; `mypy src tests` — no issues in 38 source files; `ruff check`/`ruff format --check` — clean; coverage 91% overall (`recovery.py` 89% — remaining gaps are the same repetitive `except sqlite3.Error` defensive-translation branches already proven once via failure injection elsewhere in this codebase); zero new runtime dependencies; no canonical document changed; no DocuMind file touched; F4 Port/values, F5 codec, and F6a store all confirmed byte-for-byte unchanged.

Deviations from the F6b task's plan: none of substance.

**What remains explicitly unproven** (residual risk, not a defect): full ADR-004 §17 host/VFS qualification (actual device/controller flush guarantees under power loss, as opposed to process-level termination); recovery's own behavior under a genuinely corrupted/truncated database file byte stream (only structural PRAGMA-detectable and F5-representation-detectable corruption was exercised, per the task's own §22 guidance against nondeterministic byte-level corruption); multi-process concurrent recovery (only sequential recovery-after-restart was tested, matching F6a's own single-writer model). None of these gaps block F6b's own stated goal; they are qualification-layer work the accepted plan places beyond this batch.

**What remains for F9/Gate-1 exit**: F7 (inert Plugin/Capability declarations) and F8a/F8b (observability + deterministic composition) are still unimplemented per this document's own §3 sequencing — F6b does not touch either. **Gate 1 is NOT complete**: F9's own exit criteria (not evaluated by this batch) govern that determination, and this batch does not claim it.

**Gate 2 has not been started.** No Execution, ExecutionContext, CapabilityResolver, Plugin admission, authorization enforcement, resource accounting, or any runtime engine exists anywhere in this diff.

---

## 20. Remaining Gate-1 critical path and next-batch selection (readiness analysis only)

**Planning-only task; no production code was written to produce this section.** Verified directly against `planning/GATE-1-FOUNDATION-IMPLEMENTATION.md` §14/§14.1/§18, current `src/legoai`/`tests` tree contents, and a full green `pytest` run — not against prior completion-report summaries alone.

### 20.1 Verified current state

`src/legoai` contains exactly: `kernel/{identity,references,versions,context,errors,effects,provenance}.py`, `governance/values.py`, `application/{values,ports}.py`, `evidence/values.py`, `reference/application/{configuration,codec,sqlite_store,recovery}.py`. No `plugins/`, `capabilities/`, `observability/`, or `runtime/` package exists anywhere — confirming F7/F8a/F8b are genuinely unstarted, not merely unlabeled. `pytest` reports 356 passed (no failures, no skips) across `tests/{unit,contract,architecture}`; `mypy`/`ruff` were last confirmed clean in the F6b batch. No exit criterion for F0-F6b was found unmet: F4's contract suite, F5's codec round-trip/corruption suite, F6a's real-SQLite contract-suite reuse, and F6b's restart/integrity/subprocess-durability suite are all present and passing, matching Gate-1 plan §12.1's required test families for those increments (`tests/contract`, `tests/unit/application/test_{codec,sqlite_store,recovery}.py`). One accepted, previously-reported deviation stands: F5 was implemented as a single `reference/application/codec.py` rather than the plan's original `records.py`/`migrations.py` split (no real migration case existed to split out — consistent with the plan's own anti-overengineering stance in §24).

### 20.2 F7, F8a, F8b, F9 — authoritative definitions (Gate-1 plan §14 table; not inferred from numbering)

**F7 — Inert Plugin/Capability declarations and analysis.**
Authority: ADR-002, ADR-006 (Accepted), Plugin contracts (CONTRACTS §26); owners X (Plugins) and C (Capabilities).
Files: `plugins/values.py`, `capabilities/values.py`, `reference/declarations.py`, `reference/resolution.py`, plus unit/architecture tests.
Prerequisites: F1/F2 (both done); F4 references only if a test actually uses them.
Required behavior: exact Plugin identity/release/contribution/dependency/trust declarations as **inert data only** — no executable import, no candidate-module loading, no SPI callback invocation; pure lifecycle transition-table validation (`discovered → validated → initialized → active → degraded → stopping → stopped → failed → retired`, no `configured`/`admitted`/`bootstrapping`/`quarantined` state); Capability requirement/version-constraint/offer compatibility as **pure analysis** reporting invalid/unsatisfied/conflicting/ambiguous/uniquely-compatible findings — never an executable `CapabilityResolution` binding.
Explicit exclusions: Catalog, admission, init/activation, publication, SPI execution, live eligibility.
Exit criteria (Gate-1 plan §18.1 item 9): "Inert Plugin/Capability declarations, no executable inactive binding."

**F8a — Safe local observation.**
Authority: CONTRACTS §25 (`record_trace_activity`/`record_telemetry`, CTR-050), ADR-009 baseline (Accepted); owner O (Observation).
Files: `observability/values.py`, `observability/ports.py`, `reference/observation.py`, plus observation/security tests.
Prerequisites: F1 only (done). Explicitly does **not** require ADR-013 (still Proposed, per `adrs/ADR-INDEX.md`) — Gate-1 plan §11 states ADR-013 "cannot defer the local safe diagnostic baseline," i.e. this bounded slice is justified directly by already-Accepted CONTRACTS/ADR-009, not gated on ADR-013's acceptance.
Required behavior: allowlisted bounded diagnostic record shape (schema version, safe event code, owner/module, trace/correlation/causation refs, safe tenant-safe identity token, revision refs, stage/error-category/safe-cause, bounded latency/size); an injected sink boundary with a capturing test sink and an explicitly failing sink; bounded truncation/gap indicator on overflow; no raw Secret/payload/repr leakage (canary tests required).
Explicit exclusions: exporters, sampling/retention policy, dashboards/alerting, any production observability backend, Evidence custody.
Exit criteria (§18.1 item 12): "Bounded safe local diagnostics with failure tests."

**F8b — Private deterministic composition.**
Authority: ADR-002 (private technical composition root); no new ADR.
Files: `reference/deterministic.py`, `runtime/_composition/direct.py`, needed inert parent `__init__.py`s, composition tests, developer-evidence notes for the future ForgeAI brief (§19).
Prerequisites: F2 (done) + **F7 and F8a both** (neither done yet) + F6 only for the storage-backed fixture variant (F6a/F6b done).
Required behavior: the Gate-1 plan §13 "internal walking skeleton" — a synthetic Application declaration → Principal/Tenant values → captured immutable configuration → Capability requirement/inert Plugin metadata → non-executable compatibility findings → one explicitly injected pure trusted normalization function → typed result → one safe local diagnostic record; a test-local substitute function proves substitutability. Ordinary synchronous calls only.
Explicit exclusions: canonical Execution, live Tool/effect dispatch, asyncio, scheduler, any public authoring API.
Exit criteria (§18.1 item 13): "Deterministic internal non-effectful composition and substitution test."

**F9 — Foundation exit review and handoff.**
Authority: ADR-011 evidence discipline; not a new feature — a **qualification/integration/readiness-verification** milestone over F0-F8, not implementation.
Files: relevant tests/docs only; source changes limited to bounded identified-defect fixes, not new capability.
Prerequisites: **F0-F8 complete** (F7, F8a, F8b included — none done yet).
Required output: the full §18.1 seventeen-item foundation-exit checklist evaluated against actual executed evidence (clean install/build, reproducible check loop, F0-F6b evidence already largely in hand, F7/F8a/F8b evidence still needed, named Gate-2 blockers per §18.2). F9 does **not** itself imply Gate-1 exit is achieved — it is the review that determines whether the checklist is actually met or reports the exact unmet criterion.

### 20.3 Remaining Gate-1 dependency graph (Gate-1 plan §14.1, unmodified)

```text
F6b ✓ (done)
   │
   ├── F7   (needs F1 ✓ / F2 ✓)                 READY_NOW, independent
   │
   └── F8a  (needs F1 ✓)                        READY_NOW, independent
          │
   F7 ────┴── F8b  (needs F2 ✓, F7, F8a)        BLOCKED until F7 AND F8a both done
                │
               F9   (needs F0-F8 complete)       BLOCKED until F8b done
                │
          Gate-1 exit review outcome (§18.1)
```

No prerequisite outside these four labels was found missing. F7 and F8b together are the only path introducing new owner packages before F9; F8a and F8b together are the only path touching diagnostics. Gate-2 work (Execution, CapabilityResolver, Plugin admission, authorization/resource enforcement, Model/Agent/Workflow/Retriever runtimes) is excluded from this graph entirely, per Gate-1 plan §2/§15.

### 20.4 Readiness matrix

| Item | Status | Basis |
| --- | --- | --- |
| F7 | **READY_NOW** | F1/F2 implemented and verified; ADR-002/006 Accepted; `plugins`/`capabilities`/`reference.declarations`/`reference.resolution` are all reserved-but-authorized in Gate-1 plan §20's tree; no unresolved canonical decision found; zero new external dependency needed (pure stdlib data/analysis). |
| F8a | **READY_NOW** | F1 implemented and verified; CONTRACTS §25 + ADR-009 Accepted and sufficient (ADR-013 explicitly not required for this bounded slice); `observability` package reserved-but-authorized; zero new dependency (stdlib `logging` + explicit JSON formatter per Gate-1 plan §3 tooling table). |
| F8b | **BLOCKED** | Needs F7 and F8a, neither implemented yet. Not selectable now regardless of its own readiness otherwise. |
| F9 | **BLOCKED** | Needs F0-F8 complete; F7/F8a/F8b outstanding. |

F7 and F8a may proceed in either order or in parallel per Gate-1 plan §14.2 ("F7 and F8a can run independently once the shared F1 types are stable"); for a solo maintainer/single-session implementer, §14.2 also prefers one shared-file implementer at a time, and since F8b needs both regardless of order, sequencing between them does not change total time-to-F9. The tie-break is bounded scope: F7 introduces **two** new owner packages (`plugins`, `capabilities`) plus **two** reference modules, including a Capability compatibility/ambiguity-matching algorithm with real design risk (deterministic ordering "must not arbitrarily break an ambiguity the contract requires the caller to resolve"); F8a introduces **one** new owner package (the standard `values.py`/`ports.py` two-file shape already used by every prior Gate-1 owner) plus **one** reference module, with a well-precedented bounded-record/sink/leakage-test shape this codebase has already exercised repeatedly (F4's `ErrorDetail`/`ErrorCause` safe-cause pattern, F5's closed-field JSON discipline). F8a is the smaller, lower-design-risk, equally-necessary unit.

### 20.5 Selected next batch: **F8a — Safe local observation**

Not selected merely because it is unblocked; selected because among the two equally-ready, equally-necessary candidates it is the smaller bounded unit with lower design risk, satisfying every §10 criterion (Gate-1 critical path; prerequisites complete; bounded; deterministic; locally testable — pure in-process capture/failing sinks, no real log destination; no external infrastructure; no Gate-2 leakage; concrete value toward F8b and F9).

#### WILL IMPLEMENT

- `observability/values.py`: an immutable, bounded, allowlisted diagnostic-record value (schema version; safe event code; owner/module identity; trace/correlation/causation references reusing existing Kernel identity types; a safe tenant-scoped identity token; relevant configuration-revision reference; stage/transition observation; canonical `ErrorCategory` + safe cause reference reusing F1's `ErrorDetail`/`ErrorCause`; bounded latency/size observation fields). Explicit validated construction; no raw payload/arbitrary-object field.
- `observability/ports.py`: one narrow `ObservationSinkPort` Protocol (`emit(record) -> None` or equivalent) — the boundary a capturing test sink and a deliberately-failing test sink both implement, proving substitution.
- `reference/observation.py`: one explicit local sink realization using stdlib `logging` plus a bounded JSON formatter/serializer reusing F5's closed-field JSON discipline (sorted keys, reject non-finite, bounded size/depth) — **not** the F5 module itself, a sibling narrow one for this owner. No handler configured at import; no root-logger mutation; injected explicitly by callers/tests only.
- Unit tests: `tests/unit/observability/test_values.py` (record construction/validation, allowlist enforcement), `tests/unit/observability/test_sink.py` or similar (capturing sink round-trip, failing sink does not raise past the caller in an uncontrolled way, bounded truncation indicator on oversize input).
- Security tests: canary raw-Secret/payload/repr values must never reach an emitted record, exercised across normal, oversize, and sink-failure paths.
- Architecture tests: extend `tests/architecture/test_import_boundaries.py` with an `observability`-owner boundary (Kernel + own values only, mirroring `evidence`'s existing narrow pattern), a `reference.observation` reference-owner boundary (Kernel + own values/ports + allowed peers, mirroring `reference.application.*`'s existing pattern), and the same no-test-fake-leak / no-forbidden-import checks already established for every prior owner.
- Package/install tests: extend `test_inert_import` and `test_build_and_fresh_wheel`'s expected file/module sets exactly as every prior batch has (F4 added `evidence`, F5/F6a/F6b added their reference modules).

#### WILL NOT IMPLEMENT

- No exporter, telemetry service, sampling/retention policy, dashboard, or alert routing (ADR-013 scope, Proposed, deferred).
- No Evidence custody, audit, or provenance operation (CONTRACTS §25's `record_audit_evidence`/`record_provenance` remain Evidence-owner Gate-2+ work; F8a is Observation Collection's bounded diagnostic slice only).
- No F8b composition harness, no F7 Plugin/Capability values, no Execution/ExecutionContext, no real Model/Agent/Workflow.
- No global root-logger configuration or ambient logging state; no background thread/queue/exporter.
- No canonical document or Accepted ADR change.

#### Invariants (mapped to authority)

- Bounded, allowlisted fields only; no arbitrary payload — CONTRACTS §25/CTR-050 ("no generic logging operation substitutes for required evidence"; sensitivity-aware).
- No raw Secret/credential/payload/traceback in any emitted record — Gate-1 plan §11, ADR-009 baseline, ADR-010 (Secrets remain out of scope entirely here).
- Sink failure is a diagnostic gap, never authoritative — Gate-1 plan §11: "cannot rewrite a committed owner result, close a mandatory obligation, or falsely establish recovery state."
- No global mutable logging state / no import-time side effect — ADR-002 §7 inert-parent discipline, already enforced by this repository's `test_no_ambient_context_or_module_state`.
- Closed/versioned record schema, reject unknown/malformed shape — same discipline as F5's codec (`RepresentationError`-style fail-closed, not literally reused since this is a different owner's record).
- Owner boundary: `observability` may depend only on Kernel and its own values (narrower than the ADR-002 §9.2 maximum), matching the already-established stricter pattern F4 chose for `evidence`.

#### Tests

Unit (record validation, allowlist, immutability), contract-style (capturing sink vs. failing sink both satisfy the same `ObservationSinkPort` — a small parametrized suite, not a full `STORE_FACTORIES`-style reusable contract since there is only one production sink realization), negative (unknown field, oversize/deep payload, non-finite numbers reusing F5's preflight pattern), security (canary-value leakage across normal/oversize/failure paths), architecture/import (owner and reference-owner boundaries, no test-fake leak, no forbidden import), package/install (inert import, wheel/sdist content). No restart/durability tests apply (no persistence in this batch). No new external service.

#### New dependencies

`new runtime dependencies: NO`. stdlib `logging` and `json` only, exactly as Gate-1 plan §3's tooling table already selects for "Local observation."

#### ADR requirement

`NEW ADR REQUIRED = NO`. CONTRACTS §25 and the Accepted ADR-009 baseline already settle what this bounded slice needs; ADR-013 governs only the later production-observability claims this batch explicitly excludes.

### 20.6 Path to F9

```text
F8a (selected)
  → F7 (independently ready, implement next in either order)
  → F8b (needs both F7 and F8a)
  → F9 (needs F0-F8 complete: evaluates the full §18.1 checklist)
  → Gate-1 exit determination (F9's own outcome, not assumed here)
```

After F8a, F7 remains the other independently-ready item before F8b can start; nothing about selecting F8a first changes that. F9 itself is not "the next feature" — it is Gate-1's own qualification review and must not be started until F7/F8a/F8b are all actually implemented and tested.

### 20.7 Relationship to Embedding (unchanged, not accelerated)

```text
Gate-1 exit (F9 outcome)
  → Gate-2 prerequisites (Execution/ExecutionContext, CapabilityResolver, Plugin admission, authorization/resource enforcement — none of which this batch touches)
  → Capability/Execution substrate
  → ModelPort
  → Ollama Adapter
  → legoai.intelligence.model / Embedding
```

F8a's diagnostic-record shape is generic infrastructure only; it does not model, accelerate, or presuppose any Embedding/Model/Ollama concept, consistent with the Embedding assessment's own conclusion (`EMBEDDING-CAPABILITY-DESIGN.md`) that `legoai.intelligence.model` does not exist yet and is not created by Gate-1 work.

### 20.8 DocuMind extraction status

```text
DOCUMIND_EXTRACTION = PAUSED
```

Confirmed unchanged. No Retriever/Reranker/Ingestion/Answering design occurs in this task; DocuMind-SK/DocuMind-AgentFramework were not read or touched.

### 20.9 Implementation readiness verdict

```text
READY_TO_IMPLEMENT_NEXT_GATE1_BATCH = YES
```

- Exact milestone scope (F8a) is found in the accepted Gate-1 plan (§6, §11, §14, §18.1, §20), not inferred.
- Prerequisites (F1) are implemented and verified.
- No unresolved ADR blocks it (ADR-009 Accepted and sufficient; ADR-013's Proposed status does not gate this bounded slice, per the plan's own §11 wording).
- Package placement (`observability/{values,ports}.py`, `reference/observation.py`) is exactly the Gate-1 plan's own §20 proposed tree location — no `legoai.observability` global framework, no generic logging vendor.
- Tests are defined (§20.5 above).
- No Gate-2 functionality is required or introduced.

---

## 21. F8a — Safe local observation (implementation status)

```text
F8a_IMPLEMENTATION = COMPLETE
```

Implemented exactly as scoped in §20.5, nothing beyond: `observability/{__init__,values,ports}.py` (new package) and `reference/observation.py` (new module, sibling to `reference/application/`, not nested under it — matching the Gate-1 plan's own §20 tree, which places `observation.py` directly under `reference/`).

**Safe bounded observation implemented.** `Observation` carries exactly the Gate-1 plan §11 allowlist subset available today: `schema_version` (fixed at 1), `event_code` (open `ObservationEventCode`, mirroring `DutyKind`'s already-established open-vocabulary rationale), `owner`, `correlation_id`/`trace_id`/`causation`/`operation` (reusing existing Kernel identity/reference types, never duplicated), `tenant_id`, `configuration_revision`, `error_category` (reusing Kernel's existing `ErrorCategory`), `safe_cause_reference` (bounded text, only meaningful paired with an `error_category`), `latency_ms`, `size_bytes`. No open attributes bag was added: the plan's own field list is closed and enumerated, not "attributes plus whatever," and no Plugin/Provider/Adapter/Execution/authorization field was invented since none of those types exist yet (F7/Gate-2). No semantic timestamp field exists in `Observation` itself — wall-clock acquisition belongs to the sink's own emission, not the semantic value, consistent with the existing repo-wide "no wall-clock in value constructors" discipline.

**Reference local sink implemented.** `LocalLoggingObservationSink` (`reference/observation.py`) uses stdlib `logging` + `json` only; explicit field-by-field projection (never `repr()`/`vars()`/`asdict()`); one structured JSON line per `Observation` via a named, non-root logger (`legoai.reference.observation` by default, injectable). Import has zero side effects — no `basicConfig()`, no handler attachment, no root-logger mutation — proven by a real subprocess inert-import test plus a module-reload test.

**Security/canary result: PASS.** `SUPER_SECRET_CANARY_VALUE`, `AUTHORIZATION_CANARY`, and `PRIVATE_PAYLOAD_CANARY` cannot reach any `Observation` field at all — the closed dataclass field set makes this a structural guarantee, not caller discipline: attempting `password=`/`prompt=`/`document_content=`/`api_key=`/`secret=`/`authorization_header=`/`private_payload=` on construction raises `TypeError` before any value exists to leak. Unknown-field, oversize (`>256` chars, reusing the existing `_validate` bound), non-finite numeric (`NaN`/`Infinity`/`-Infinity`), and no-nested-structure behavior are all explicitly tested and rejected.

**Failure containment demonstrated.** `FailingObservationSink` (test-only, `tests/support/observation.py`) raises on `emit()`; a dedicated test proves the `Observation` value itself is unaffected and that a different sink still works afterward. No best-effort/swallowing wrapper was introduced — the task's own instruction was not to add one unless the accepted plan calls for it, and it does not; `ObservationSinkPort.emit()` may simply raise, and no code anywhere in this batch or in F0-F6b catches that exception to decide semantic success.

**Architecture boundaries.** `observability.values`/`ports` may depend only on Kernel (narrower than ADR-002 §9.2's Governance-inclusive maximum for the O plane — no field in this batch actually needs Governance, mirroring `evidence`'s own precedent of choosing narrower-than-maximum when nothing yet requires the wider permission). `reference.observation` may depend only on Kernel plus its own `observability.values`/`.ports` — it cannot import `application.ports`, other reference-owner realizations, or leak the test fake. `kernel` cannot import `observability` (confirmed explicitly, mirroring the existing `evidence`/`governance` symmetry checks). No F0-F6b semantic package depends on `reference.observation`.

Verified before closing this batch: `pytest` 430 passed; `mypy src tests` — no issues in 45 source files; `ruff check`/`ruff format --check` — clean; coverage of the new modules is 100% (`observability/values.py`, `observability/ports.py`, `reference/observation.py`); zero new runtime dependencies; no canonical document changed; no DocuMind file touched; no F0-F6b file touched (confirmed via `git diff --stat HEAD` against every prior package).

Deviations from the F8a task's plan: none of substance.

**ADR-013 remains unresolved/Proposed** for production observability (exporters, sampling, retention, distributed trace propagation, metrics backend, central aggregation, operational alerting) — this batch settles none of that and does not attempt to.

**F7 is still outstanding.** No `plugins/`, `capabilities/`, `reference/declarations.py`, or `reference/resolution.py` exists anywhere in this diff.

**F8b remains blocked until F7 is complete** (it needs both F7 and F8a; only F8a is now done). No `reference/deterministic.py` or `runtime/_composition/direct.py` exists anywhere in this diff.

**Gate 1 is not complete.** F9's own exit checklist (§18.1) was not evaluated by this batch.

---

## 22. F7 — Inert Plugin/Capability declarations and analysis (implementation status)

```text
F7_IMPLEMENTATION = COMPLETE
```

Implemented exactly the Gate-1 plan §14 file list, nothing beyond: `plugins/{__init__,values}.py`, `capabilities/{__init__,values}.py` (new packages), `reference/declarations.py` and `reference/resolution.py` (new modules, siblings to `reference/observation.py` and `reference/application/*`).

**Plugin declarations implemented.** `PluginId` (namespace + local identity, PLG-006) and `PluginDeclaration` (identity, release `Version`, declared `CapabilityOffer`/`CapabilityRequirement` tuples, PLG-004/009/011/040). Deliberately **not** modeled: PLUGIN-SPEC's full PLG-063 manifest (owner/publisher, metadata, configuration contract, lifecycle contract, health, permissions/trust, tenant/isolation, extensions, resource/Secret requirements) — none has a real consumer in this batch, and none is needed to prove pure compatibility analysis or the "no executable inactive binding" exit criterion. Most deliberately absent: any implementation locator (module/class/entry-point/factory/command/URL/executable) — omitted outright rather than represented-but-unused, so there is no field a future implementer could be tempted to resolve "just this once."

**Capability declarations implemented.** `CapabilityId`, `CapabilityVersionRange` (explicit inclusive/exclusive minimum, optional unbounded-above maximum — PLG-008's "ranges with inclusive/exclusive bounds," never semver caret/tilde shorthand, never implicit 0.x compatibility), `CapabilityRequirement` (what a consumer needs), `CapabilityOffer` (what a Plugin release declares, attributed to its containing `PluginDeclaration` rather than duplicating Plugin identity on the offer itself — Provider identity, PLG-014, is not separately modeled since no real consumer needs Provider-vs-Plugin distinctness yet).

**Pure compatibility analysis implemented.** `reference/resolution.py`'s `analyze_compatibility`/`analyze_requirements` — deliberately not named `resolve` (PLUGIN-SPEC's own `Resolution` row is Gate-2's future `CapabilityResolver`). `CompatibilityStatus` is exactly `NO_MATCH`/`UNIQUE_MATCH`/`AMBIGUOUS` (a fourth "invalid declaration" status does not exist, since a structurally invalid `PluginDeclaration` cannot be constructed at all — validated at its own `__post_init__`). `reference/declarations.py` provides `normalize_declarations` (deterministic ordering with no preference meaning) and `find_duplicate_identities` (surfaces, never resolves, an identical-`(PluginId, release)` collision across independently supplied declarations — PLUGIN-SPEC's "Namespace impersonation" risk row).

**Ambiguity preserved.** Proven directly: two Plugins offering the same Capability at different versions returns both candidates as `AMBIGUOUS`, never the highest version, never the alphabetically-first namespace — no selection logic of any kind exists in this batch.

**No executable inactive binding: proven, not merely asserted.** Every value type's fields are closed (Python dataclass field sets, not an open dict); attempting to pass a callable through any unsupported keyword argument raises `TypeError` before construction completes, verified with an actual callable canary that never fires; a source-level AST scan of `reference/resolution.py` confirms no `eval`/`exec`/`compile`/`__import__`/dynamic-import call exists in the module. Hostile text (`"os.system(...)"`, `"import os; os.system('x')"`, `"../../etc"`) passed through `CapabilityId`/`PluginId` remains ordinary inert string data — never resolved, imported, or executed, since no code path in this batch ever does either.

**Architecture boundaries**, mirroring F8a's exact precedent: `capabilities.values` may depend only on Kernel (narrower than ADR-002 §9.2's G/R/O/X maximum for the C plane); `plugins.values` may depend on Kernel plus `capabilities.values` only (the one ADR-002-authorized X→C peer, narrower than the full C/G/R/Q/O/V maximum); `reference.declarations`/`reference.resolution` may depend on Kernel plus `plugins.values`/`capabilities.values` only — neither can import the abstract `application.ports`, any other reference-owner realization, or leak a test fake. No F0-F8a semantic package depends on either new reference module.

Verified before closing this batch: `pytest` 543 passed; `mypy src tests` — no issues in 55 source files; `ruff check`/`ruff format --check` — clean; coverage of every new F7 module is 100% (`plugins/values.py`, `capabilities/values.py`, `reference/declarations.py`, `reference/resolution.py`); zero new runtime dependencies; no canonical document changed; no DocuMind file touched; no F0-F8a file touched (confirmed via `git diff --stat HEAD` against every prior package, including `observability`/`reference/observation.py`).

Deviations from the F7 task's plan: none of substance.

**F8a is already complete** (unaffected by this batch — confirmed byte-for-byte unchanged).

**F8b is now unblocked**: both of its prerequisites (F7, F8a) are complete. F8b itself has not been started — no `reference/deterministic.py` or `runtime/_composition/direct.py` exists anywhere in this diff.

**Gate 1 is not complete.** F9's own exit checklist (§18.1) was not evaluated by this batch; F9 additionally requires F8b, which has not started.

**Gate 2 has not been started.** No Execution, ExecutionContext, CapabilityResolver runtime, Plugin admission/activation, authorization enforcement, or resource-claim code exists anywhere in this diff.

---

## 23. F8b — Private Deterministic Composition (implementation status)

```text
F8b_IMPLEMENTATION = COMPLETE
```

Implemented exactly the Gate-1 plan §14 file list, nothing beyond: `reference/deterministic.py` (new module, sibling to `reference/declarations.py`/`resolution.py`/`observation.py`) and `runtime/{__init__,_composition/__init__,_composition/direct}.py` (new private package, exactly as the plan's §20 tree names it — nothing exported from `legoai.runtime.__init__` or `legoai.__init__`).

**Private deterministic composition implemented.** `compose_direct` (`runtime/_composition/direct.py`) proves, by ordinary explicit Python construction, that F2 configuration capture (`compose_configuration`), F7 inert declarations and pure compatibility analysis (`analyze_compatibility`), the one F8b deterministic reference function (`normalize_text`), and F8a's safe observation (`ObservationSinkPort`) compose into one coherent typed `CompositionResult` — exactly Gate-1 plan §13's "internal walking skeleton" composition-experiment half. No Execution, ExecutionContext, CapabilityResolver, Plugin admission/activation, authorization enforcement, resource claim, or async supervision was introduced; `compose_direct` is an ordinary synchronous function.

**Deterministic reference fixture.** Bounded ASCII whitespace normalization (`legoai.reference.deterministic.normalize_text`), exactly the fixture Gate-1 plan §13 names: `TRIM` removes only leading/trailing characters found in the caller's `allowed_whitespace`; `COLLAPSE` additionally collapses interior runs to one ASCII space; non-ASCII characters are never inspected or altered; an empty `allowed_whitespace` means pass-through; oversize input relative to `max_input_length` is rejected, never truncated. Pure: no I/O, randomness, wall clock, or mutable global state — proven by a 50-iteration repeatability test and explicit fixed-identity tests (`text_normalization_capability_id`/`_plugin_id`/`_release` never vary across calls, never randomly generated).

**F7 declarations remain exactly as inert as before.** `text_normalization_declaration()` constructs an ordinary `PluginDeclaration`/`CapabilityOffer` — no executable field, no `Binding` type, no callable attached anywhere. The static correspondence between the one known declaration and the one known implementation lives entirely in `compose_direct`'s own code (an equality check against `text_normalization_plugin_id()`/`_release()`), never inside `PluginDeclaration`/`CapabilityOffer` themselves — confirmed by regression tests asserting neither gains a `callable`/`implementation`/`factory` attribute after composition runs.

**Compatibility stays analytical, exactly as F7 established.** `UNIQUE_MATCH` against the known declaration → `COMPOSED`, deterministic function runs exactly once. `NO_MATCH` → `NO_COMPATIBLE_DECLARATION`, deterministic function never called (proven with a spy function asserting zero invocations). `AMBIGUOUS` → `AMBIGUOUS_DECLARATION`, deterministic function never called, and declaration order is proven not to affect the outcome (no first/latest/alphabetical selection exists anywhere in this batch). A `UNIQUE_MATCH` against a real but *unrelated* declaration this module has no implementation for → `FIXTURE_MISMATCH`, also never invoking the function — a case the F7 batch itself could not have needed, since only F8b introduces a real static-correspondence check.

**Observation sink failure contained exactly at the diagnostic boundary.** `_emit_best_effort` wraps only the single `sink.emit(...)` call in `try/except Exception` — nothing else in `compose_direct` is guarded this broadly. Proven directly: composing the identical inputs with `CapturingObservationSink` and with `FailingObservationSink` produces byte-for-byte equal `CompositionResult` values, and the failing-sink path never raises out of `compose_direct`. A private `_NoOpObservationSink` (module-internal, not a public `NullObject` abstraction) is used when no sink is supplied.

**Architecture boundaries**, extending F7/F8a's exact precedent: `reference.deterministic` may depend only on Kernel, `application.values`, `plugins.values`, `capabilities.values` — not on the composition root, SQLite store/recovery, or `reference.observation`. `runtime._composition.*` may depend on the "needed slice" ADR-002 §4.2 authorizes for private runtime composition (Kernel; `application.values`; `capabilities.values`/`plugins.values`; `observability.values`/`.ports`; `reference.declarations`/`resolution`/`deterministic`/`application.configuration`) — but never on `application.ports`, the concrete SQLite/recovery/observation-sink realizations, or any other reference-owner realization; callers inject whichever concrete `ObservationSinkPort` they choose. No F0-F8a/F7 semantic package depends on `runtime._composition`, and no reference module depends on it either (composition is top-level private wiring only, never a dependency target).

Verified before closing this batch: `pytest` 618 passed; `mypy src tests` — no issues in 62 source files; `ruff check`/`ruff format --check` — clean; coverage of every new F8b module is 100% (`reference/deterministic.py`, `runtime/_composition/direct.py`); zero new runtime dependencies; no canonical document changed; no DocuMind file touched; no F0-F8a/F7 file touched (confirmed via `git diff --stat HEAD` against every prior package).

Deviations from the F8b task's plan: none of substance.

**F9 is now unblocked**: F7 and F8b are both complete, and F8a was already complete. F9 itself has not been started — no foundation-exit review, no Gate-2 work, and no claim that Gate 1 is complete exists anywhere in this diff.

**Gate 2 has not been started.** No Execution, ExecutionContext, CapabilityResolver, Plugin admission/activation, authorization enforcement, resource-claim, or async-supervision code exists anywhere in this diff.

---

## 24. F9 — Foundation Exit Review and Handoff

```text
F9_REVIEW = COMPLETE
GATE_1_EXIT_VERDICT = NOT_READY
```

This is a qualification/review task only. No implementation was added or changed to make the gate pass, per this task's own hard rule; the one gap found below (G1-EXIT-08) is reported, not patched. The only repository change from this task is this section.

### 24.1 Authoritative checklist confirmed

`planning/GATE-1-FOUNDATION-IMPLEMENTATION.md` §18.1 is confirmed, by direct re-read of that section, to still be the accepted seventeen-item Gate-1 foundation-exit checklist, verbatim. No substitute checklist was used. Each item is assigned `G1-EXIT-01` through `G1-EXIT-17` below in the exact original order and wording.

### 24.2 Verification method

Re-run directly for this review (not taken from prior completion reports): `pytest` (full suite, both `legoai-reference` and the independent `packages/legoai-document` Document Pack), `mypy --strict`, `ruff check`, `ruff format --check`, `coverage run --branch` across every implemented package, a clean `uv build` with wheel-content inspection, and targeted `grep`/source reads for specific claims (durability-boundary disclaimers, `QUALIFIED` usage, pickle/marshal absence, migration code presence).

Results: `pytest` — **618 passed** (`legoai-reference`); **268 passed, 64 skipped** (Document Pack, skips are documented pre-existing invariant-coverage overlaps, not failures). `mypy src tests` — **no issues in 62 source files**. `ruff check`/`ruff format --check` — **clean**. Coverage — **94% overall** across `application`, `reference.application`, `observability`, `reference`, `capabilities`, `plugins`, `runtime` (every F7/F8a/F8b module at 100%; the 88-92% modules are F4-F6 files whose gaps are exclusively repetitive defensive `except sqlite3.Error` translation branches and secondary type-guard branches, already documented in their own batch reports). Wheel contents inspected directly: exactly `legoai.{kernel,application,governance,evidence,observability,capabilities,plugins,reference,runtime}` and their exact implemented submodules — no `legoai.execution`, no unimplemented package. Wheel `METADATA` carries no `Requires-Dist` line at all. `uv.lock` contains only build/test tooling and its own transitive dependencies (`hatchling`, `editables`, `pytest`, `mypy`, `ruff`, `coverage`, and their dependencies) — zero runtime packages.

### 24.3 Checklist evaluation

**G1-EXIT-01 — "Local installable distribution and clean wheel/sdist smoke test."**
`PASS`. `pyproject.toml` declares one distribution (`legoai-reference`) with `dependencies = []`. `tests/architecture/test_package_install.py::test_build_and_fresh_wheel` builds the real wheel+sdist via `uv build --no-build-isolation`, asserts exact file contents, installs into a fresh isolated venv, and imports/exercises the package from that installation — re-run directly for this review, passing, wheel contents independently re-verified above.

**G1-EXIT-02 — "Reproducible documented local test/type/lint/format/build loop."**
`PASS`. `docs/development.md` documents the exact command loop (`uv sync --locked ...`, `pytest`, `mypy`, `ruff check`, `ruff format --check`, `uv build`), matching Gate-1 plan §12.4 verbatim. All commands re-run directly in this review with the results in §24.2.

**G1-EXIT-03 — "Minimal nominal values and safe explicit contexts with negative tests."**
`PASS`. `kernel/identity.py` (`TenantId`, `PrincipalId`, `ApplicationId`, `OperationId`, `RequestId`, `CorrelationId`, `TraceId`), `governance/values.py` (`Principal`, `OperationContext` — explicit tenant/requester, no `trusted=True`/ambient authority field of any kind). Negative tests: `tests/unit/kernel/test_identity.py`, `tests/architecture/test_package_install.py::test_f1_static_misuse` (cross-kind ID substitution rejected by mypy, asserted directly), `tests/unit/governance/test_context.py` (wrong/missing scope rejected).

**G1-EXIT-04 — "Enforced import/dependency direction and inert package parents."**
`PASS`. `tests/architecture/test_import_boundaries.py` — 61 test functions (141 parametrized cases), covering every owner (`application`, `governance`, `evidence`, `observability`, `capabilities`, `plugins`, every `reference.*` module, `runtime._composition`) with both positive (`test_production_boundaries` scanning the real `src/legoai` tree) and negative (synthetic forbidden-graph) cases; all inert `__init__.py` files checked by the same `initializer` rule. Re-run directly: 141 passed.

**G1-EXIT-05 — "Immutable candidate composition and exact published revision behavior in isolated owner tests."**
`PASS`. `reference/application/configuration.py::compose_configuration` (F2, immutable `ComposedConfiguration`/`EffectiveConfiguration`) plus `application/ports.py::ConfigurationStorePort.publish` (F4) realized by both `tests/support/configuration_store.py::InMemoryConfigurationStore` and `reference/application/sqlite_store.py::SQLiteConfigurationStore` (F6a), proven identical via the shared parametrized suite `tests/contract/test_configuration_store.py` (`STORE_FACTORIES` = `[in-memory-fake, sqlite]`, 17 test methods × 2 backends). `test_exact_historical_revision_read`, `test_missing_historical_revision_does_not_fall_back`, `test_old_revision_remains_readable_after_a_new_publish` prove exact-revision behavior on both realizations.

**G1-EXIT-06 — "SQLite owner boundary selected/recorded, compound guards/results/duties implemented and tested; any unqualified durability environment explicitly blocks durable runtime use... never described as qualified."**
`PASS`, with the required disclaimer confirmed present at the source level, not only in planning prose. `planning/runtime/LOCAL-PERSISTENCE-REALIZATION.md` (Accepted) records the selection. `reference/application/sqlite_store.py` implements owner-local compound commit (`_insert_committed_result` writes revision/head/result/duty in one `BEGIN IMMEDIATE`/`COMMIT`); `tests/unit/application/test_sqlite_store.py::test_failure_during_commit_leaves_no_partial_mutation` proves no partial set survives an injected mid-transaction failure. The durability-boundary disclaimer is present verbatim in `reference/application/recovery.py`'s own module docstring ("Failure model scope... does NOT qualify disk destruction... `synchronous=EXTRA` is not claimed here as a universal durability guarantee") — confirmed by direct `grep` in this review, not merely asserted in a completion report.

**G1-EXIT-07 — "Safe versioned serialization and supported-reader rejection."**
`PASS`. `reference/application/codec.py` is the sole F5 codec authority (confirmed: no other module in `src/legoai` implements JSON encode/decode of these record kinds). `RecordSchemaVersion` distinct from `Version`/`OwnerRevision`/`ConfigurationRevisionRef` (module docstring states this explicitly; `tests/unit/application/test_codec.py::test_record_schema_version_type_is_distinct_from_domain_version`). Unsupported version rejection: `test_unsupported_record_schema_version_fails_closed`. No pickle/marshal anywhere in `src/legoai` — confirmed by direct source `grep` in this review (zero matches).

**G1-EXIT-08 — "Revision/conflict/duplicate/lost-ack/process-restart and migration-interruption evidence for the selected owner."**
`PARTIAL` — **this is the one real gap this review found.** Revision/conflict evidence: `TestConditionalMutation` (contract suite) + `test_two_writers_expecting_same_head_only_one_advances` (SQLite-specific, real second writer). Duplicate/lost-ack evidence: `test_lost_acknowledgment_does_not_create_second_commit` (contract suite) + `test_lost_ack_result_recoverable_after_logical_restart` (F6b, spans an actual store-object discard/reopen). Process-restart evidence: `tests/unit/application/test_recovery.py::TestSubprocessDurability` — two **real OS subprocess** tests, including one that kills a child process mid-transaction and proves zero partial state survives. All five of those sub-clauses are solidly evidenced. **Migration-interruption evidence does not exist anywhere in the repository**: `grep -rn migration src/legoai tests` finds only two files (`codec.py`, `sqlite_store.py`) and only as prose explaining that no migration mechanism is implemented ("no migration is attempted by F6a"). This is a genuine shortfall against the Gate-1 plan's own explicit instruction (§9.3): *"Use a clearly synthetic predecessor fixture to exercise interrupted migration before a real upgrade exists; do not invent a historical supported release."* F5/F6a/F6b's own completion reports characterized omitting this as consistent with the plan's anti-overengineering stance; on direct re-reading of §9.3 for this review, that characterization conflated "don't invent a false historical release narrative" (correctly avoided) with "don't build the interruption-test fixture at all" (not actually authorized — the plan asks for exactly this fixture). **Classification: incomplete test evidence, not a missing production capability** (the plan explicitly says no real migration *code* is warranted yet). **Owning milestone: F5/F6a** (record schema versioning + physical schema versioning are where the synthetic fixture and interruption test belong). Per this task's own hard rule, no fixture or test was added during this review to close the gap.

**G1-EXIT-09 — "Inert Plugin/Capability declarations, no executable inactive binding."**
`PASS`. `plugins/values.py::PluginDeclaration`/`PluginId` and `capabilities/values.py::CapabilityId`/`CapabilityOffer`/`CapabilityRequirement`/`CapabilityVersionRange` — every field is a closed dataclass field (Kernel identity/version types or bounded text), no callable/module/entry-point field exists at all. Proven, not merely asserted: `tests/unit/plugins/test_values.py::test_cannot_pass_callable_as_unsupported_field` and `tests/unit/capabilities/test_values.py::test_no_executable_field_exists` both use a real callable canary that never fires, asserted via `TypeError` before construction completes. `tests/integration/composition/test_direct.py::TestNoExecutableDeclarationBinding` and `TestNoGate2Symbols` (AST source scan for `eval`/`exec`/`compile`/`__import__`, and `dir()` scan for forbidden Gate-2 symbol names) prove the private F8b composition root never converts an inert declaration into an executable one either.

**G1-EXIT-10 — "Explicit Principal/Tenant inputs, no ambient or fake authority."**
`PASS`. `governance/values.py::Principal`/`OperationContext` require explicit `PrincipalRef`/`TenantContext` at construction; `OperationContext.__post_init__` rejects a self-causing operation and cross-tenant reference mismatches. No `trusted=True`, no thread-local/contextvar ambient state anywhere — `tests/architecture/test_import_boundaries.py::test_no_ambient_context_or_module_state` scans all of `src/legoai` for `contextvars`/`threading` imports and module-level mutable state; confirmed passing.

**G1-EXIT-11 — "Safe source/Evidence/provenance references; source duty not mistaken for custody."**
`PASS`. `evidence/values.py::EvidenceRequirement` is explicitly documented as "not custody: no store, no retention engine, no receipt/acknowledgment"; `kernel/provenance.py::DutyId`/`DutyKind` are "not a custody receipt and not proof any obligation was accepted or resolved." `application/values.py::ConfigurationSourceSubmissionDuty` docstring states resolving it "is explicitly deferred to later custody work."

**G1-EXIT-12 — "Bounded safe local diagnostics with failure tests."**
`PASS`. `observability/values.py::Observation` — closed, enumerated field set (no attributes bag), bounded text via the shared `_validate` (1-256 code points), non-finite numeric rejection. Security/canary tests: `tests/unit/observability/test_values.py::TestSensitiveDataCannotBeExpressed` (canary values for secret/authorization-header/private-payload all rejected via `TypeError` on unsupported fields). Failure test: `tests/unit/observability/test_sink.py::TestFailingSinkContainment`.

**G1-EXIT-13 — "Deterministic internal non-effectful composition and substitution test."**
`PASS`. `reference/deterministic.py::normalize_text` — pure, no I/O/randomness/wall-clock (module docstring and `tests/unit/reference/test_deterministic.py::TestDeterminism` including a 50-iteration no-drift check). Substitution: `runtime/_composition/direct.py::compose_direct`'s `normalization_function` parameter, proven by `tests/integration/composition/test_direct.py::TestSubstitutability::test_alternative_pure_function_is_used_when_supplied` (an entirely different pure function substituted at the call site, no code change to the composition root).

**G1-EXIT-14 — "No real Secret/provider dependency."**
`PASS`. No `SecretRef`/credential-resolution code exists anywhere in `src/legoai` (F8a/F8b explicitly declined to introduce Secret plumbing per their own tasks' instructions). No provider SDK import anywhere — confirmed by the existing `test_no_ai_or_agent_framework_imported_by_production_source` architecture test (scans for `semantic_kernel`, `agent_framework`, `openai`, `anthropic`, `ollama`, `langchain`, `langgraph`), passing.

**G1-EXIT-15 — "No optional AI dependency or unnecessary service."**
`PASS`. `pyproject.toml` `dependencies = []` (confirmed by direct read in this review); wheel `METADATA` carries no `Requires-Dist` line (confirmed by direct wheel inspection in this review, §24.2). No network/broker/cache/database-server code anywhere in `src/legoai`.

**G1-EXIT-16 — "Applicable tests/static/package checks pass; counterevidence and limitations remain visible."**
`PASS` for the checks-pass half (§24.2's re-run results). For "limitations remain visible": every batch's own residual-risk section is preserved in this document (§18, §21-23) and not overwritten by this review; G1-EXIT-08's gap is recorded here rather than concealed, which is itself evidence this criterion is being honored rather than merely claimed.

**G1-EXIT-17 — "Gate-2 blockers below have named owners and are not relabeled optional to claim progress."**
`PASS`. `planning/GATE-1-FOUNDATION-IMPLEMENTATION.md` §18.2's "Remaining Gate-2 blockers" table (Qualified persistence, Finite independent roots, Current owner-boundary enforcement, Resources and Approval, Real Plugin lifecycle and Catalog, Evidence custody, Supervision, Protected Tool/Adapter, Final arbitration, Retry/reconciliation, Composed crash/restart proof, Conditional features) already names an owner and accepted basis for every row in the Accepted planning document itself; this review neither weakens nor relabels any of them, and confirms none has been silently implemented as a shortcut (§24.4 below).

### 24.4 Cross-milestone regression review (task §7)

- **F4 semantics vs F5 representation**: `application/ports.py`/`application/values.py` (F4) confirmed byte-for-byte unchanged by every later batch (`git diff --stat HEAD` checked at the close of F5 through F8b; re-confirmed here — zero uncommitted diff against them). F5's `codec.py` encodes/decodes the exact F4 value shapes without adding fields.
- **F4 Port vs F6a SQLite realization**: `SQLiteConfigurationStore` implements `ConfigurationStorePort` structurally (no inheritance, pure Protocol conformance — `tests/unit/application/test_sqlite_store.py` and the shared contract suite both instantiate it directly against the same Protocol).
- **F5 codec vs F6b recovery**: `recovery.py` imports and calls `codec.decode_revision_content`/`decode_publication_result`/`loads` directly (confirmed by source read) — it does not reimplement decoding.
- **F7 declarations vs F8b composition**: confirmed inert in G1-EXIT-09 above; `text_normalization_declaration()` (F8b) constructs an ordinary `PluginDeclaration` with no new field.
- **F8a observation vs F8b containment**: `compose_direct`'s `_emit_best_effort` is the only broad `except Exception` in the entire private composition module (confirmed by source read — one occurrence, explicitly commented as diagnostic-boundary-only).
- **F2 configuration vs F8b deterministic composition**: `compose_direct` calls the unchanged F2 `compose_configuration` and passes its `EffectiveConfiguration` straight into F8b's `normalize_text` — no new configuration object was invented.

No later milestone was found to have retroactively altered an earlier invariant.

### 24.5 Verdict

```text
GATE_1_EXIT_VERDICT = NOT_READY
```

**Reason**: G1-EXIT-08 is `PARTIAL`, not `PASS` — migration-interruption evidence, explicitly called for by the Gate-1 plan's own §9.3, does not exist. Every other criterion (16 of 17) is `PASS` with concrete, independently-verified evidence. This is a narrow, precisely bounded gap, not a systemic one: no production capability is missing (the plan itself says no real migration code is warranted yet), only one class of test evidence (a synthetic old-format decode fixture plus a migration-interruption test, following the exact subprocess-kill pattern F6b's own `TestSubprocessDurability` already establishes).

**Recommended remaining work before re-attempting Gate-1 exit**: one small, bounded follow-up batch, owned by F5/F6a, adding (a) one clearly-labeled synthetic "legacy" record-schema-version-0 fixture in the F5 codec tests proving a decode-time version-mismatch rejection path distinct from the current "future unsupported version" tests already in place, and (b) one subprocess-based test in the F6a/F6b test area proving that a killed-mid-migration-marker-write process leaves the store in its prior complete state on reopen (using the same barrier/kill pattern as `test_uncommitted_transaction_absent_after_abrupt_termination`). Neither requires implementing a real migration runner; F6a's existing schema-version check already provides the fail-closed behavior the interruption test needs to observe.

Gate 2 must not begin until this batch closes G1-EXIT-08 and this review is re-run.

---

## 25. G1-EXIT-08 remediation (implementation status)

```text
G1_EXIT_08_REMEDIATION = COMPLETE
F9_RE_REVIEW_REQUIRED = YES
```

**This is a narrow remediation batch only — it does not itself constitute a re-run of F9.** The authoritative Gate-1 exit review must still be independently re-performed against all seventeen criteria before any `GATE_1_EXIT_VERDICT` is updated.

**Evidence added**: `tests/support/migration_fixture.py` (test-only synthetic predecessor construction + migration transform) and `tests/integration/application/test_migration_interruption.py` (16 tests: 7 control-case/successful-migration tests, 6 real-subprocess interruption tests, 1 precondition test, 2 fixture-hygiene tests).

**Zero production-code changes.** `git diff --stat HEAD -- src/legoai` is empty — confirmed at the close of this batch. The migration transform reuses F6a's own `_schema_statements()`/`_physical_schema_version()` private helpers directly (imported by the test fixture, not duplicated), so the "current" side of the migration is guaranteed structurally identical to production with zero drift risk. `SQLiteConfigurationStore`, `ConfigurationStorePort`, F5's codec, and F4's semantic values are all confirmed unchanged; no bug was found in any of them that would have required stopping.

**Synthetic predecessor is not a historical release.** `SYNTHETIC_PREDECESSOR_SCHEMA_VERSION = 0` is documented, in the fixture module's own docstring and in the test file's own module docstring, as never having been a released LegoAI representation — F6a's real schema has been version 1 since its first implementation. The fixture's one deliberate structural difference from v1 (an outstanding duty embedded as a nullable JSON column on the result row, `duty_json_embedded`, instead of living in a separate `config_duty` table) is a plausible pre-refactor shape invented solely to give the migration something genuine to transform, not a claim about what LegoAI ever shipped.

**Migration mechanics**: one explicit `BEGIN IMMEDIATE` transaction (LOCAL-PERSISTENCE-REALIZATION.md §11) performing table renames (`config_revision_v0`→`config_revision`, `config_head_v0`→`config_head`, SQLite auto-updating the FK reference), current-shape table creation via F6a's own schema statements, duty extraction into the new `config_duty` table, a result-row copy dropping the obsolete embedded column, and the physical `store_metadata.schema_version` marker bumped to 1 **last**, immediately before `COMMIT`.

**Control case (successful migration)**: `TestSuccessfulMigrationControlCase` proves migration actually completes and the resulting store is fully usable through the **unchanged** production `SQLiteConfigurationStore`/`qualify_store` APIs — including exact preservation of the historical revision content, the operation result without recomputation, `EffectExtent.UNKNOWN` (never downgraded to `NONE`), the outstanding duty (still outstanding, never auto-resolved), and the distinctness of `OwnerRevision` (H) from `ConfigurationRevisionRef` (R) after migration.

**Interruption case (the primary required proof)**: `TestInterruptedMigration` launches a real child OS process (`subprocess.Popen` + `sys.executable`) running the migration with `stop_before_commit=True`; the child performs every structural step, writes a ready-marker file, then blocks in `time.sleep(3600)` — deliberately never reaching the schema-version bump or `COMMIT`. The parent polls for the marker (no sleep-based timing guess) and then calls `process.kill()` — a real, abrupt OS-level termination, not exception injection. Verified outcomes: the physical table set is byte-for-byte the original v0 set (no `config_duty`/renamed tables exist at all — SQLite's transactional DDL fully rolled back every structural step); `store_metadata.schema_version` is still exactly `0`; `SQLiteConfigurationStore(path)` raises the existing `UnsupportedPhysicalSchemaVersionError` unchanged; `qualify_store(path)` returns the existing `RecoveryStatus.BLOCKED` with `physical_schema_version == 0` and zero scopes interpreted; repeated qualification attempts are stable; qualification itself performs no silent repair or cleanup of the interrupted file.

**Central invariant proven** (never a mixed-version healthy report): at no point does the interrupted store expose `some-predecessor-rows + some-current-rows + a current schema marker` as `QUALIFIED` — the schema-version check happens before any per-scope interpretation is attempted at all, exactly as F6b's existing `qualify_store` already implements it.

Verified before closing this batch: `pytest` 634 passed (was 618 before this batch; +16 new); `mypy src tests` — no issues in 64 source files; `ruff check`/`ruff format --check` — clean; coverage unchanged at 94% overall (confirming zero production lines were added); architecture tests unchanged at 141 passed (no boundary rule needed — test code importing production private helpers is unrestricted); package-install tests unchanged at 5 passed; Document Pack unchanged at 268 passed/64 skipped; zero new runtime dependencies; no canonical document changed; no DocuMind file touched.

**F9 must be re-run** to update `GATE_1_EXIT_VERDICT`. This batch does not itself declare Gate 1 passed.

---

## 26. F9 re-review (post G1-EXIT-08 remediation)

```text
F9_RE_REVIEW = COMPLETE
GATE_1_EXIT_VERDICT = READY
```

This is a re-review only. No implementation was added, changed, or planned in this task. The only repository change from this task is this section (`planning/NEXT-CORE-IMPLEMENTATION-BATCH.md`); `git status --porcelain=v1` was empty at the start of this task.

No `planning/GATE-1-EXIT-REVIEW.md` file exists in this repository (`ls planning/` confirmed: `DOCUMIND-EXTRACTION-ASSESSMENT.md`, `GATE-1-FOUNDATION-IMPLEMENTATION.md`, `IMPLEMENTATION-READINESS.md`, `NEXT-CORE-IMPLEMENTATION-BATCH.md`, `documind/`, `runtime/`). The established convention in this repository has been to record all F9/Gate-1-exit review content in this document (§24 = original review, §25 = remediation status). Per this task's own instruction not to create a second competing exit-review document unless repository convention explicitly requires one, this re-review is recorded here, continuing that convention, rather than creating the named-but-nonexistent file.

### 26.1 Original verdict and gap (unchanged history — not overwritten)

§24.5 originally recorded `GATE_1_EXIT_VERDICT = NOT_READY`, 16 PASS / 1 PARTIAL / 0 FAIL, with the sole partial being **G1-EXIT-08** ("Revision/conflict/duplicate/lost-ack/process-restart and migration-interruption evidence for the selected owner") — specifically the absence of any migration-interruption evidence, against the Gate-1 plan's own §9.3 instruction to "use a clearly synthetic predecessor fixture to exercise interrupted migration." That original PARTIAL determination and its full reasoning remain intact in §24.3 above, unedited by this section.

### 26.2 G1-EXIT-08 re-evaluation

`PARTIAL` → **`PASS`**, on direct re-verification of the remediation evidence against each required point:

1. **Synthetic predecessor clearly test-only, not misrepresented as historical.** `tests/support/migration_fixture.py` lives under `tests/`, is never imported by any production module — confirmed by both a dedicated AST-scan test (`test_migration_fixture_module_is_test_only_not_imported_by_production`, re-run passing) and a direct `grep -rn migration_fixture src/legoai` (no matches, re-confirmed in this review). Its module docstring states explicitly that `SYNTHETIC_PREDECESSOR_SCHEMA_VERSION = 0` "was never a released LegoAI representation."
2. **Migration transactional.** Directly re-read `migrate_predecessor_to_current` (lines ~255-350): opens one `BEGIN IMMEDIATE`, performs all renames/creates/data-moves inside it, commits once at the end. SQLite's transactional DDL guarantees all-or-nothing rollback on interruption.
3. **Real subprocess termination before COMMIT.** Directly re-read `test_migration_killed_before_commit_leaves_predecessor_intact` (lines ~189-233): launches `subprocess.Popen([sys.executable, "-c", child_script], cwd=REPO_ROOT, ...)` — a genuine separate OS process, not a thread, mock, or exception injection — polls `ready_marker.exists()` in a bounded loop (0.05s interval, 10s deadline; not a fixed sleep guess), then calls `process.kill()` (real OS-level abrupt termination) followed by `process.wait(timeout=10)`.
4. **Schema marker not advanced prematurely.** Confirmed by direct source read: the `stop_before_commit` branch writes `ready_marker` then calls `time.sleep(3600)` and returns, never reaching the `store_metadata.schema_version` bump or `COMMIT`, which are the last two statements in the non-interrupted path.
5. **Interrupted migration leaves no partial current-schema state.** `test_migration_killed_before_commit_leaves_predecessor_intact` asserts `_physical_tables(path) == original_tables` and the explicit absence of `config_duty`/`config_revision`/`config_head`/`config_result` post-kill — re-run passing.
6. **Restart doesn't misinterpret predecessor state as current.** `test_interrupted_store_is_refused_by_production_construction` asserts `SQLiteConfigurationStore(path)` raises the existing, unmodified `UnsupportedPhysicalSchemaVersionError`.
7. **Recovery blocks safely.** `test_interrupted_store_is_blocked_by_recovery_qualification` and `test_interrupted_migration_never_reports_qualified` assert `qualify_store(path)` returns the existing, unmodified `RecoveryStatus.BLOCKED` with `physical_schema_version == 0` and `scopes == ()` — no per-scope interpretation is attempted once the version check fails, so no mixed-state report is ever possible. `test_repeated_recovery_attempts_remain_stable_after_interruption` and `test_no_silent_repair_or_cleanup_after_interruption` confirm this is stable and non-mutating across repeated attempts.
8. **Successful control case proves genuine migratability.** `TestSuccessfulMigrationControlCase` (7 tests) runs the same transform to completion (no kill) and proves the resulting store is usable through the unchanged production `SQLiteConfigurationStore`/`qualify_store` APIs, ending in `RecoveryStatus.QUALIFIED`.
9. **Semantic identities/results/duties/history intact.** `test_migration_preserves_historical_revision_content_exactly`, `test_migration_preserves_operation_result_without_recomputation`, `test_migration_preserves_unknown_effect_exactly` (`EffectExtent.UNKNOWN`, never downgraded to `NONE`), `test_migration_preserves_outstanding_duty_as_outstanding`, and `test_migration_preserves_owner_revision_and_configuration_revision_distinctly` (explicit `not hasattr` checks proving H and R remain structurally distinct types) — all re-run passing.
10. **No production-code changes.** `git diff --stat HEAD -- src/legoai` — empty, re-confirmed in this task.

Additional robustness check performed in this re-review (not present in the original remediation report): the full `test_migration_interruption.py` file was run three independent times in a row to rule out subprocess-timing flakiness — **16/16 passed each time** (3.41s, 2.15s, 1.60s). No flakiness observed.

**G1-EXIT-08 = PASS.**

### 26.3 Regression reconfirmation for the other sixteen criteria

The remediation batch added only two test files (`tests/support/migration_fixture.py`, `tests/integration/application/test_migration_interruption.py`) plus a two-line addition to the sdist expected-file list in `tests/architecture/test_package_install.py`. `git diff --stat HEAD -- src/legoai` is empty, so no criterion whose evidence cites production source in §24.3 has had that source altered. Regression evidence re-run fresh in this task (not taken from the remediation batch's own report):

- `pytest` (Core): **634 passed** (matches remediation report exactly: 618 original + 16 new).
- `mypy src tests`: **"Success: no issues found in 64 source files."**
- `ruff check src tests`: **"All checks passed!"** `ruff format --check src tests`: **"64 files already formatted."**
- `coverage` (branch, same module set as §24.2): **94% overall**, TOTAL 1404 stmts / 78 miss / 502 branch / 33 partial — identical to the pre-remediation figure, confirming zero production lines were added or altered.
- `tests/architecture` suite: **141 passed** — identical count to §24.3's G1-EXIT-04 evidence, confirming import-boundary/inertness/no-ambient-state/no-Gate-2-symbol rules all still hold unchanged.
- Document Pack (`packages/legoai-document`, independent `.venv`): **268 passed, 64 skipped** — identical to §24.2, confirming the Document Pack was untouched.
- Fresh `uv build --no-build-isolation` + wheel inspection: file list identical to the pre-remediation wheel (35 files, no new production module); `METADATA` shows `Requires-Python: <3.15,>=3.14` and **no `Requires-Dist` line at all** — zero new runtime dependencies, matching §24.2/§26.6.
- Package-install tests: **5 passed**, including the fresh-wheel-build-and-install test (now also covering the two new sdist-listed test files, per the one non-production edit this remediation made).

On this basis, **G1-EXIT-01 through G1-EXIT-07 and G1-EXIT-09 through G1-EXIT-17 are reconfirmed `PASS`**, retaining the original evidence citations in §24.3 (which remain valid, since nothing they depend on changed) rather than re-deriving them from zero. No regression was found in any of the sixteen.

### 26.4 Production source verification

`git diff --stat HEAD -- src/legoai` — empty. Zero production source changes from either the remediation batch or this re-review task.

### 26.5 Canonical authority documents verification

`git status --porcelain=v1 -- intent.md SPEC.md architecture/ARCHITECTURE.md contracts/CONTRACTS.md plugin-spec/PLUGIN-SPEC.md security/SECURITY.md evaluation/EVALUATION.md conformance/CONFORMANCE.md adrs` — empty. No canonical document or Accepted ADR was touched. `git status --porcelain=v1` filtered for `documind` — no output; the DocuMind extraction work is untouched.

### 26.6 Dependency and wheel-metadata verification

`pyproject.toml` still declares `dependencies = []`. Fresh wheel `METADATA` (rebuilt in this task) carries no `Requires-Dist` line at all — identical to the pre-remediation wheel. `uv.lock` unchanged (build/test tooling only). Zero new runtime dependencies introduced by either the remediation batch or this re-review.

### 26.7 Gate-2 absence reconfirmation

`grep -rln "class CapabilityResolver\|class Execution\|class PluginAdmission\|class ExecutionContext\|class ModelPort\|class Agent\b\|class Workflow\b" src/legoai` — no matches. `find src/legoai -iname "*execution*" -o -iname "*resolver*" -o -iname "*catalog*" -o -iname "*admission*"` — no matches. No Execution, ExecutionContext, CapabilityResolver runtime, Plugin admission/activation, authorization enforcement, dispatch, resource claim enforcement, async supervision, ModelPort, Embedding, Agent runtime, or Workflow runtime exists anywhere in the repository.

### 26.8 Final seventeen-item checklist

| Criterion | Previous | Re-review | Evidence |
|---|---|---|---|
| G1-EXIT-01 — installable distribution / wheel-sdist smoke test | PASS | PASS | §24.3; wheel/sdist rebuilt and re-inspected in this task, §26.3/§26.6 |
| G1-EXIT-02 — reproducible test/type/lint/format/build loop | PASS | PASS | §24.3; all commands re-run fresh in this task, §26.3 |
| G1-EXIT-03 — minimal nominal values / safe explicit contexts with negative tests | PASS | PASS | §24.3; unchanged, no source diff |
| G1-EXIT-04 — enforced import/dependency direction, inert package parents | PASS | PASS | §24.3; 141 architecture tests re-run passing, §26.3 |
| G1-EXIT-05 — immutable candidate composition / exact published revision | PASS | PASS | §24.3; unchanged, no source diff |
| G1-EXIT-06 — SQLite owner boundary, compound guards/results/duties, durability disclaimer | PASS | PASS | §24.3; unchanged, no source diff; further corroborated (not superseded) by the new interruption evidence in §26.2 |
| G1-EXIT-07 — safe versioned serialization, supported-reader rejection | PASS | PASS | §24.3; unchanged, no source diff |
| G1-EXIT-08 — revision/conflict/duplicate/lost-ack/process-restart/migration-interruption evidence | **PARTIAL** | **PASS** | §26.2; `tests/support/migration_fixture.py` + `tests/integration/application/test_migration_interruption.py`, 16/16 passing across 3 independent runs, zero production changes |
| G1-EXIT-09 — inert Plugin/Capability declarations, no executable inactive binding | PASS | PASS | §24.3; unchanged, no source diff |
| G1-EXIT-10 — explicit Principal/Tenant inputs, no ambient/fake authority | PASS | PASS | §24.3; unchanged, no source diff |
| G1-EXIT-11 — safe source/Evidence/provenance references, duty ≠ custody | PASS | PASS | §24.3; unchanged, no source diff |
| G1-EXIT-12 — bounded safe local diagnostics with failure tests | PASS | PASS | §24.3; unchanged, no source diff |
| G1-EXIT-13 — deterministic internal non-effectful composition, substitution test | PASS | PASS | §24.3; unchanged, no source diff |
| G1-EXIT-14 — no real Secret/provider dependency | PASS | PASS | §24.3; unchanged, no source diff |
| G1-EXIT-15 — no optional AI dependency / unnecessary service | PASS | PASS | §24.3; wheel METADATA re-checked in this task, §26.6 |
| G1-EXIT-16 — applicable checks pass, counterevidence/limitations remain visible | PASS | PASS | §24.3/§26.3; original PARTIAL history for G1-EXIT-08 preserved above, not concealed |
| G1-EXIT-17 — named Gate-2 blockers, not relabeled optional | PASS | PASS | §24.3; §18.2 blocker table unchanged, Gate-2 absence reconfirmed, §26.7 |

**17 / 17 PASS. 0 PARTIAL. 0 FAIL.**

### 26.9 Final verdict

```text
GATE_1_EXIT_VERDICT = READY
```

**Artifact status: ACCEPTED — GATE 1 EXIT QUALIFIED.**

All seventeen Gate-1 §18.1 foundation-exit criteria are `PASS`, independently re-verified from source in this task, with the previous sole gap (G1-EXIT-08) closed by the remediation batch's migration-interruption evidence and no regression found in any of the other sixteen. Production source, canonical authority documents, the runtime dependency set, and the absence of any Gate-2 concept are all reconfirmed unchanged.

**Gate 1 foundation is qualified. Gate 2 may now be planned in a separate task.** No Gate-2 planning or implementation was performed in this task.
