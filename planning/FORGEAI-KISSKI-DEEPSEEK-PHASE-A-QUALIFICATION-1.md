# FORGEAI-KISSKI-DEEPSEEK-PHASE-A-QUALIFICATION-1

Status: EVIDENCE_INSUFFICIENT — current-baseline maintainer validation pending.
Verification: NOT RUN — Awaiting user execution.
No live execution, credentials, model qualification or pilot admission authorized.

## Baseline and existing qualification

Reviewed commit: `201c4294c4e443ae56f0252a974e5e0e3a5f98ce`.
The working tree was clean before this readiness slice. Only this record and
`validate_forgeai_kisski_deepseek_phase_a_qualification_1.py` are added.
The existing frozen harness is reused without modification.

The maintainer supplied a successful host-lifecycle validator transcript in this
conversation: 76 evaluation tests, 48 frozen evaluation regressions, 524 REMOTE
tests, 126 KiSSKI tests and 397 architecture tests; typing, lint, formatting and
whitespace checks passed. Its final result was
`FORGEAI-KISSKI-CODING-EVAL-HOST-LIFECYCLE-1 LOCALLY QUALIFIED; NO MODEL QUALITY QUALIFIED; NO LIVE EXECUTION AUTHORIZED`.
Its source-manifest digest was
`618f870f8121eb69e3e5becae931b6141b272215480c7080190210712547f61f`.
This is maintainer-reported evidence, not an internally repeated check.
The older evaluation plan's pending lifecycle wording is stale; its history is
preserved. Later maintainer finish-reason diagnostic validation also included
76 passing lifecycle/evaluation tests.

The repair is commit `023a6cf`. Inspection of `runner.live` confirms construction
and use of one host inside one event loop per model, capacity four, sequential
awaited tasks, and stop on failed provider invocation. Phase A initializes empty
prior records; only Phase B reads a prior report. No retry, fallback, concurrency
or resume is introduced. Existing lifecycle tests cover success, returned failure,
unknown exception, loop ownership and exact capacity.

The runner subsequently gained bounded finish-reason diagnostic projection in
`52ea38d`. Historical passes are not blanket qualification of today's baseline.
The old validator measures scope against `18fc8e9b53e96e93717075f1be4d521bc9ef16b5`;
later committed work and this readiness document exceed that slice. The new
validator uses today's baseline and exact two-file scope, reuses existing tests
and integrity verification, and does not widen or change the old validator.

## Frozen identity and bounds

Pack version: `FORGEAI-KISSKI-CODING-MODEL-EVALUATION-1`.
Current normalized source-manifest SHA256 (file hash only, not executed integrity
verification): `3cd0e5a14f6ff9d2beba5cb1af9bcc6ac214637a7b3858ad3282bd0e51691ef6`.
The manifest pins the pack, scorer, runner, frozen verifier and reused contract
and safety sources. The validator must verify these pins and canonical schemas.
This source-manifest identity is distinct from the semantic `pack_digest` in
derived reports; preserve the actual digest emitted by the future runner/report.
No pins were refreshed.

Exact candidate: `deepseek-v4-flash-0731`. It is in `pack.OBSERVED`; fresh account
discovery eligibility is UNKNOWN until a separately authorized session. Selection
requires membership in both inventories. A single unquoted ID is supported.
No substitute candidate is allowed by this run plan.

Tasks, in frozen order: `bug`, `refactor`, `api`, `diagnosis`.
Maximum one discovery and four task chats, 1024 output tokens per task and
60-second client timeout. Existing prompts, fixtures, proposal contract, scoring,
scope and Python safety gates remain unchanged. The generic runner plan can show
the multi-model ceiling; after selecting this one ID its actual bound must be
four chats. Decline if the selected model or actual bound differs.

## Failure and scoring interpretation

| Evidence | Interpretation |
| --- | --- |
| Discovery cannot list the exact candidate | No task screening; no model substitution |
| Discovery/provisioning exception before task records | Inconclusive; current generic exception path does not reliably distinguish these causes in the derived report |
| Provider/transport/protocol failure | Failed invocation, not an incorrect-code score; stop the phase |
| `MODEL_ID_MISMATCH` | Exact response identity rejected |
| `TOOL_CALL_PRESENT` / `FUNCTION_CALL_PRESENT` | Unsupported call contract rejected |
| `FINISH_REASON_MISSING` / `FINISH_REASON_INVALID` | Completion contract rejected; safe category may refine evidence |
| Completed invocation with malformed proposal | Structured-output/schema failure, distinct from provider failure |
| Completed, valid but incorrect proposal | Score the frozen acceptance criteria |
| Scope or Python subset safety violation | Critical safety gate failure; never relax the scorer |
| Incomplete invocation or unclassified exception | Preserve uncertainty; do not infer no effect or retry |

Only `finish_reason == "stop"` is accepted; LENGTH remains rejected. Existing
null function-call equivalence and all other adapter gates remain unchanged.
Do not infer historical finish categories that were not retained.

Four unique completed Phase A task records for this exact model are required for
full screening. `runner.screening` requires all four schema-valid, instruction-
adherent, scope-disciplined and free of critical safety violations, with at least
three acceptance-criteria passes. Report per-task correctness and the existing
schema reliability counters separately from protocol failures and missing rows.
Do not manufacture scores for missing or failed provider invocations.

The Phase A report's overall `RESULT_INCONCLUSIVE`, null full-evaluation summaries
and empty qualified groups are expected: full classification requires Phase B as
well. Exit success alone does not establish screening eligibility. Inspect all
four records against the existing screening predicate. A Phase A pass is neither
general coding competence nor production readiness.

## Custody and security

Use existing S1 hidden provisioning, separate discovery/chat purposes and fresh
runner-created custody. No credentials in arguments, environment variables,
configuration, source or reports. Frozen synthetic inputs only; no repository
disclosure, generated-code execution or workspace mutation is added.

The runner saves completed rows after each task and attempts a final save. Retain
the complete custody directory and derived `evaluation.json`; never overwrite,
import or resume historical attempts. Persistence itself can fail: do not assert
that absent rows prove absent calls. Execution IDs and attempt custody supply
effect evidence; derived rows alone do not expose every attempt state. Preserve
UNKNOWN where evidence is insufficient. No raw errors, responses or credential
stores should be printed or shared. The pre-task discovery/provisioning diagnostic
limitation remains explicit rather than guessed; no new diagnostic semantics are
needed to prepare this bounded run. A failure requiring finer classification
must return for safe inspection before any separately authorized new attempt.

## Maintainer validation and future interaction

Prerequisites: repository root, existing locked Python 3.14 environment and all
offline dependencies already present. No environment variables or Docker needed.
The validator reuses synthetic/loopback tests; it does not run a live provider.

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_kisski_deepseek_phase_a_qualification_1.py
if ($LASTEXITCODE -ne 0) { throw 'DeepSeek Phase A readiness validation failed' }
```

Expected: every phase passes, ending in local checks passed, no model quality
qualified, fresh discovery still required, no live execution authorized. Stop and
provide the transcript. Current-baseline verification remains pending until then.

Only after relevant local validation passes AND separate live authorization:

```powershell
uv run --locked --offline --no-sync python -m scripts.kisski_coding_eval.runner --live --phase A
```

Use an attended terminal. Type the exact authorization phrase printed by the
current runner; provision only through hidden prompts. After discovery enter
`deepseek-v4-flash-0731` alone, without quotes or commas, only if displayed. Confirm
the four-chat bound and approve the synthetic phase. If unavailable, stop. Preserve
the report and custody on success or failure. Do not authorize Phase B or replay.

## Next decision

DeepSeek remains unevaluated and not admitted to the bounded pilot. `ADMISSIONS`
is unchanged. Review the fresh four-task evidence before any later milestone.
Even a Phase A pass requires separate pilot-admission review of connectivity,
structured-output smoke, reviewer-role suitability, completion compatibility,
the exact pilot output budget and current operator disclosure conditions.
Discovery alone is insufficient. No existing qwen or other candidate result is
changed by this readiness record.
