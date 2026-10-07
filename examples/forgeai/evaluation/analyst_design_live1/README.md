# FORGEAI-ANALYST-DESIGN-LIVE-1 HARNESS

**IMPLEMENTED — LOCAL VALIDATION PENDING.** Harness and offline verification only.
No live model-quality claim. No smoke, full run, Ollama or Docker was invoked.

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

The 65-phase validator sets an explicit offline provider fence inherited by
spawned children. It uses fixed responses through the real governed Agent path,
fake identity probes, failure injection and existing evaluator/Agent/loop/Analyst/
worker regressions, followed by mypy, Ruff and diff checks. No Ollama, provider
endpoint or Docker is needed. Run statuses remain pending until operator execution.

After operator qualification, obtain explicit maintainer authorization before
smoke; use a committed clean harness/runtime. Full execution requires another
explicit approval after smoke review. No runnable smoke/full command is supplied
as part of this implementation-only delivery. LIVE-2, final analysis, production
integration and G07 closure remain unauthorized.
