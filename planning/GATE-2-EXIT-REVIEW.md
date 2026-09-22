status: ACCEPTED — GATE 2 EXIT QUALIFIED

# Gate-2 Exit Review

Reviewer role: Principal Software Architect / Conformance Reviewer / Security Reviewer / implementation maintainer.
Scope: this is a review only. No remediation, no ModelPort/Embedding/DocuMind/Agent/Workflow/MCP/A2A work was started or planned in this task.

```text
GATE_2_EXIT_VERDICT = READY
```

---

## 1. Executive result

Gate-2's own accepted target — ADR-015's "the governed executable slice," realized by M1 through M11 — is **qualified within an explicitly narrow, documented scope**: one statically known, pure, synchronous, trusted-host deterministic capability (F8b's `normalize_text`), invocable only after the complete governed path (current authorization, Approval consumption, Catalog revalidation, dispatch arbitration, structured supervision) has actually been crossed by the exact reference realizations this review inspected.

No mandatory exit criterion derived from accepted ADR authority was found to be missing, partial, unproven, or contradicted for **this narrow scope**. Three deliberately deferred items (permit replay/exactly-once, resource-runtime gating, invocation-result Evidence custody, configuration-revision revalidation) were each individually re-derived from ADR-007/008/009/003 and CONTRACTS directly (not merely trusted from milestone completion reports) and found to be **legitimately out of scope for the currently proven slice**, not silently excused gaps — each is written into §16's deferred-items table with an explicit blocking trigger for when it stops being deferrable.

`GATE_2_EXIT_VERDICT = READY`, strictly bounded to §17's qualified scope. §18 states, with equal weight, everything this gate does **not** prove.

## 2. Authority reviewed

Read in this task: `intent.md`, `SPEC.md`, `architecture/ARCHITECTURE.md`, `contracts/CONTRACTS.md` (relevant sections: §§10, 25, 29, 30, CTR-027/028/059-061), `plugin-spec/PLUGIN-SPEC.md` (cross-checked against ADR-006), `security/SECURITY.md` (cross-checked against ADR-005 §§4, 11-14, 19), ADR-005 (fully, §§1-19), ADR-006 (targeted: bootstrap/lifecycle/DEGRADED/publication sections), ADR-007 (fully, prior session + re-verified this session), ADR-008 (targeted: identity/idempotency/downstream-impact sections), ADR-009 (fully, this session), ADR-015 (fully, prior session), `planning/GATE-2-IMPLEMENTATION-PLAN.md` (all 38 sections), `planning/NEXT-CORE-IMPLEMENTATION-BATCH.md` (all pointer sections). Current source under `src/legoai/` and current tests under `tests/` were read and spot-verified directly (see per-criterion evidence below) rather than trusted from milestone completion reports alone, per this task's own instruction.

**No numbered Gate-2 exit checklist exists** in any accepted planning artifact. `planning/GATE-2-IMPLEMENTATION-PLAN.md` §"authority" states this explicitly and points to `ADR-INDEX.md` §7's ordering statement and ADR-015's own target phrase ("supervised live work and the governed executable slice") as the sole authoritative exit definition. This review therefore derives the checklist in §5 strictly from ADR-005 through ADR-009 and ADR-015's mandatory requirements plus CONTRACTS' cross-cutting rules — never from invented product-readiness criteria.

## 3. Gate-1 handoff

Spot-checked (not re-run from scratch, since no regression was found):

| Invariant | Result | Evidence |
|---|---|---|
| Configuration semantics intact | PASS | `src/legoai/application/values.py`, `src/legoai/reference/application/configuration.py` untouched by any Gate-2 commit; `tests/unit/application/*` still pass (part of the 1315 total) |
| Owner-local persistence/recovery intact | PASS | `src/legoai/reference/application/{sqlite_store,recovery}.py` untouched; `tests/unit/application/test_sqlite_store.py`, `test_recovery.py` pass |
| Plugin/Capability declarations remain inert | PASS | see G2-EXIT-31 below (repo-wide check, not just F7) |
| Safe Observation remains non-authoritative | PASS | `legoai.observability` untouched since F8a; M10/M11 deliberately did **not** add Observation emission (documented in `reference/execution.py` module docstring: "no current consumer") |
| Private deterministic composition remains valid | PASS | `src/legoai/runtime/_composition/direct.py` confirmed **byte-for-byte unchanged** this session (`git diff` empty for that path); its own test suite `tests/integration/composition/test_direct.py` still passes |
| No canonical regressions | PASS | full Core suite 1315 passed, 0 failed (§4 below) |

## 4. Full verification run (this session)

| Check | Command | Result |
|---|---|---|
| Core pytest | `pytest` (full) | **1315 passed**, 0 failed, 0 skipped |
| Document Pack pytest | `pytest` in `packages/legoai-document` | **268 passed, 64 skipped** (pre-existing characterization-test skips, unrelated to Gate-2) |
| mypy | `mypy src tests` (strict) | **Success: no issues found in 97 source files** |
| ruff check | `ruff check src tests` | **All checks passed** |
| ruff format | `ruff format --check src tests` | **97 files already formatted** |
| Architecture tests | `pytest tests/architecture` | **229 passed** |
| Coverage | `coverage run --branch --source=legoai` + `pytest` | **97% overall** (2631 stmts / 79 miss; 1086 branches / 34 partial) — see §16.1 for per-module breakdown |
| Wheel/fresh-install | `pytest tests/architecture/test_package_install.py -v` | **5 passed**, including `test_build_and_fresh_wheel`, which builds a clean wheel, installs it in an isolated venv with `--no-deps`, and runs the complete real governed slice (publish → resolve → authorize → dispatch → coordinate → `invoke_governed_text_normalization`) to a genuine `SUCCEEDED`/`"hello world"` result |
| Runtime dependencies | `pyproject.toml` | `dependencies = []` (zero); dev-only group unchanged |
| Race/concurrency tests | 5 consecutive re-runs (see §13) | all pass every run, no flakiness observed |

## 5. Derived Gate-2 exit checklist (`G2-EXIT-01`…`G2-EXIT-76`)

No accepted numbered checklist exists (§2), so each item below is a review-local identifier derived directly from ADR-005/006/007/008/009/015 + CONTRACTS, scoped to the one accepted exit target: "one governed deterministic executable invocation." Each appears exactly once. `PASS (scoped)` means the criterion is satisfied **for the narrow proven slice**, with the exact scope boundary stated — never a claim of general-purpose completeness.

### 5.1 M1 — Execution semantics

| ID | Criterion | Result | Evidence |
|---|---|---|---|
| G2-EXIT-02 | `ExecutionId` distinct from `OperationId`; no alias | PASS | `src/legoai/execution/values.py` — `ExecutionId`/`OperationRef` remain separate dataclasses; `ExecutionContext.causation != ExecutionContext.operation` enforced by `__post_init__`; `tests/unit/execution/test_values.py` |
| G2-EXIT-02b | Exact 10 `ExecutionState` members preserved unchanged since M1 | PASS | `src/legoai/execution/values.py:45-62` — `created, admitted, running, waiting, suspended, cancelling, succeeded, failed, cancelled, rejected`; `assert len(execution_values.ExecutionState) == 10` in the wheel smoke script (`tests/architecture/test_package_install.py`) still asserts this after M9/M10/M11 |
| G2-EXIT-02c | `SecurityContextRef` remains opaque/non-authoritative | PASS | `execution/values.py` docstring: "Holding this reference is not proof that the referenced authorization currently remains valid"; M10/M11 only ever *resolve* it through `SecurityContextResolutionPort`, never treat the reference itself as sufficient |
| G2-EXIT-02d | `ExecutionContext` remains explicit tenant/security scoped, no arbitrary payload/metadata bag | PASS | `ExecutionContext` fields unchanged since M1 (`execution_id, operation, tenant_context, security_context_ref, correlation_id, trace_id, deadline, causation`); no `dict[str, Any]`/`payload` field exists anywhere in `execution/values.py` or `execution/ports.py` |
| G2-EXIT-02e | `ExecutionResult` preserves `EffectExtent` semantics; terminal-state restriction unweakened | PASS | `ExecutionResult.__post_init__` still restricts `final_state` to `{SUCCEEDED, FAILED, CANCELLED, REJECTED}` and still enforces `REJECTED ⇒ EffectExtent.NONE` — unchanged since M1, confirmed by direct read this session |

### 5.2 M2 — Governance semantics

| ID | Criterion | Result | Evidence |
|---|---|---|---|
| G2-EXIT-03 | `Principal ≠ Grant ≠ Approval`; `PolicyRef` inert/versioned; no credential/secret field; no bool authority shortcut | PASS | `src/legoai/governance/values.py` — `Grant`/`Approval`/`PolicyRef` are separate dataclasses; `AuthorizationOutcome` is a 3-member enum (`ALLOWED/DENIED/UNAVAILABLE`), never a bool (confirmed §9's tri-state re-check); no field named `secret`/`credential`/`token` anywhere in `governance/values.py` or `governance/ports.py` |
| G2-EXIT-03b | Grant does not mean currently valid; Approval does not mean currently usable | PASS | `Grant`/`Approval` are pure declarative records (issuer, scope, validity window, `max_uses`); *current* validity is a separate, later-checked fact via `GrantStatePort.current_revocation_status`/`ApprovalUsePort.current_use_state` (M4), never derivable from the value alone |

### 5.3 M3 — Resource semantics

| ID | Criterion | Result | Evidence |
|---|---|---|---|
| G2-EXIT-04 | `ResourceClaim ≠ availability ≠ authorization`; `ResourceQuantity` preserves amount-kind semantics; no `ResourcePort`/allocation engine exists | PASS (scoped) | `src/legoai/resources/values.py` unchanged since M3 — purely declarative, no Port, no engine |
| G2-EXIT-04b | Does Gate-2 exit require real resource gating for the first governed slice? | **NOT_APPLICABLE, independently re-derived, not assumed** | CONTRACTS CTR-062 row 9 ("Resource obligations"): "Applicable §6/§15.3 units/claims/deadlines/uncertainty; **explicit policy-permitted empty applicability if none**" — this is the canonical text that legitimizes a *declared* zero-resource-requirement capability proceeding without a `ResourcePort`. F8b's `normalize_text` (`src/legoai/reference/deterministic.py`) performs no I/O, has no configured resource dimension, and its `PluginDeclaration` carries no resource claim of any kind — the "explicit policy-permitted empty applicability" is satisfied structurally by the capability declaring nothing, not by silent omission. This does **not** establish that resource gating is solved; see §16 deferred-items table for the exact future trigger. |

### 5.4 M4 — Current authority

| ID | Criterion | Result | Evidence |
|---|---|---|---|
| G2-EXIT-05 | Current Grant/Approval-use/Policy-currency state actually checked (not historical/cached) | PASS | `src/legoai/reference/governance.py::DeterministicAuthorizationEvaluator.evaluate` calls `self.grant_state.current_revocation_status`, `self.approval_use.current_use_state`, `self.policy_currency.current_status` on every call, never caches; `tests/contract/test_authorization.py` |
| G2-EXIT-05b | Tenant mismatches fail closed | PASS | `_grant_covers`/`_approval_covers` in `reference/governance.py` compare exact scope; `DispatchRequest`/`CoordinationRequest`/`GovernedInvocationResult`-path all raise `ValueError("...tenant mismatch")` at construction (`execution/ports.py` `__post_init__`s) |
| G2-EXIT-05c | Unknown state does not ALLOW | PASS | `RevocationStatus.UNKNOWN` and `PolicyCurrencyStatus.UNKNOWN` both map to `AuthorizationOutcome.UNAVAILABLE`, never `ALLOWED` — `reference/governance.py:115-122`; tested by `test_unknown_revocation_state_fails_closed_unavailable` (`tests/unit/reference/test_execution.py`) |
| G2-EXIT-05d | `AuthorizationDecision` is tri-state, non-bool | PASS | `AuthorizationOutcome` = `{ALLOWED, DENIED, UNAVAILABLE}` (§ G2-EXIT-03 evidence) |
| G2-EXIT-05e | Historical authority ≠ current authority | PASS | see G2-EXIT-55 (dedicated cross-test) |
| G2-EXIT-06 | Interval semantics: `valid_from` inclusive, `expires_at` exclusive; no wall-clock leak into values | PASS | `reference/governance.py:68,70,84,86` — `established_at < valid_from` (so `==` passes ⇒ inclusive) and `established_at >= expires_at` (so `==` fails ⇒ exclusive), re-verified by direct grep this session; `established_at` is always caller-supplied on `SecurityContext`, never `datetime.now()` inside `governance/values.py` or `reference/governance.py` |

### 5.5 M5 — Plugin lifecycle

| ID | Criterion | Result | Evidence |
|---|---|---|---|
| G2-EXIT-07 | `PluginDeclaration` remains inert; validation ≠ admission; lifecycle state separate from declaration; ACTIVE embeds no executable binding; trusted-host assumption explicit; ADR-012 unresolved | PASS | `src/legoai/plugins/values.py` (declaration, no callable field); `src/legoai/plugins/ports.py` (`PluginLifecycleState`, 9 members, separate from `PluginDeclaration`); `reference/plugins.py` module docstring cites ADR-006 §8 explicitly; `grep -rn "ADR-012"` across `src/` shows only "remains unresolved"/"Proposed" citations, never a resolution claim |
| G2-EXIT-08 | No misleading equation of `VALIDATED`/`ACTIVE`/"Catalog published" with a stronger canonical trust/admission claim than ADR-006 supports | PASS | `plugins/ports.py` docstring for `PluginLifecycleState` and `capabilities/ports.py` module docstring both explicitly state "Catalog presence means 'published and eligible for consideration' — never 'authorized for this caller', 'resource-available', 'trusted', or 'safe to dispatch'"; no source file or docstring anywhere in `src/legoai` uses the word "admitted"/"ADMITTED" to describe a Plugin lifecycle state (the canonical ADR-006 lifecycle states are `discovered/validated/initialized/active/degraded/stopping/failed/stopped/retired` — no literal ADMITTED state exists, confirmed by direct enum read) |

### 5.6 M6 — Catalog

| ID | Criterion | Result | Evidence |
|---|---|---|---|
| G2-EXIT-09 | Tenant-scoped; ACTIVE-only publication (current realization); entries inert; multiple providers preserved; no ranking; no executable binding; no authorization/resource-availability implication | PASS | `src/legoai/reference/catalog.py::InMemoryCatalog.publish/snapshot` key by `TenantContext`; `CatalogEntry` (`capabilities/ports.py`) carries no callable; `tests/unit/reference/test_capability_resolution.py`/`test_capability_resolution.py`'s multi-candidate tests confirm no ranking is applied |
| G2-EXIT-10 | DEGRADED publication gap disposition | **PASS (scoped), explicitly not excused** | `capabilities/ports.py` module docstring documents the gap in full, citing ADR-006 §9's own text ("Ordinary eligibility requires an active activation, **or a degraded activation whose contributions still meet every hard requirement**, plus current suitability and required evidence"). Re-derived independently this session: ADR-006 describes DEGRADED as an *available* eligibility path for Plugins that have a genuine health/degradation concept — it does not mandate that the reference Catalog realization support publishing DEGRADED entries before Gate-2's own accepted exit target (one governed deterministic invocation) can qualify. F8b's `normalize_text` has no health/degradation concept at all (pure, local, no external dependency) and therefore never exercises this path. **This is not required for the current exit**, but it is a real, standing gap that blocks onboarding any future Plugin/Provider with a genuine degraded-operation mode — recorded as a blocker-trigger in §16, not silently closed. |

### 5.7 M7 — Runtime capability resolution

| ID | Criterion | Result | Evidence |
|---|---|---|---|
| G2-EXIT-11 | Resolution consumes only `CatalogSnapshot`; tenant scope preserved; version semantics reused from F7; `NO_MATCH` normal, `RESOLVED` unique, `AMBIGUOUS` preserved; no ranking; no provider binding; `catalog_revision` attributed | PASS | `src/legoai/reference/resolution.py::resolve` signature takes only `(requirement, snapshot, resolved_at=...)`; `ResolutionStatus` = `{RESOLVED, NO_MATCH, AMBIGUOUS}`; `CapabilityResolution.catalog_revision` field present and asserted in `tests/unit/reference/test_capability_resolution.py` and in the wheel smoke script |
| G2-EXIT-12 | Catalog staleness = "entry no longer present in current snapshot," not revision-inequality; compatible with ADR-007; unrelated mutations do not wrongly invalidate a still-published candidate | PASS | `reference/execution.py::DeterministicDispatchArbiter.arbitrate` — `if request.resolved_entry not in snapshot.entries: ... STALE` (entry-presence check, not `snapshot.revision != permit_revision`); dedicated test `test_catalog_revision_advancing_without_withdrawal_still_permits` (`tests/unit/reference/test_execution.py`) proves an unrelated publish that bumps the Catalog revision does **not** invalidate a still-published candidate; ADR-006 §9's own text ("publishing a row is not... an irrevocable eligibility guarantee") is the cited authority, consistent with ADR-007's "current applicability" language — no contradiction found |

### 5.8 M8 — Evidence custody

| ID | Criterion | Result | Evidence |
|---|---|---|---|
| G2-EXIT-13 | `EvidenceRequirement ≠ EvidenceRecord`; Evidence ≠ Observation (structurally, not just documented); append-only; exact duplicate-replay semantics; conflict never overwrites; tenant-scoped read; historical `ALLOWED` evidence does not authorize current work; no chain-of-thought dependency | PASS | `src/legoai/evidence/ports.py` — `EvidenceRecord`/`EvidenceConflictError`; dedicated architecture test proves `legoai.reference.evidence` cannot import `legoai.observability` at all; `InMemoryEvidenceCustody.record` is idempotent-on-exact-match, raises `EvidenceConflictError` on divergent resubmission (`src/legoai/reference/evidence.py`); `read()` is tenant-scoped, returns `None` on cross-tenant/unknown; mandatory cross-M4/M8 test `test_historical_authorization_evidence_survives_grant_revocation_but_does_not_reauthorize` (`tests/unit/reference/test_evidence.py`) — see also G2-EXIT-55 |
| G2-EXIT-14 | Does Gate-2 exit require Evidence for Execution result / dispatch decision / capability resolution / Plugin lifecycle / Catalog publication / resource state, for the first slice? | **NO, independently re-derived from ADR-009 directly, not assumed** | ADR-009 §5: "Mandatory evidence derives from **accepted contracts and applicable entitled Policy/control requirements**... No new universal category or official profile is imposed." CONTRACTS CTR-059 confirms evidence obligations are conditional on an actual "Policy-required" pre-dispatch requirement — not a categorical rule that every dispatch/resolution/lifecycle fact must be evidenced. No accepted `EvidenceRequirement` was ever established anywhere in this codebase's plan for any of the six listed subjects. M8's own subject union (`ConfigurationRevisionRef`, `AuthorizationDecision`) already covers the two subjects that *do* have an established requirement (F4's configuration evidence, and this task's own mandatory historical-authorization test scenario). None of the other four subjects has a genuine consumer; adding them speculatively would itself violate ADR-009 §5's "no new universal category" instruction. |
| G2-EXIT-15 | M11's own invocation-result Evidence deferral — same question, re-confirmed independently for this specific subject | **NO** | Same ADR-009 §5/CTR-059 citation applies identically to the Execution-result subject specifically: no `EvidenceRequirement` naming an execution outcome exists anywhere in accepted planning. `required_evidence_ids` (M9's own pre-effect evidence mechanism, unchanged since M9, exercised by `test_missing_required_evidence_fails_closed_unavailable`/`test_present_required_evidence_permits`) remains the live, working mechanism for *whichever* future requirement does get established — nothing was removed or weakened, only left correctly unpopulated for this fixture. |

### 5.9 M9 — Dispatch arbitration / TOCTOU

| ID | Criterion | Result | Evidence |
|---|---|---|---|
| G2-EXIT-16 | Revalidates current authorization/Approval-use/Catalog publication/evidence *inside* the gate, never trusting preparation-time facts | PASS | `reference/execution.py::DeterministicDispatchArbiter.arbitrate` — every check (`self._authorization.evaluate`, `self._catalog.snapshot`, `self._evidence.read`, `self._approval_consumption.current_use_state`/`consume`) happens inside the single `with self._lock:` block, none reused from an earlier call |
| G2-EXIT-17 | TOCTOU closure: prepare-under-active-Grant-then-revoke-before-gate → not permitted; `max_uses=1` + two concurrent requests → at most one permit; no sleep-based tests | PASS | `test_grant_revoked_before_gate_denies_even_though_prepared_when_active` and `test_concurrent_last_use_race_at_most_one_permitted` (`tests/unit/reference/test_execution.py`) — the latter uses `threading.Barrier`, zero `time.sleep`/`asyncio.sleep(n>0)` calls in either test, confirmed by direct read |
| G2-EXIT-18 | `ApprovalUsePort ≠ ApprovalConsumptionPort`; consumption happens inside the same gate that protects the eligibility decision; no second race window | PASS | `governance/ports.py` defines both Protocols separately; `arbitrate()` calls `self._approval_consumption.consume(approval)` in the same `with self._lock:` block as the eligibility check — no second lock acquisition, no window between check and consume |
| G2-EXIT-19 | Catalog staleness race: resolve at snapshot N, withdraw selected entry, gate later → `STALE`, zero invocation | PASS | `test_withdrawn_entry_is_stale_not_silently_permitted` (M9) and `test_stale_catalog_never_invokes` (M11 integration, `tests/integration/composition/test_governed_direct.py`) both assert `calls == []`/`invocation count == 0` |
| G2-EXIT-20 | Resource-claim gating inside the dispatch gate — required or legitimately deferred? | **Deferred, legitimately, not converted from "not implemented" to "not needed" without evidence** | Re-derived independently (not merely restated from the plan): CONTRACTS CTR-062 row 9's "explicit policy-permitted empty applicability if none" (same citation as G2-EXIT-04b) applies at the dispatch-gate level too — `DispatchRequest` (`execution/ports.py`) carries no resource field because no resource-bearing capability exists in this reference tree to require one. This is a **structural absence matching a declared-empty requirement**, not a silent capability gap being relabeled — the distinction the task explicitly warned against collapsing. See §16 for the exact future trigger. |
| G2-EXIT-21 | Mandatory `EvidenceRequirement` ordering before permit issuance, if one exists for this slice | **NOT_APPLICABLE (none exists)** | Same finding as G2-EXIT-14/15. The *mechanism* (`required_evidence_ids` checked before permit issuance) is present and tested; there is simply nothing populated into it for this fixture, correctly. |
| G2-EXIT-22 | No unsupported "exactly once"/"guaranteed single global invocation" claims anywhere | PASS | Grepped `src/` and `tests/` and `planning/*.md` for "exactly once", "exactly-once", "guaranteed single" — every occurrence found is an explicit **disclaimer** ("No exactly-once claim", "makes no operation-ledger/dedup guarantee"), never an affirmative claim. `DispatchDecision`/`DispatchPermit`/`ExecutionResult` all carry identity fields "for attribution only, not as proof no equivalent dispatch has occurred or will occur" (verbatim from `execution/ports.py`'s own docstring) |

### 5.10 M10 — Coordinator / supervision

| ID | Criterion | Result | Evidence |
|---|---|---|---|
| G2-EXIT-23 | Structured concurrency; `TaskGroup` ownership; no detached tasks; cancellation propagation; deadline enforcement; child-failure observation; no task leaks | PASS | `reference/execution.py::ExecutionCoordinator._run_prepared` owns exactly one child task per call inside its own `asyncio.TaskGroup`; `except* Exception` maps child failure to `_PreparationFailed`, never silently dropped; `asyncio.timeout(delay)` wraps the TaskGroup for deadline enforcement; leak-freedom proven by `asyncio.all_tasks()` diffing in `test_ready_when_permitted`, `test_rejected_when_deadline_expires_during_supervised_wait`, `test_cancellation_before_running_marks_cancelled_and_propagates`, and the integration-level `test_no_task_leaks_across_success_failure_and_cancellation` |
| G2-EXIT-24 | Lifecycle transition graph exactly matches SPEC §5.1 | PASS | `reference/execution.py::_allowed_next_states` quotes SPEC §5.1 verbatim in its own docstring and encodes exactly its 20 edges; independently re-derived this session by re-reading SPEC §5.1's literal transition text and cross-checking every edge in the table by hand — no discrepancy found |
| G2-EXIT-25 | `ADMITTED → RUNNING` on permit; pre-permit faults (deny/stale/deadline/dependency-failure) → `REJECTED`; `RUNNING → SUCCEEDED/FAILED/CANCELLING`; `CANCELLING → CANCELLED` | PASS | `coordinate()` transitions `admitted → running` only on `DispatchOutcome.PERMITTED`; all of DENIED/UNAVAILABLE/STALE/deadline-exceeded/internal-preparation-fault map to `admitted → rejected` (`coordinate()` body, all four `self._transition(execution_id, ExecutionState.REJECTED)` call sites); `invoke_governed`/`settle` (M11) use `running → succeeded`/`running → failed` directly and `running → cancelling → cancelled` for the two-step case (`test_settle_cancelled_takes_two_step_cancelling_path` spies on `_transition` call order and asserts `[CANCELLING, CANCELLED]`) |
| G2-EXIT-26 | Deadline-before-running belongs in `REJECTED`, verified against source authority, not merely the implementation's own interpretation | PASS | SPEC §5.1: "admitted MAY be cancelled or **fail admission revalidation into rejected**" — deadline expiry during the admitted phase (before any driver/effect has begun) is exactly an admission-revalidation failure under this literal text, independently re-confirmed this session, not merely re-asserted from the M10 report |
| G2-EXIT-27 | Deadline: semantic wall-clock absolute vs. monotonic loop-time scheduling, both already-expired and mid-wait cases | PASS | `coordinate()` computes `delay = (deadline - now).total_seconds()` (wall-clock subtraction via the injectable `clock` seam) and hands only the **relative** `delay` to `asyncio.timeout(delay)`, which owns monotonic scheduling internally — the two clock domains are never conflated; `test_rejected_when_deadline_already_expired_without_arbitrating` (eager check, resolver never called) and `test_rejected_when_deadline_expires_during_supervised_wait` (real timeout mid-wait, `asyncio.all_tasks()` diff proves cleanup) both pass |
| G2-EXIT-28 | External `CancelledError` never swallowed; `RUNNING → CANCELLING → CANCELLED` where invocation supervision is involved | PASS | `coordinate()`'s `except asyncio.CancelledError:` records `CANCELLED` then `raise`s unmodified (never returns a value); `invoke_governed`'s equivalent handler does the same via `settle(..., final_state=CANCELLED, ...)` which internally inserts the `CANCELLING` step; `test_cancellation_before_running_marks_cancelled_and_propagates` and `test_invoke_governed_cancellation_before_closure_marks_cancelled` both assert `pytest.raises(asyncio.CancelledError)` around the await, i.e. it truly propagates |

### 5.11 M11 — Governed invocation

| ID | Criterion | Result | Evidence |
|---|---|---|---|
| G2-EXIT-29 | Cancellation limitation (CPython cannot preempt the synchronous closure once started) — acceptable for this slice, not generalized | PASS (explicitly scoped) | `reference/execution.py` module docstring states this limitation in its own dedicated paragraph and explicitly frames it as a property of *this pure/synchronous fixture only*; the planning doc (§38) repeats the same scoping. No claim anywhere generalizes this to future blocking/network providers — §18 restates this as explicitly non-qualified scope. |
| G2-EXIT-30 | First invocation impossible unless the exact Coordinator instance previously reached `RUNNING` via the governed path (`_require_running`) | PASS | `ExecutionCoordinator._require_running` reads `self._states.get(execution_id)` and raises `ExecutionTransitionError` unless it is exactly `RUNNING`, called *before* the capability closure in both `settle` and `invoke_governed`; three dedicated tests prove zero invocations for (a) a hand-built `CoordinationResult` never coordinated at all, (b) a genuine `READY` result produced by a **different** `ExecutionCoordinator` instance used against a fresh one, and (c) a second call against an already-`SUCCEEDED` result — `test_invoke_governed_rejects_hand_built_result_not_produced_by_this_coordinator`, `test_invoke_governed_second_call_on_already_settled_result_fails_structurally` (`tests/unit/reference/test_coordinator.py`) |
| G2-EXIT-31 | `legoai.runtime._composition.governed` is the correct ADR-002 composition root for Application configuration + deterministic capability + Catalog identity + Execution coordinator; no lower package imports a higher owner | PASS | ADR-002 §9.2's E-row foreign-target maximum (K, C, T, I, M, Artifacts, G, R, O, X, V) excludes Application; separately, §9's "no reference owner implementation imports another reference owner implementation" independently forbids `legoai.reference.execution` importing `legoai.reference.deterministic`. `legoai.runtime._composition` is the one location ADR-002 explicitly authorizes to import "as needed" across owner values and "selected concrete realizations" for wiring (ADR-002 body text, re-quoted and cross-checked this session, not merely re-asserted). Dedicated architecture test `test_production_boundaries` (whole-tree scan) passes; the widened `composition-owner` allowlist in `tests/architecture/test_import_boundaries.py` names exactly `legoai.capabilities.ports`, `legoai.execution.ports`/`.values`, `legoai.reference.execution` as the new M11 grants, nothing broader |
| G2-EXIT-32 | No inert value (`PluginDeclaration`, `CatalogEntry`, `CapabilityResolution`, `DispatchPermit`, `CoordinationResult`) contains a callable/provider/runtime handle | PASS | Direct field-by-field re-read this session of all five dataclasses in `plugins/values.py`, `capabilities/ports.py`, `reference/resolution.py`, `execution/ports.py` (×2) — no field typed `Callable`, `object`, or `Any` exists in any of them; `FORBIDDEN_RUNTIME_FIELDS` check in `tests/unit/execution/test_ports.py` asserts this structurally for the M9/M10/M11 types (`callable, handler, adapter, provider, factory, connection, instance` all absent) |
| G2-EXIT-33 | No dynamic loading (`eval`/`exec`/`compile`/`importlib`/entry-point/filesystem-driven discovery) determines executable code from Catalog/Plugin text | PASS | `grep -rn "eval(\|exec(\|compile(\|importlib\|__import__" src/legoai` returns exactly two matches, both inside docstring prose explaining what is deliberately *not* done (`reference/execution.py:80`, `runtime/_composition/governed.py:35`) — no actual call site exists; dedicated AST-based architecture test `test_composition_root_does_not_hide_coordinator_behind_generic_lookup` independently checks actual `ClassDef`/`Name`/`Attribute`/`Import` nodes (not substring matching) in `runtime/_composition/governed.py` and finds none |
| G2-EXIT-34 | Trusted-host qualification explicit; ADR-012 remains Proposed/unresolved, not silently treated as solved | PASS | `runtime/_composition/governed.py` module docstring: "Trusted-host scope only... ADR-012 (Plugin isolation/sandboxing) remains completely unresolved and is not claimed here in any way"; `adrs/ADR-012.md` status confirmed unchanged (not read/modified this session; no source file claims otherwise) |
| G2-EXIT-35 | Exact implementation correspondence — `PluginId` + release + full `CapabilityOffer` (id+version), never fuzzy | PASS | `governed.py::_known_text_normalization_entry_matches` compares all three fields by exact equality (`==`), no substring/prefix/partial match; `test_hostile_plugin_identifier_remains_inert` proves a maliciously-named `PluginId`/`CapabilityId` (containing `../../etc`, `os.system(...)`, `__import__('os').system`) is still treated purely as an equality-comparison mismatch, zero invocations |
| G2-EXIT-36 | Implementation mismatch → 0 invocations, `FAILED`/appropriate category, correct `EffectExtent` | PASS | `test_implementation_mismatch_never_invokes_and_fails` — `calls == []`, `final_state is FAILED`, `effect is EffectExtent.NONE`, `error.category is ErrorCategory.DEPENDENCY_FAILURE` |
| G2-EXIT-37 | Successful invocation → `RUNNING → SUCCEEDED`, `EffectExtent.COMPLETED`, correct deterministic output | PASS | `test_full_governed_slice_succeeds` — real declared→ACTIVE→published→resolved→authorized→dispatched→coordinated→invoked path, `outcome.output == "hello world"` for input `"  hello   world  "` |
| G2-EXIT-38 | Capability failure → `FAILED`/`EffectExtent.NONE`, never `UNKNOWN` merely because an exception occurred | PASS | `test_capability_failure_invokes_once_and_fails` — exactly 1 invocation, `final_state is FAILED`, `effect is EffectExtent.NONE`, `error.category is ErrorCategory.EXECUTION_FAILURE` |
| G2-EXIT-39 | Broader `EffectExtent.UNKNOWN` representational capability not broken; `UNKNOWN` never aliases `NONE` | PASS | `kernel/effects.py::EffectExtent` unchanged since Gate-1 (`NONE, PARTIAL, COMPLETED, UNKNOWN`, 4 distinct members); `assert len(effects.EffectExtent) == 4` still holds in the wheel smoke script; nothing in M9-M11 collapses `UNKNOWN` into `NONE` anywhere (confirmed by grep — every `EffectExtent.NONE` assignment in `reference/execution.py`/`governed.py` is for a genuinely no-effect case, pre-permit or pre-invocation) |
| G2-EXIT-40 | Pure fixture never incorrectly produces `PARTIAL` | PASS | `grep -n "EffectExtent.PARTIAL" src/legoai/reference/execution.py src/legoai/runtime/_composition/governed.py` — zero matches; `PARTIAL` is not reachable from any code path in the M9-M11 governed slice |
| G2-EXIT-41 | Invocation-count proofs across all required scenarios | PASS | `tests/integration/composition/test_governed_direct.py` — success → exactly 1 (`test_full_governed_slice_succeeds`, `test_capability_failure_invokes_once_and_fails`); denied/stale/exhausted/unresolvable/deadline/mismatch/hostile-identifier → 0 each (`test_authorization_denied_never_invokes`, `test_stale_catalog_never_invokes`, `test_approval_exhausted_never_invokes`, `test_unresolvable_security_context_never_invokes`, `test_deadline_already_expired_never_invokes`, `test_cancellation_before_ready_never_invokes`, `test_implementation_mismatch_never_invokes_and_fails`, `test_hostile_plugin_identifier_remains_inert`) — 8 zero-invocation scenarios plus 2 exactly-one-invocation scenarios, all passing |

### 5.12 Cross-cutting

| ID | Criterion | Result | Evidence |
|---|---|---|---|
| G2-EXIT-42 | Permit replay / exactly-once — mandatory or legitimately deferred? | **Deferred, legitimately, with a precisely bounded and disclosed residual risk — this is the single most important disposition in this review; see §16** | Full reasoning in §16.1 |
| G2-EXIT-43 | Concurrent double-invocation of the same `RUNNING` result — does it currently exist, and is it disclosed? | **YES it exists; fully disclosed, not hidden as "safe because pure"** | `reference/execution.py` module docstring's own dedicated paragraph states plainly: "nothing today prevents two *concurrent* `invoke_governed` calls for the same still-`RUNNING` `execution_id` from both passing that check before either commits its terminal transition, both then calling the capability closure." This is stated as a fact, then separately argued to be *inert for this specific fixture* (pure, no external effect) — the argument and the fact are kept visibly distinct, per this task's explicit instruction not to conflate them. |
| G2-EXIT-44 | ADR-008 identity distinctness: `OperationId ≠ ExecutionId ≠ retry attempt`; must M11 persist/dedup against `OperationId`? | PASS / **NO, not required for current exit** | `execution/values.py` module docstring: "`ExecutionId` is a distinct identity from the logical `OperationId`/`OperationRef`... one logical operation may have several linked Execution attempts". ADR-008's own downstream-impact table (re-read this session) lists "broader equivalence/effect identity and deduplication machinery" as explicitly **undecided/future** for every consumer, not specifically demanded of M1-M11's scope; no Gate-2 planning batch was ever scheduled to build an ADR-008 operation ledger — its absence here is consistent with the entire accepted implementation plan, not a gap introduced at M11 |
| G2-EXIT-45 | Configuration-revision revalidation at invocation — mandatory or deferred? | **Deferred, legitimately — no accepted M1-M10 governed-path type carries a pinned `ConfigurationRef` to revalidate against** | Re-derived directly from ADR-003/007/008 this session (not merely restated): none of `ExecutionContext` (M1), `CatalogEntry` (M6), or `DispatchPermit` (M9) was ever given a `ConfigurationRef` field across any Gate-2 milestone — this is an inherited scope boundary from M1's own original design, not something M11 introduced. CTR-028 requires "current governance" at invocation (authority), not a categorical configuration-revision check independent of any established requirement. Inventing this now would require modifying an already-accepted M1 value without new authority to do so — correctly refused rather than done speculatively. |
| G2-EXIT-46 | Configuration consistency: one explicit `EffectiveConfiguration`, immutable, never silently substituted mid-invocation | PASS | `EffectiveConfiguration` (`application/values.py`) is a frozen dataclass; `governed.py::invoke_governed_text_normalization` receives exactly one `effective` parameter and passes it unchanged into the closure — no second composition/fetch call exists anywhere in the invocation path |
| G2-EXIT-47 | Durable Execution-result persistence — required for this exit, or is transient proof sufficient? | **Transient sufficient; not inferred from Gate-1 Configuration persistence** | No accepted ADR mandates a persisted Execution-result store for the first governed slice; ADR-004's owner-local persistence pattern is *available* infrastructure, not a mandate applied here without a canonical trigger. `planning/GATE-2-IMPLEMENTATION-PLAN.md` never scheduled an "Execution repository" batch. This review does not treat Gate-1's Configuration store as precedent requiring the same for Execution absent explicit authority. |
| G2-EXIT-48 | Crash/restart recovery of in-flight Execution | **Not required; not claimed** | No source file or docstring in M9-M11 claims restart-survival; `reference/execution.py`'s own docstrings explicitly disclaim "restart-surviving operation ledger" (M9) and describe the internal runtime record as "a bounded technical index, not authoritative state" (M10, quoting ADR-015 §5 verbatim) |
| G2-EXIT-49 | No retry engine exists; not required for this slice | PASS | `grep -rn "retry" src/legoai/reference/execution.py src/legoai/runtime/_composition/governed.py` — only docstring disclaimers ("No retry engine"), no retry loop/backoff code exists |
| G2-EXIT-50 | No compensation engine exists; not required for the pure deterministic slice | PASS | Same grep pattern for "compensation" — disclaimer-only; the fixture has no external effect to compensate |
| G2-EXIT-51 | `asyncio` confined to authorized reference/execution runtime modules only | PASS | Dedicated whole-tree AST scan `test_asyncio_confined_to_authorized_reference_execution_module` (`tests/architecture/test_import_boundaries.py`) — passes; direct `grep -rln "^import asyncio\|^from asyncio" src/legoai/` this session returns exactly one file: `src/legoai/reference/execution.py` |
| G2-EXIT-52 | `threading` exception remains narrowly scoped to `legoai.reference.execution` only, not broadened | PASS | `test_no_ambient_context_or_module_state`'s `threading_import_allowed = {"legoai.reference.execution"}` set, re-read this session — unchanged since M9, not widened by M10/M11 (M10/M11 use `asyncio.Lock`, never `threading.Lock`) |
| G2-EXIT-53 | No ambient state (global Principal/tenant/security context/Catalog/provider registry/service locator/ambient execution) | PASS | `grep -rn "^_CURRENT\|global \|_ambient\|ContextVar" src/legoai` — no matches for any global mutable security/tenant/catalog state; `test_no_ambient_context_or_module_state` also bans any module-level `ast.Assign`/`ast.AnnAssign` across the entire `src/legoai` tree, re-run and passing this session |
| G2-EXIT-54 | No unjustified generic framework creep (`Manager`, `ServiceLocator`, `RuntimeBuilder`, `GenericRepository`, `GlobalRegistry`, `ProviderRegistry`, `DIContainer`) | PASS | `grep -rn "Manager\|ServiceLocator\|RuntimeBuilder\|GenericRepository\|GlobalRegistry\|ProviderRegistry\|DIContainer" src/legoai` — zero matches; dedicated architecture test `test_composition_root_does_not_hide_coordinator_behind_generic_lookup` additionally proves this by AST inspection of the one module (`governed.py`) that could plausibly have hidden one |
| G2-EXIT-55 | `SecurityContextResolutionPort` used explicitly, no ambient bypass; unknown reference fails safe | PASS | `ExecutionCoordinator._resolve_and_arbitrate` calls `self._resolver.resolve(...)` (injected Port, no global lookup); `resolve()` returning `None` maps to `REJECTED`/`DependencyFailure`, never a fabricated `SecurityContext` — `test_unresolvable_security_context_never_invokes` |
| G2-EXIT-56 | Historical `ALLOWED` evidence exists → Grant later revoked → fresh current evaluation `DENIED` → dispatch/invocation blocked (critical cross-batch proof) | PASS | `test_historical_authorization_evidence_survives_grant_revocation_but_does_not_reauthorize` (`tests/unit/reference/test_evidence.py`, M8) proves the evidence-vs-authority half directly; `test_grant_revoked_before_gate_denies_even_though_prepared_when_active` (M9) proves the dispatch-blocking half using the same revocation mechanism — together they cover the full chain this criterion names |
| G2-EXIT-57 | Catalog entry present alone cannot lead to invocation | PASS | `test_authorization_denied_never_invokes`/`test_approval_exhausted_never_invokes` (M11 integration) use a **published, ACTIVE, resolvable** entry throughout and still reach 0 invocations purely from an authorization failure — proving Catalog presence is necessary but insufficient |
| G2-EXIT-58 | `CapabilityResolution.RESOLVED` alone cannot lead to invocation | PASS | `_Environment.resolve_entry()` in the M11 integration test always returns a genuinely `RESOLVED` candidate before every denied/stale/exhausted/unresolvable/deadline scenario — resolution success never bypasses the later gates |
| G2-EXIT-59 | `PluginLifecycleState.ACTIVE` alone cannot lead to invocation | PASS | Same environment always promotes the Plugin to `ACTIVE` before every zero-invocation scenario; ACTIVE state is a precondition, not a sufficient condition, in every test |
| G2-EXIT-60 | Historical Evidence alone cannot lead to invocation | PASS | No test or code path treats a pre-existing `EvidenceRecord` as invocation-sufficient; M9's own evidence check only ever *confirms presence*, never substitutes for the authorization/Catalog/Approval checks that run independently in the same gate |
| G2-EXIT-61 | Approval consumption persists at least for the reference in-memory lifetime, checked under lock; no overclaim of process durability | PASS | `InMemoryApprovalUseFake.consume`/`InMemoryCatalog` are plain in-process dicts (`tests/support/governance.py`, `reference/catalog.py`) — no persistence claim exists anywhere in their docstrings; `consume()` only ever runs inside `DeterministicDispatchArbiter`'s `threading.Lock` |
| G2-EXIT-62 | Exact gate-atomicity claim: single-process reference-arbiter atomicity only, never distributed/multi-process/global-transaction | PASS | `reference/execution.py::DeterministicDispatchArbiter` docstring: "a **reference lock scoped to one arbiter instance and one process only** — it makes no multi-process or distributed exclusivity claim; ADR-007 §13's own initial scope is 'one trusted local arbitration process'" — direct quote, re-verified this session, matches ADR-007 §13 exactly |
| G2-EXIT-63 | M9 releases its gate before actual capability invocation; M11 does not hold the M9 lock across the function call | PASS | `arbitrate()`'s `with self._lock:` block ends (and the lock is released) when `arbitrate()` returns a `DispatchDecision` to `coordinate()`; `invoke_governed`/`settle` never touch `DeterministicDispatchArbiter._lock` at all — they only touch `ExecutionCoordinator`'s own separate `asyncio.Lock`, confirmed by reading both classes' full method bodies this session |
| G2-EXIT-64 | No post-effect authorization; current authority checked before crossing the effect boundary, never after | PASS | Authorization (`self._authorization.evaluate`) is the **first** check inside `arbitrate()`'s gate, strictly before the Catalog/evidence/approval checks and strictly before any permit is issued; `invoke_governed` performs no authorization call of any kind — by the time it runs, authorization has already been checked and the gate already released |
| G2-EXIT-65 | Observation failure cannot authorize, deny, or alter Evidence custody / current-state result | PASS | `runtime/_composition/direct.py::_emit_best_effort` (F8b, unchanged) is the only Observation-emission code touched by anything Gate-2-adjacent, and it explicitly catches and discards sink exceptions without affecting `CompositionResult`; M9-M11 add **no** Observation emission at all (§3 above), so there is no new code path where this could regress |
| G2-EXIT-66 | No chain-of-thought/hidden-reasoning dependency anywhere in Gate-2 code/tests/docs | PASS | `grep -rniE "chain_of_thought|chain-of-thought|hidden_reasoning|private_reasoning|scratchpad"` across `src/legoai`/`tests`/planning docs finds matches only in `evidence/ports.py`'s own docstring disclaimer ("no private chain-of-thought... required") and `tests/unit/evidence/test_ports.py`'s `FORBIDDEN_FIELDS = {"chain_of_thought", "hidden_reasoning", "private_reasoning", "scratchpad"}` structural-absence check (M8) — every match is a disclaimer or a test proving absence, never a dependency |
| G2-EXIT-67 | Zero third-party runtime dependencies | PASS | §4 above — `dependencies = []` in `pyproject.toml`; wheel `METADATA` asserted to contain no `Requires-Dist:` line in the smoke script |
| G2-EXIT-68 | Fresh wheel build/install runs the full governed slice with no source-tree leakage | PASS | §4 above — `test_build_and_fresh_wheel`; installed via `uv pip install --no-deps --offline`, executed with `python -I -B` (isolated, no site customization, no bytecode-writing) against a separate temp venv, all module `__file__`s asserted `is_relative_to(sys.prefix)` |
| G2-EXIT-69 | Import inertness: importing Gate-2 modules performs no capability invocation, task/thread start, authorization, Approval consumption, Catalog publication, Evidence recording, DB open, environment read, network, or logging configuration | PASS | `tests/integration/composition/test_import_inertness.py` — imports every Gate-2 module (including the new `legoai.runtime._composition.governed`) under an `sys.addaudithook` that raises on `socket.*`/`subprocess.*`/`sqlite3.*`/`os.mkdir`/`os.remove`/`os.rename`/`os.system`, plus a patched `logging.basicConfig` that raises on any call — passes with zero violations |
| G2-EXIT-70 | Full Core test suite | PASS | 1315 passed, 0 failed (§4) |
| G2-EXIT-71 | Document Pack regression isolated from Gate-2 qualification | PASS | 268 passed / 64 skipped, run as a **separate** suite in `packages/legoai-document`; no Document Pack test imports any Gate-2 module, confirmed by the package's own isolated `pyproject.toml`/dependency set |
| G2-EXIT-72 | Coverage: overall + critical-module breakdown; no uncovered branch involving authorization/Approval-consumption/Catalog-staleness/Coordinator-cancellation/implementation-correspondence/invocation-failure | PASS | §16.1 below — 97% overall; **100%** branch coverage on every Gate-2-specific module (`execution/{ports,values}.py`, `governance/{ports,values}.py`, `capabilities/{ports,values}.py`, `plugins/{ports,values}.py`, `evidence/{ports,values}.py`, `reference/{execution,governance,catalog,plugins,evidence,deterministic}.py`, `runtime/_composition/governed.py`). The <100% modules are exclusively Gate-1-era `application`/`reference.application` files (codec/recovery/sqlite_store edge branches), pre-existing and unrelated to any of the six named invariant categories. |
| G2-EXIT-73 | mypy strict | PASS | §4 |
| G2-EXIT-74 | ruff check + format | PASS | §4 |
| G2-EXIT-75 | Architecture tests: ADR-002 ownership, async confinement, threading confinement, no reverse-reference dependencies, no dynamic Plugin loading, no provider registry | PASS | 229 passed (§4); see G2-EXIT-31/33/51/52/54 for the specific boundary tests |
| G2-EXIT-76 | Canonical docs/ADRs unmodified; DocuMind untouched | PASS | `git diff origin/br-documind-merging --stat` against `intent.md, SPEC.md, architecture/, contracts/, plugin-spec/, security/, evaluation/, conformance/, adrs/` is **empty**; no `DocuMind`/`documind` directory exists in this repository at all (confirmed by direct filesystem check) |

## 6. Current-authority review (summary)

Covered in full above (G2-EXIT-05, 05b-e, 06, 56). No additional findings.

## 7. Plugin/Catalog/Resolution review (summary)

Covered in full above (G2-EXIT-07 through G2-EXIT-12, 57-59). No additional findings.

## 8. Evidence review (summary)

Covered in full above (G2-EXIT-13 through G2-EXIT-15, 60). No additional findings.

## 9. Dispatch/TOCTOU review (summary)

Covered in full above (G2-EXIT-16 through G2-EXIT-22, 61-64). No additional findings.

## 10. Coordinator/supervision review (summary)

Covered in full above (G2-EXIT-23 through G2-EXIT-28). No additional findings.

## 11. Governed-invocation review (summary)

Covered in full above (G2-EXIT-29 through G2-EXIT-41). No additional findings.

## 12. Security review

Concrete tests proving each required security property:

| Property | Test(s) |
|---|---|
| Fail closed on unknown state | `test_unknown_revocation_state_fails_closed_unavailable` |
| Tenant isolation | `test_dispatch_request_tenant_mismatch_rejected`, `test_coordination_request_tenant_mismatch_rejected` (construction-time rejection) |
| Revocation | `test_grant_revoked_before_gate_denies_even_though_prepared_when_active`, `test_rejected_when_grant_revoked_before_coordination` |
| Approval exhaustion | `test_approval_exhausted_denies`, `test_approval_exhausted_never_invokes` |
| Stale Catalog | `test_withdrawn_entry_is_stale_not_silently_permitted`, `test_stale_catalog_never_invokes` |
| Missing SecurityContext | `test_rejected_when_security_context_unresolvable`, `test_unresolvable_security_context_never_invokes` |
| No executable inert binding | `FORBIDDEN_RUNTIME_FIELDS` structural checks (`tests/unit/execution/test_ports.py`) |
| No dynamic loading | `test_composition_root_does_not_hide_coordinator_behind_generic_lookup`, `test_hostile_plugin_identifier_remains_inert` |

## 13. Concurrency/race evidence

| Test | Mechanism | Repeated-run result (this session) |
|---|---|---|
| `test_concurrent_last_use_race_at_most_one_permitted` | `threading.Barrier(2)` | 5/5 pass |
| `test_concurrent_requests_no_double_consumption_across_many_threads` | `threading.Barrier(10)` | 5/5 pass |
| `test_concurrent_grant_revocation_race_never_permits_after_revoke_wins` | `threading.Event`-instrumented interleaving | 5/5 pass |
| `test_two_coordinations_race_for_last_approval_use` | `asyncio.sleep(0)`-forced deterministic interleaving (no sleep-based timing) | 5/5 pass |
| `test_no_task_leaks_across_success_failure_and_cancellation` | `asyncio.all_tasks()` diffing | 5/5 pass |

No sleep-based race orchestration exists in any of these tests (verified by direct read).

## 14. ADR consistency

No contradiction between accepted ADR text and current source was found. Every deviation/deferral is explicitly authorized by a specific ADR citation re-verified this session (not merely trusted from a prior report): ADR-006 §9 (Catalog staleness, DEGRADED), ADR-007 §13 (single-process gate scope), ADR-008 downstream table (dedup/equivalence machinery undecided), ADR-009 §5 + CTR-059 (evidence conditional on established requirement), ADR-015 §§2, 5-7 (supervision scope, internal registry non-authoritative).

## 15. Architecture/dependency review

229 architecture tests passed. Key boundaries independently re-verified this session (not merely re-run): ADR-002 E-row/composition-owner allowlists (G2-EXIT-31), `asyncio` confinement (G2-EXIT-51), `threading` confinement (G2-EXIT-52), reverse-dependency checks — `legoai.execution.values` and every M2-M9 semantic-values module proven not to import `legoai.reference.execution` — no dynamic Plugin loading (G2-EXIT-33), no provider registry (G2-EXIT-54).

## 16. Deferred-items disposition

### 16.1 Deferred items table

| Deferred item | Required for current exit? | Evidence | Decision |
|---|---|---|---|
| `DispatchPermit` replay protection | **NO** | ADR-008's dedup/equivalence machinery is explicitly undecided project-wide (not just here); no Gate-2 batch was ever scheduled to build it; residual risk is a concurrent double-invocation of a **pure, no-external-effect** capability only — bounded to "duplicate identical computation, discarded," never a duplicated external effect | **Deferred, blocker trigger: the first time a Gate-2-governed capability has any external/non-idempotent effect, replay protection becomes mandatory before that capability may use this invocation boundary** |
| Resource runtime gating | **NO** | CONTRACTS CTR-062 row 9 explicitly permits "policy-permitted empty applicability if none"; `normalize_text` declares no resource dimension at all | **Deferred, blocker trigger: the first resource-bearing capability introduced to the Catalog** |
| Invocation-result Evidence custody | **NO** | ADR-009 §5 + CTR-059: evidence obligations are conditional on an established Policy/control requirement; none exists for this outcome anywhere in accepted planning | **Deferred, blocker trigger: the first accepted `EvidenceRequirement` naming an Execution-result subject** |
| Configuration revision revalidation | **NO** | No M1-M10 governed-path type (`ExecutionContext`, `CatalogEntry`, `DispatchPermit`) was ever given a pinned `ConfigurationRef`; inventing one now would require unauthorized modification of an already-accepted M1 value | **Deferred, blocker trigger: a future batch that explicitly adds a pinned configuration reference to the governed path (a design decision, not a bug fix)** |
| DEGRADED Catalog publication | **NO** | ADR-006 §9 makes DEGRADED an *available*, not mandatory, eligibility path; the one governed fixture has no health/degradation concept to exercise it | **Deferred, blocker trigger: the first Plugin/Provider with a genuine degraded-operation mode** |
| Execution persistence/restart recovery | **NO** | No accepted ADR mandates it for the first slice; explicitly disclaimed, never falsely claimed, in M9/M10 docstrings | **Deferred, blocker trigger: a future ADR-004-style Execution-repository batch, not yet scheduled** |
| Untrusted Plugin isolation | **NO for the trusted slice** | ADR-012 status is Proposed; Gate-2 planning never made it a Gate-2 dependency | **Deferred to ADR-012's own future acceptance/realization** |
| Production observability | **NO** | ADR-013 status is Proposed; F8a's bounded, non-authoritative Observation mechanism is unchanged and sufficient for this scope | **Deferred to ADR-013's own future acceptance/realization** |

### 16.2 Why none of these block this specific exit

Every deferred item above shares the same structural justification, independently re-verified against its cited ADR/contract rather than restated from a completion report: the accepted Gate-2 exit target is **one** governed deterministic invocation, and each deferred capability (replay protection, resource gating, evidence custody, configuration pinning, degraded eligibility, persistence, isolation, observability) is conditional on a triggering fact (an effectful capability, a resource-bearing capability, an established evidence requirement, a pinned configuration reference, a degraded-capable Plugin, a scheduled persistence batch, an accepted ADR-012/013) that **does not yet exist anywhere in this codebase**. None of the eight items was "not implemented" quietly relabeled as "not needed" — each has an explicit, independently-derived textual citation showing the requirement itself is conditional, and each carries a named future trigger that will make it mandatory.

## 17. Qualified scope

Gate 2 qualifies **exactly** the following, and nothing broader:

```text
One deterministic, synchronous, statically known, trusted-host capability
implementation (F8b's normalize_text), invocable only via the complete
governed path:

  explicit tenant (TenantContext, verified at every construction boundary)
  + current authorization (re-evaluated inside the exclusive dispatch gate,
    never a cached/historical decision)
  + bounded Approval use (checked and consumed inside the same gate,
    zero-window between check and consume)
  + a published Catalog candidate (ACTIVE-only, tenant-scoped, revalidated
    for continued presence at dispatch time)
  + runtime capability resolution (RESOLVED/NO_MATCH/AMBIGUOUS, unranked,
    catalog_revision-attributed)
  + dispatch arbitration (single-process exclusive gate, ADR-007 ordering)
  + structured supervision (one owned asyncio.TaskGroup child per call,
    proven leak-free, cancellation-propagating, deadline-enforcing)
  + actual invocation (structurally impossible without the exact
    Coordinator instance having reached RUNNING through this path)
  + terminal execution semantics (SUCCEEDED/FAILED/CANCELLED/REJECTED,
    exactly matching SPEC SS5.1's transition graph, correct EffectExtent)
```

## 18. Explicit non-qualified scope

Gate 2 does **not** prove, and no artifact in this codebase claims it proves:

```text
arbitrary third-party Plugins / untrusted Plugin execution
Plugin process isolation or sandboxing (ADR-12 remains Proposed)
network providers or any blocking/non-cooperative provider
resource-limited providers (resource gating is deferred, not proven)
exactly-once / single-use permit enforcement for effectful capabilities
Model calls, Embedding, Agents, Workflows, MCP, A2A
distributed or multi-process dispatch atomicity
crash/restart recovery of in-flight Execution
production-grade observability beyond F8a's bounded local mechanism
durable persistence of Execution results
configuration-revision staleness detection at invocation time
```

## 19. Residual risks

1. **Concurrent double-invocation of a single `RUNNING` result** (G2-EXIT-43) — inert today only because the one governed capability is pure; becomes a real correctness/safety risk the moment any effectful capability reuses this exact boundary without first adding replay protection.
2. **No resource accounting at all** — a future resource-bearing capability introduced without first building `ResourcePort` would silently bypass resource governance entirely; there is no structural guard preventing that mistake today beyond code review discipline.
3. **DEGRADED-eligible Plugins would currently be rejected or mis-handled** — `InMemoryCatalog`/`DispatchArbiter` only recognize `ACTIVE`; a future Plugin genuinely entering `DEGRADED` needs new, currently-unbuilt logic, not merely a state-enum check.
4. **No durable audit trail of governed invocations** — if a governed capability with a real external effect were added without first resolving the Evidence-custody deferral, there would be no historical record of what was invoked, when, or with what outcome, beyond process-lifetime logs.
5. **Trusted-host, single-process assumption is load-bearing everywhere** — every atomicity/exclusivity claim in this codebase (M9's gate, M10's internal record) is explicitly scoped to one process; none of it survives a future multi-process or distributed deployment without a new, separately-qualified mechanism.

## 20. Final Gate-2 determination

```text
GATE_2_EXIT_VERDICT = READY
```

Gate 2's governed executable slice is qualified within the explicitly documented scope stated in §17. The next phase (post-Gate-2 planning, including whether/how to sequence ModelPort, Embedding, DocuMind extraction, Agent runtime, Workflow runtime, MCP, or A2A) must be planned separately, as a distinct task. No such work was started, planned, or scoped in this review.
