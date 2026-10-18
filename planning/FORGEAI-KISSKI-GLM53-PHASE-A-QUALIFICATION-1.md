# FORGEAI-KISSKI-GLM53-PHASE-A-QUALIFICATION-1

Status: KEEP_GLM53_NOT_ADMITTED; LENGTH DISPOSITION VALIDATION PENDING.
Readiness validation: PASSED by maintainer; disposition extension NOT RUN.
NO LIVE EXECUTION AUTHORIZED; NO PHASE B AUTHORIZED.

## Baseline and integrity

Clean initial baseline: `12de226b1549eedd8f983dd7b96345344b942aea`.
Source inspection found no changes to the evaluation directory, qualification
configuration or OpenAI-compatible adapter since reviewed baseline `201c4294`.
The frozen manifest is unchanged, with expected normalized SHA256
`3cd0e5a14f6ff9d2beba5cb1af9bcc6ac214637a7b3858ad3282bd0e51691ef6`.
The retained reports identify semantic pack digest
`2bab09bdd0177040c67833611d67b54f56916d5a2f0366f914bb33d4f65edc57`.
Source-manifest and semantic pack digests are distinct identities.

The new documentary validator pins this baseline and permits only itself and
this document to change in working/index scope. It reuses `frozen.verify(ROOT)`
to check the existing source manifest and canonical contract hashes, also
requiring the expected manifest digest. No pins are refreshed. These integrity
checks are prepared, not executed by the agent.

## Existing qualification and historical GLM evidence

The host-lifecycle correction remains present in `runner.live`: one host created
inside one event loop per model, capacity four, sequential awaited invocations,
stop on provider failure. Phase A starts with no previous records. The maintainer
previously supplied the lifecycle pass with 76 evaluation tests and supporting
regressions, manifest `618f870f8121eb69e3e5becae931b6141b272215480c7080190210712547f61f`.
Later finish-reason diagnostic validation also included 76 passing evaluation
tests. This is historical evidence, not a new current-baseline test run.
Existing tests cover lifecycle, exact selection, partial evidence and scoring;
this slice adds no functional behavior and no duplicate evaluation framework.

Two retained derived reports were inspected read-only under
`C:/Users/nisha/AppData/Local/Temp/`:

| Custody directory | Safe retained observation |
| --- | --- |
| `kisski-coding-eval-qpogdycg` | `bug`: `exec-bdb7596dc6e946e8b3cc7069354c40ee`, `FINISH_REASON_INVALID`, `LENGTH`, `protocol_incompatible`; one failed invocation row |
| `kisski-coding-eval-wfzugxcm` | `bug` passed: `exec-62aa6f76b5b64e5e9a647c7f02ece961`; `refactor`: `exec-36ca18a226be4bedb088535c788633b4`, `FINISH_REASON_INVALID`, `LENGTH`, `protocol_incompatible` |

Both report `RESULT_INCONCLUSIVE`, null quality scores and no qualified groups.
Existing GLM evidence is inconclusive; provider failures are not quality scores.
Their source-manifest identity and full attempt effect state are not established
by these derived reports alone. No chronology, repeatability or global inability
is inferred. Custody databases, credentials and raw responses were not read.
These reports remain unchanged and are not imported into any future run.

DeepSeek: `NO_MODEL_QUALIFIED`; `MODEL_NOT_QUALIFIED`.
Pilot: `ADMISSIONS` remains empty.
The earlier recommendation to treat GLM as wholly unevaluated is superseded by
the partial evidence above. A new evaluation would require explicit authorization
with awareness of both prior failures, not an automatic replay recommendation.

## Exact prospective session

Model: `glm-5.3-flash`.
Tasks: `bug`, `refactor`, `api`, `diagnosis`.
Bounds: one discovery; four chats; 1024 output tokens; 60 seconds per chat.
Acceptance: only `finish_reason == "stop"`; LENGTH remains rejected.
No retry, fallback, model reselection, resume or historical record merging.

`runner.selected` supports one unquoted model ID and intersects the frozen
`OBSERVED` inventory, fresh discovery and eligible models. GLM is in the frozen
inventory; fresh account eligibility remains unknown. The shared generic plan
permits multiple models, so the operator must select GLM alone and confirm the
displayed bound is four chats. Decline if selection or bound differs.
Use existing hidden S1 provisioning, purpose separation and fresh custody only.
No credentials in arguments, environment variables or documents. Inputs remain
the frozen synthetic prompts; no repository disclosure or production mutation.

## Maintainer validation

Prerequisites: repository root, existing locked Python 3.14 environment and
installed offline dependencies. No new environment variables, Docker or installs.

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_kisski_glm53_phase_a_qualification_1.py
if ($LASTEXITCODE -ne 0) { throw 'GLM Phase A readiness validation failed' }
```

Expected: local document checks and frozen integrity pass, prior GLM protocol
failures remain recorded, no model quality qualified, no live authorization.
The validator includes positive/negative required-statement controls and staged
document checking when staged. It does not rerun regression suites or claim new
behavioral qualification. Supply its result before advancing this slice.

Historical prospective procedure (superseded by the no-call disposition below):
only after successful local validation and a new separate live authorization,
an attended operator may choose to run:

```powershell
uv run --locked --offline --no-sync python -m scripts.kisski_coding_eval.runner --live --phase A
```

Copy the exact authorization phrase printed by the current runner. Provision
through hidden prompts; select only `glm-5.3-flash` without quotes or commas if
fresh discovery lists it. Confirm the four-chat ceiling. If unavailable, stop.
This document does not authorize that operation or any repeat of prior attempts.

## Outcome decisions

- Incomplete/provider/protocol failure: preserve all completed evidence and
  uncertainty; stop. Do not count failure placeholders as incorrect code.
  A repeated LENGTH refusal calls for a bounded-profile disposition, not a
  higher budget, relaxed acceptance or automatic retry in this slice.
- Four unique completed rows: apply unchanged `runner.screening`. All four must
  be schema-valid, instruction-adherent, scope-disciplined and free of critical
  safety violations; at least three must meet acceptance criteria.
- Screening failure: retain it as failure of this frozen gate. No pilot admission.
- Screening pass: consider a separately authorized Phase B review; no automatic
  continuation. Reviewer suitability and pilot admission remain separate gates.

Phase A's overall report remains `RESULT_INCONCLUSIVE` even on a screening pass;
full classification requires Phase B. Preserve the complete fresh custody
directory and derived report, including execution IDs and partial records.
Missing rows do not prove no calls; effect truth requires retained attempt
evidence. Do not invent NONE/COMPLETED states from score fields. Pre-task
discovery/provisioning exceptions may remain unclassified in the current report.

## FORGEAI-KISSKI-GLM53-LENGTH-DISPOSITION-1

Decision: KEEP_GLM53_NOT_ADMITTED.
Next action: STOP; NO LIVE CALL OR AUTOMATIC PHASE A REPEAT.
Disposition baseline: `3c7273692bd44ccdf0e25beec4abdc80066ba1b5`.

The maintainer successfully ran the readiness validator: exact scope, frozen
source and canonical pins, documentary controls and whitespace all passed.
This closes the earlier readiness-validation pending status, not the new
disposition validation. It did not authorize live execution or qualify GLM.

Both preserved reports were re-read. They identify `glm-5.3-flash`, Phase A,
and the same semantic pack digest recorded above. The first has zero completed
model invocations and one protocol-failure row; the second has one completed
passing bug invocation and one protocol-failure row. Neither has four completed
tasks. Both remain `RESULT_INCONCLUSIVE`; coding quality is neither qualified
nor disqualified by these incomplete screenings. No records were merged.

Read-only SQLite inspection of each `model-0/remote-attempts.db` selected only
attempt ID, execution ID, state and categorical observations. No record payload,
credential database, token, prompt or response body was accessed.

| Execution | Attempt | Transport custody |
| --- | --- | --- |
| `exec-bdb7596dc6e946e8b3cc7069354c40ee` | `attempt-bd1524a07b75db5f07ca80cae3c7dd68` | completed; sent_all; response_complete |
| `exec-62aa6f76b5b64e5e9a647c7f02ece961` | `attempt-677855a6f2a9775250d0818427f4c9b4` | completed; sent_all; response_complete |
| `exec-36ca18a226be4bedb088535c788633b4` | `attempt-25b794f2831f9a769230327ec9137ce7` | completed; sent_all; response_complete |

Transport completion is not generation completion or accepted model output.
The LENGTH rows remain provider_or_protocol_failure / protocol_incompatible /
FINISH_REASON_INVALID. The accepted bug row remains completed / VALIDATED.
No no-send claim, task retry or rewriting of historical effects is justified.

Current adapter source rejects any finish_reason other than the exact string
`stop`. LENGTH is consistent with incomplete generation and cannot establish
that output satisfies the completion contract. Token exhaustion, hidden token
accounting and the exact provider cause are not independently established;
failed rows retain null output-token counts. Complete HTTP responses do not
resolve that uncertainty. Do not normalize LENGTH to STOP or add model-specific
acceptance branches. Preserve all budgets, tasks, scoring and historical custody.

A further call has no defined discriminating hypothesis needed for this admission
decision. A smaller synthetic smoke would not establish completion of the frozen
tasks, and another unchanged Phase A would repeat prior work without a new basis.
Therefore no separate bounded live diagnostic is justified by current evidence.
This is a profile-specific admission decision, not global model-quality judgment.

Smallest evidence action: retain these reports and custody with the existing
safe metadata linkage; run only the documentary validator below. Reconsider
live research only in a separate proposal identifying new evidence, a concrete
question, fixed bounds and explicit authorization. No new call is recommended now.

The existing validator command above is reused for this disposition. Expected
claim: local document checks passed; KEEP_GLM53_NOT_ADMITTED; no model quality
qualified; no live execution authorized. Its current-baseline scope permits only
this document and the validator to change. Disposition verification remains
NOT RUN — Awaiting user execution.
