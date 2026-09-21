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
