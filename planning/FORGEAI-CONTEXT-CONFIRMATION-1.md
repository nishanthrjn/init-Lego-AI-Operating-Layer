# FORGEAI-CONTEXT-CONFIRMATION-1

Status: IMPLEMENTED — MAINTAINER VALIDATION REQUIRED.
Verification: **NOT RUN — Awaiting user execution**.
Baseline: `7aeedc6283a5970a498a4c46ceb63c9bc65af22b`.

## Problem and authority

The qualified repository preflight produced bounded metadata, but its boolean
confirmation did not bind the contents subsequently acquired by CodingAgent.
A changed file could therefore reach coding after confirmation of older bytes.

Authority is the maintainer's FORGEAI-CONTEXT-CONFIRMATION-1 request, shared
AGENTS.md, accepted ADR-002/ADR-014 public ownership boundaries and ADR-024 §8
disclosure separation. Existing public CodingRequest, CodingEvidencePort,
AuthorizedCodingEvidence, ContentDigest, ExecutionContext and repository path
contracts supply the mechanisms. The previous preflight qualification remains
historical evidence; it does not qualify this extension.

## Scope and reuse decisions

Reuse the existing explicit-path authorized acquisition, preflight metadata
projection, exact UTF-8 digests, composition-supplied operator callback, workspace
guard, remote disclosure gate and proposal approval. Extend repository_context,
the worker, bounded task evidence and CLI summary. Create only application-owned
immutable binding/decision values and an ephemeral implementation of the existing
CodingEvidencePort. No new Port, Core contract, dependency, provider behavior or
general approval subsystem is introduced.

Non-goals: repository discovery, semantic completeness, autonomous context
expansion, model-quality qualification, remote admission changes, retries,
fallback, frozen evaluation changes, live execution, credentials or deployment.
No accepted ADR is edited. The canonical architecture remains accurate; this is
application intent enforced using the existing public capability boundary.

## Confirmation semantics and binding

Only READY_FOR_CONTEXT_CONFIRMATION is eligible. The worker constructs a binding
before invoking the trusted composition callback with the immutable inventory.
Only literal boolean True confirms. Missing callbacks, false/non-boolean results,
exceptions and interruption decline with closed reasons. Incomplete context
cannot reach the callback. The CLI retains explicit y/yes, default No.

The versioned confirmation identity binds five SHA-256 digests:

| Component | Exact input |
| --- | --- |
| Repository | Composition-normalized root key, HEAD kind, branch and commit |
| Scope | Version label and sorted required paths with create/update/reference roles |
| Task | Objective and ordered constraints, including bounded rework feedback |
| Lifecycle | Governed execution id and tenant id |
| Inventory | Sorted paths, roles, existence, byte counts and exact content digests |

CREATE binds observed absence. Required reference paths remain distinct from
editable targets. Existing path validation and case-fold uniqueness reject
duplicates and aliases. The binding constructor also requires exact agreement
between the supplied request and inventory scope. No proposal exists at this
stage; later proposal identity and mutation approval remain separate.

The composite identity identifies this preflight decision within this execution;
there is no persisted receipt admission API, reusable token or implicit approval
from any previous run. Digests are evidence, not credentials or grants.

CONTEXT_CONFIRMED means only that the operator confirmed the bounded inventory
for subsequent disclosure processing. Confirmation itself calls no CodingAgent,
reviewer, model, check runner, mutation or network capability. The trusted
callback may interact with the operator; its configured implementation is part
of the application trust boundary.

## Orchestration and invalidation

The initial decision remains immediately after successful preflight and before
check-environment preparation and remote disclosure approval. Immediately before
CodingAgent.propose, the worker re-acquires through the same authorized reader,
projects metadata through the same function used by preflight, observes HEAD and
compares the full binding. Changed scope, root/HEAD, task, run/tenant, path,
existence or content digest refuses. Unreadable or no-longer-authorized context
also stops; it never falls back to the prior bundle. Cancellation propagates and
the workspace guard is released.

On success, a per-call immutable bundle implements the existing public
CodingEvidencePort for exactly the acquired targets, tenant and references.
CodingAgent serializes that bundle instead of independently reading a third
version. No asynchronous work intervenes between comparison and CodingAgent's
bundle acquisition. This closes the unchecked-reread gap without changing
CodingAgent or retaining file contents in task confirmation evidence.

Rework performs a fresh preflight and explicit confirmation because target
contents, CREATE/UPDATE roles, constraints and execution identity may change.
It cannot add files. A rework refusal preserves the earlier applied effects and
returns FAILED, not a false claim that the whole run had no effects.

Staleness is exact identity mismatch, not an invented wall-clock TTL. Read and
model authorization remain independently checked by their existing owners.
External filesystem changes after acquisition cannot alter the captured payload;
later mutations still require their existing exact preconditions. No atomic
filesystem snapshot or hostile-process isolation is claimed.

## Refusals and evidence

Closed reasons are CONTEXT_CONFIRMATION_REQUIRED, CONTEXT_CONFIRMATION_DECLINED,
CONTEXT_CONFIRMATION_INVALID, CONTEXT_INCOMPLETE, CONTEXT_CONFIRMATION_STALE,
CONTEXT_REPOSITORY_MISMATCH, CONTEXT_SCOPE_MISMATCH, CONTEXT_TASK_MISMATCH and
CONTEXT_INVENTORY_CHANGED. Existing EVIDENCE_DENIED/EVIDENCE_UNAVAILABLE task
failures retain fresh acquisition failures. A changed binding is CONTEXT_STALE
at the task boundary with its specific confirmation reason retained.

TaskEvidence holds at most two immutable decisions. Each records the requested
binding, whether the operator approved, and a closed refusal/invalidation reason.
The CLI prints the composite identity, inventory digest and effective result.
An approved decision may subsequently be invalidated; approved does not override
its refusal reason. Incomplete preflight is recorded without claiming a
confirmation was requested. No content, host path, raw exception, bearer or
provider payload is added to confirmation evidence.

## Independent authority and reviewer

Successful confirmation does not authorize model invocation, grant remote
disclosure, approve mutation or accept a review. Existing governed host admission,
custody, remote confirmation, proposal approval and check gates remain intact.
IndependentReviewer receives only the existing bounded derived proposal/check
material and exactly applied file contents whose digests are checked, consistent
with ADR-024 §8. It gains no new path or context authority from this slice.

## Offline tests and regression coverage

New test_context_confirmation covers deterministic evidence and exact identity;
each binding dimension; actual task/root/HEAD/execution changes; added, removed,
aliased and changed inventory; incomplete/duplicate inventories; strict boolean
approval; exception canaries; post-confirmation content drift; no unchecked third
acquisition; captured-bundle scope refusal; fresh rework confirmation; revoked
reads, unexpected acquisition failures and cancellation. Replay and fake sandbox
fixtures exercise successful coding and independent mutation refusal without
live inference. Existing preflight tests prove missing confirmation, no effects,
required paths and separate disclosure refusal. Existing LOCAL/REMOTE/PROJECT,
review, custody, model and architecture regressions remain in the validator.

The post-effect Git fault fixtures now trigger on observed mutation/model effects,
not on the ordinal of a read-only observation. The expired-read rework regression
still asserts denial and two prior model calls, but now requires no second
CodingAgent entry. Clean-install input includes confirmation for each proposal's
context; that build suite is not executed by this offline validator.

Requirements A-Z are covered by these focused tests plus the preserved preflight,
worker, rework, review, remote-profile, project-profile and architecture suites.
The exact baseline allowlist excludes Core, dependencies, accepted ADRs and all
historical/frozen model evaluation files.

## Files changed

- examples/forgeai/src/forgeai/repository_context.py
- examples/forgeai/src/forgeai/worker.py
- examples/forgeai/src/forgeai/domain.py
- examples/forgeai/src/forgeai/cli.py
- examples/forgeai/tests/test_context_confirmation.py (new)
- examples/forgeai/tests/test_architecture.py
- examples/forgeai/tests/test_domain.py
- examples/forgeai/tests/test_worker.py
- examples/forgeai/tests/test_review.py
- examples/forgeai/tests/test_rework.py
- examples/forgeai/tests/test_clean_install.py
- examples/forgeai/README.md
- planning/FORGEAI-CONTEXT-CONFIRMATION-1.md (new)
- validate_forgeai_context_confirmation_1.py (new)

## Maintainer validation

No tests, validators, builds, live calls or commits were executed by the agent.
Prerequisites: existing locked root, ForgeAI and Engineering environments, Python
3.14, uv and Git; no dependency acquisition. Working directory: repository root.
No credentials or environment variables are required. The validator selects
offline/synthetic suites and excludes real Docker/sandbox and build suites.

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_context_confirmation_1.py
if ($LASTEXITCODE -ne 0) { throw 'ForgeAI context confirmation validation failed' }
```

Expected only after successful maintainer execution:

`FORGEAI-CONTEXT-CONFIRMATION-1 LOCALLY QUALIFIED; EXACT REPOSITORY CONTEXT REQUIRES EXPLICIT OPERATOR CONFIRMATION; UNCONFIRMED OR STALE CONTEXT STOPS BEFORE MODEL DISCLOSURE; NO MUTATION, MODEL QUALITY, OR DEPLOYMENT AUTHORIZATION CLAIMED`

Risks: execution is pending; no global snapshot guarantee; trusted in-process
callbacks remain trusted; rework now requires an additional explicit prompt.
No qualification claim is made until the maintainer supplies passing evidence.
After qualification, recommended next separately scoped work is
FORGEAI-V0.2-BOUNDED-TASK-QUALIFICATION-1: deterministic application-level
qualification of the complete confirmed-context workflow. It is not authorized
or started here and implies no live provider evaluation.

Proposed commit: `feat(forgeai): bind operator confirmation to exact context`.
