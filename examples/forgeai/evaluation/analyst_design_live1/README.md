# FORGEAI-ANALYST-DESIGN-LIVE-1 HARNESS

**HARNESS-RUNTIME-FIX-1 IMPLEMENTED — LOCAL VALIDATION PENDING.**
The prior harness was locally qualified offline, then its first authorized smoke
failed without a completed assessment. That history remains immutable. This fix
is verified offline only; no new smoke, provider call, FULL or Docker execution
is authorized or performed. No live model-quality claim.

## Authority and bindings

The harness binds `forgeai-analyst-design-live/1` to immutable
`forgeai-analyst-design-eval/2` and
`forgeai-analyst-sufficiency-live-profile/1`. Normalized UTF-8 source digests in
pins.json cover the frozen evaluation, Agent definition/parser/values and both
[profile](../../../../planning/FORGEAI-ANALYST-SUFFICIENCY-LIVE-PROFILE-1.md) and
[experiment](../../../../planning/FORGEAI-ANALYST-DESIGN-LIVE-1-DECISION.md)
decisions. Per-run provenance includes live harness hashes, prompt digest,
Agent fingerprint, model requirement, clean Git commit and platform/processor.
EvidenceSufficiencyAgent 1.0.0 and its SYSTEM prompt/parser remain unchanged.

Report identity: `forgeai-analyst-sufficiency-live-report/1`, separately checked
against report-schema.json. Grounding is explicitly NOT_MEASURED; full revision-2
aggregate verdict is NOT_APPLICABLE. No numeric grounding, scripted analysis
claim, raw model response, explanation or chain-of-thought is persisted.
Complete bounded parsed requests, governing citations, failures and input-payload
digests are retained. Request descriptions remain untrusted model text.

## Closed execution modes

PREFLIGHT, SMOKE and FULL are explicit, separate operator modes. Importing modules
performs no calls. PREFLIGHT verifies exact loopback endpoint, model tag/digest,
Ollama 0.35.1, committed code/decisions, clean tracked tree and fresh destination;
only GET /api/version and /api/tags are issued, in a bounded probe process.
No proxy, redirect, credentials or remote endpoint is supported. Before each
semantic call, tracked cleanliness, commit and source bindings are rechecked. Ignored/untracked
scratch is not described as a dirty tracked tree; required harness files must
exist in HEAD. A runtime version difference requires identity review and does
not proceed automatically. Refusals are reported without evaluation calls.

SMOKE is exactly d01,d05,d09,d13,d20,d21 initial, maximum six calls, no follow-up.
It never receives full-profile SUPPORTED. Passing output is
`SMOKE_PASS — FULL RUN STILL REQUIRES EXPLICIT APPROVAL`.
FULL requires a passing smoke report with matching provenance and a separate
operator approval reference. Approval references record trusted operator input,
not a cryptographic authorization service. Neither mode escalates automatically.

FULL has 56 condition rows, 70 planned slots and at most 68 model calls: d27/d28
remain deterministic non-model controls, q19-q22 remain nongating regressions.
Each resolved variant starts a fresh sequence. Interventions use only frozen
paths/clarifications after scoring the complete request set. No repair, retries,
fallback, discovery, mutation or final RepositoryAnalyst call exists.

AuthorizedRepositoryEvidence supplies synthetic fixture contents, through the
same bounded in-memory authorized evidence composition as revision 2; no model
path becomes a filesystem read. EvidenceSequence owns one-round transitions.
Every semantic invocation uses EvidenceSufficiencyAgent.assess and the public
local governed host, never a copied prompt or direct ModelPort invocation.
The pre-dispatch guard compares the governed USER input with the independent
input-facts projection and the permitted evidence/clarification transition.

## Metrics and failure custody

The profile reuses revision-2 summarize and request scoring; it never uses the
aggregate evaluate verdict. All complete-partition metrics retain frozen planned
denominators. If a partition has unexecuted rows, its metrics explicitly say
UNAVAILABLE_INCOMPLETE_PARTITION: do not silently shrink denominators or invent
attempt records. The full planned counts, observed records, call lifecycle and
not-recorded slots remain visible. Observed-condition summaries reuse the frozen
computations independently and are labelled by scope; they are not a reduced
full-condition aggregate. Conditional terminal sequences with an initial
assessment remain in the frozen denominator even when no final call occurs.

Safety takes precedence over runtime, contract, incomplete, usefulness and support.
Run completeness remains independent. Uniform smoke disposition blocks continuation.
Expected operational controls must all function. Semantic regression results are
separate; no safety failure can be repaired into independent success.

A fresh exclusive directory and UUID identify each run. Each call-start,
call-finish and parsed observation is exclusively created and flushed to disk;
completed files survive interruption. Final JSON and Markdown are never overwritten.
There is no resume or run-merge operation. A hard process kill may leave an absent
or partial final report; immutable lifecycle/observation files remain inspection
evidence only, not authority to resume or claim a completed run.

Per-call timeout is min(600 seconds, remaining budget with two seconds reserved
for bounded client cleanup); smoke budget is 1800 seconds, full 21600 seconds.
A supervised child contains the blocking adapter thread; timeout/interruption
terminates that client process and tests exercise the timeout path offline.
**Server inference termination is not proven.** Reports preserve
SERVER_EFFECT_UNKNOWN rather than equating client termination with stopped
Ollama inference. No subsequent work or automatic resume follows an interrupted
call. This is local client supervision, not a Core cancellation redesign.

## Operator qualification

From repository root:

```powershell
uv run python .\validate_forgeai_analyst_design_live_1.py
```

The extended 99-phase validator sets an explicit offline provider fence inherited by
spawned children. It uses fixed responses through the real governed Agent path,
fake identity probes, failure injection and existing evaluator/Agent/loop/Analyst/
worker regressions, followed by mypy, Ruff and diff checks. No Ollama, provider
endpoint or Docker is needed.

Operator qualification recorded on 2026-10-07 for implementation commit
`662a367`, using the repository-root command above. All **65/65 phases passed**,
including **598 tests** (**69 harness tests**), revision-1/revision-2, sufficiency
Agent, evidence-loop, RepositoryAnalyst, ForgeAI worker and governed runtime
regressions, mypy, Ruff lint/format and git diff check. Qualification is offline
contract/conformance evidence only. No live Ollama/provider call, smoke/full live
run, final RepositoryAnalyst analysis or Docker execution occurred. No live
semantic-quality, stability or production-readiness claim follows.

Next, run the extended validator for operator local qualification, commit the
qualified fix when authorized, and establish a clean tracked tree. Obtain fresh
explicit maintainer authorization before any NEW smoke identity. Full execution requires another
explicit approval after smoke review. No runnable smoke/full command is supplied
as part of this implementation-only delivery. LIVE-2, final analysis, production
integration and G07 closure remain unauthorized.

## HARNESS-RUNTIME-FIX-1 (2026-10-07)

The actual-provider composition now supplies the existing selection
`{"revision": "live1", "binding": "ollama"}`. Core host-selection semantics and
the Ollama adapter are unchanged. Offline regressions exercise this same branch
with DNS/socket/HTTP fences installed after Windows event-loop initialization;
the Agent is stopped before inference. Removing binding fails the regression.
Replay composition remains independently covered.

`execution_lifecycle` is additive to the separate LIVE-1 report/1; historical
reports without it remain readable. It partitions MODEL_CALL_OPPORTUNITIES into
NEVER_ATTEMPTED, ATTEMPTED_NO_RESULT and COMPLETED_RESULT, with identity lists,
per-slot finish custody, and planned/attempted/completed counts. It derives
starts and finishes from durable call files and completed phases from durable
observation files, not transient returned rows. A semantic failure returned by
the Agent is a completed result, not a child-process failure or quality pass.
A finish file alone does not establish semantic result custody. Orphan finishes,
duplicate starts and completed model results without starts are rejected.

For this partition, planned = never_attempted + attempted_no_result +
completed_result, and attempted = attempted_no_result + completed_result.
FULL retains 70 semantic slots and separately partitions 68 model opportunities;
d27/d28 remain non-model controls. `not_run` now lists only condition rows with
no started model call, excluding controls; per-phase unreached opportunities
remain in the lifecycle lists even after a row's initial call. Frozen semantic
metrics and denominators are unchanged.

The child emits an ordered, bounded closed stage protocol: CHILD_STARTED,
HOST_COMPOSITION_STARTED/COMPLETED, AGENT_CALL_STARTED,
PAYLOAD_GUARD_STARTED/COMPLETED, GOVERNED_RUNTIME_ENTERED, RESULT_COMPLETED.
An Agent prerequisite result may complete before entering the payload guard.
The parent flushes separate immutable per-call diagnostic records on observed
stages and at cleanup, and embeds the final diagnostic in the finish record.
Call/phase identity is supplied by the parent. No raw exception, traceback,
prompt, environment dump, hidden oracle, secret or model explanation is added.

Closed failure categories distinguish observed launch, bootstrap, composition,
pre-dispatch Agent, timeout, abnormal exit, protocol and invalid-result failures;
UNKNOWN_CHILD_FAILURE covers unlocated failures. TRANSPORT_FAILURE is reserved
but not inferred: this harness has no adapter transport receipt. Bootstrap
failure can only be located after child entry; an exit before any marker is not
proof of an import failure. Exception identifiers use an explicit allowlist,
with OtherException otherwise. Result/failure envelopes, EOF, invalid envelopes,
pipe errors, observed exit codes and parent terminate/kill actions are separate.
An error envelope does not mean abnormal process exit. Cleanup remains bounded
within the existing two-second reserve, including a 0.5-second natural-exit wait.

GOVERNED_RUNTIME_ENTERED is not ModelPort entry, HTTP initiation, or provider
acceptance. `model_dispatch` and `http_request` remain NOT_OBSERVED;
`provider_acceptance` remains UNKNOWN. No missing marker narrows historical or
future uncertain effects to NONE. SERVER_EFFECT_UNKNOWN remains conservative.
No result-parse stage is invented inside the unchanged Agent implementation.

The historical smoke and preflight are checked byte-for-byte against the
committed diagnostic's eight-file SHA-256 inventory. They are required local
qualification inputs; missing history fails the guard rather than being skipped.
The original smoke remains runtime failed / SERVER_EFFECT_UNKNOWN.

No profile, revision-2 artifact, Agent 1.0.0, prompt/parser, model pin, membership,
N, call/time ceiling, outcome precedence, threshold, grounding interpretation,
retry policy or authority changed. See the
[diagnostic and implementation record](../../../../planning/FORGEAI-ANALYST-DESIGN-LIVE-1-CHILD-FAILURE-DIAGNOSTIC.md).

Implementation verification completed offline: **99/99 validator phases passed**,
including **617 tests (88 harness tests)**, mypy, Ruff lint/format and diff checks.
This is the implementation check, not the pending maintainer/operator execution
of the validator. No provider endpoint, smoke, FULL or Docker was invoked.
