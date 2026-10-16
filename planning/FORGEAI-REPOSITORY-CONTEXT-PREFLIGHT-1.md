# FORGEAI-REPOSITORY-CONTEXT-PREFLIGHT-1

Status: IMPLEMENTED — MAINTAINER VALIDATION REQUIRED.
Verification: **NOT RUN — Awaiting user execution**.
Baseline: `85f78ac6e382afdc379ccfe43b94e5d4fcd07375`.

## Problem and authority

Required repository evidence was acquired inside CodingAgent, so missing context
looked like a coding attempt rather than a distinct deterministic pre-coding gate.
The primary direction is [the v0.2 readiness review](FORGEAI-V0.2-REPOSITORY-ENGINEER-READINESS-1.md),
especially sections 14–15 and 20. Accepted ADR-002 keeps application intent in
ForgeAI; ADR-014 supplies public governed composition; ADR-024 keeps disclosure
admission separate from local inspection and mutation approval. None changes.

The current implementation instruction narrows section 20's proposed standalone
root-inventory approach: integrate explicit-path sufficiency immediately before
coding. Root discovery, implicit guidance selection and recursive structure
inventory are deferred. This does not claim to implement the entire section 20
discovery proposal. No new public Port or architectural authority is needed.

## REUSE / EXTEND / CREATE

- REUSE TaskRequest, CodingRequest, RepositoryPath, CodingEvidencePort,
  AuthorizedCodingEvidence and its separate target/reference authorization,
  workspace policy, content digests, Git start identity and workspace guard.
- EXTEND ForgeAI worker, composition, CLI and TaskEvidence with preflight and
  explicit context confirmation. Existing proposal/disclosure gates remain.
- CREATE only the application-owned repository_context module, immutable bounded
  metadata values, focused tests and the slice validator.

## Input and decision model

All declared UPDATE targets and all declared read-only context paths are required.
CREATE targets require observed absence under an existing authorized parent.
TaskRequest remains the intent contract; composition's allowed paths remain
independent authority. No optional file, required symbol, source-root guessing or
semantic-completeness claim is introduced. Empty supporting context is valid when
the operator has declared none; the targets still require inspection.

`preflight_context(reader, request)` acquires exactly the requested evidence via
the existing public reader, validates matching target/reference sets, discards
text and returns stable sorted metadata. It never calls an agent or executes
checks. Existing portable path grammar, case-alias rejection, hidden-path
exclusions, symlink/junction protections and authorization rechecks remain with
their existing owners. No direct filesystem abstraction is added in ForgeAI.

| Outcome/reason | Worker disposition before first coding attempt |
| --- | --- |
| READY_FOR_CONTEXT_CONFIRMATION | Show inventory; require explicit `True` from the trusted confirmer. Missing confirmer declines. |
| CONTEXT_INCOMPLETE / DENIED | Existing EVIDENCE_DENIED rejection; no authority expansion. |
| CONTEXT_INCOMPLETE / UNAVAILABLE | CONTEXT_INCOMPLETE rejection. Public reader deliberately does not distinguish missing, unreadable and authorization-service unavailability. |
| CONTEXT_INCOMPLETE / BOUNDARY or BUDGET | CONTEXT_INCOMPLETE rejection. |
| CONTEXT_INCOMPLETE / ACQUISITION_FAILED or EVIDENCE_MISMATCH | CONTEXT_PREFLIGHT_FAILED infrastructure/reader-contract rejection, never a model failure. |
| Ready inventory not confirmed | CONTEXT_DECLINED rejection. |

Invalid task/path values still fail task construction. Git unavailability,
unsupported HEAD and dirty start retain existing reasons before preflight.
Cancellation during acquisition propagates; unexpected acquisition exceptions
produce only a closed reason, never arbitrary exception text.

## Bounds and evidence

Existing bounds: 1–8 targets, 0–8 references, 960 UTF-8 path bytes, 8192 bytes per
file, 24576 target bytes and 16384 reference bytes. Workspace policy additionally
limits reads, depth and parent listings; no recursive traversal is introduced.
The existing CodingAgent serialized-input bound remains independently enforced
after re-acquisition. Ready is not a guarantee that an eventual serialized coding
prompt fits, nor a reservation of future read/disclosure permission.

TaskEvidence retains preflight outcome, one closed reason on failure, at most 16
sorted items on success and context_confirmed. Each item has relative path,
required role (create/update/reference), observed existence, byte count and
content digest (or absent for CREATE). Successful items imply authorized readable
files, or authorized verified absence. No raw text, exception, credentials or
host absolute path is retained. Existing start HEAD/run identity binds observations
to the worker's guarded repository run. No new evidence file is written.

## Integration and authority

RepositoryTaskWorker._run performs preflight after committed clean start and
before PROJECT environment preparation, remote disclosure confirmation or
CodingAgent.propose. Success alone never invokes CodingAgent: context confirmation
is a separate attended CLI question or explicit trusted callback. Checks and
model invocation then follow their existing governed flow. Proposal approval is
still required before mutation; IndependentReviewer stays after coding/checks.

CodingAgent re-acquires and re-authorizes current content; preflight text is never
cached into its prompt. Observations are not an atomic snapshot. The existing
stable-workspace assumption remains, including possible changes after confirmation.
The single existing rework budget and later review semantics are unchanged.

## Tests and production scope

Production files: examples/forgeai/src/forgeai/{repository_context,domain,worker,
composition,cli}.py. Regression fixture callers now provide explicit separate
context confirmation. Existing missing/budget/denial assertions move to preflight
evidence rather than a fabricated first coding attempt. Architecture controls
cover the new application module.

Focused tests cover deterministic inventory, readiness without model calls,
default refusal, missing/directory paths, scope denial, portable path/case/count
validation, closed failures, metadata-only output, separate disclosure and
confirmation. Existing context tests cover byte limits, CREATE, injection inertness,
reference isolation and rework. Engineering workspace tests cover filesystem
boundaries, including links and bounded reads. Validator includes existing ForgeAI,
PROJECT, LOCAL/REMOTE synthetic and KiSSKI regressions and architecture checks.

No Core, ModelPort, T2, provider, task pack, scorer, frozen evaluation manifest or
historical model evidence changes. DeepSeek is not newly qualified or authorized.
No PlannerAgent, automatic crawl, optional context, indexing, role routing,
retry/fallback, model quality assessment or live call is added.

## Maintainer validation and limits

From repository root, use pre-existing locked root, ForgeAI and Engineering uv
environments (Python 3.14, Git, installed dev dependencies). No sync/install is
performed. Existing CLI metadata-readiness tests can require the configured Docker
CLI/engine/image; real workload tests are excluded from this slice validator.
No credential or provider environment variable is needed. Network model calls are
synthetic/local TLS only. Run:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_repository_context_preflight_1.py
if ($LASTEXITCODE -ne 0) { throw 'ForgeAI repository context preflight validation failed' }
```

Expected only after successful maintainer execution:

```text
FORGEAI-REPOSITORY-CONTEXT-PREFLIGHT-1 LOCALLY QUALIFIED; DETERMINISTIC PRE-CODING CONTEXT GATE ESTABLISHED; CONTEXT_INCOMPLETE STOPS BEFORE CODING; NO MODEL QUALITY OR DEPLOYMENT AUTHORIZATION CLAIMED
```

Open limits: semantic sufficiency remains operator-owned; no snapshot isolation;
public UNAVAILABLE deliberately cannot identify an exact missing/unreadable cause;
full prompt admission remains CodingAgent's responsibility. New confirmer argument
defaults to refusal: embedding callers must explicitly adopt this gate. Historical
validators expecting the old prompt sequence are not the new slice's qualification.
After this validator passes, the next proposed slice is bounded declared-root
guidance inventory from readiness section 20, with separate authorization before
implementation. No next milestone starts while this validation is pending.
