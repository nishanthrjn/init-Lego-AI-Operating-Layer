# OPENAI-COMPAT-FINISH-REASON-SHAPE-DIAGNOSTIC-1

Status: IMPLEMENTED; MAINTAINER VALIDATION PENDING.
Verification: NOT RUN — Awaiting user execution.
No live execution authorized. No compatibility relaxation authorized.

## Motivation and evidence limits

The historical qwen3.5-397b-a17b / bug Phase A attempt completed transport with
sent_all and response_complete, but failed FINISH_REASON_INVALID. Its exact
finish-reason shape/value was not retained. INSUFFICIENT_SAFE_EVIDENCE remains the
historical classification. This change cannot reconstruct the missing observation.
Historical custody and all evaluation records remain unchanged.

## Contract and ownership

The OpenAI-compatible adapter still accepts exactly finish_reason == "stop".
Absent, null, length, content_filter, tool_calls, function_call, unknown strings
and non-string values still reject. Model identity and single-choice checks remain
before this gate, and message/content validation remains after it. Existing
function_call:null compatibility is unchanged.

The existing private ephemeral diagnostic projection gains finish_reason_category:
ABSENT, NULL, STOP, LENGTH, CONTENT_FILTER, TOOL_CALLS, FUNCTION_CALL,
OTHER_STRING, NON_STRING. Presence is represented by ABSENT rather than duplicated.
Only enum members are retained/projected. Unknown strings are never copied;
objects/arrays/numbers/booleans collapse to NON_STRING. State resets per chat.
Observation faults omit the category without changing acceptance or rejection.
No provider/model branches, public contracts, transport, custody, Secret,
disclosure, retry or agent behavior change.

The qualification runner already prints safe adapter diagnostics. The evaluation
runner copies only an allowlisted category for FINISH_REASON_MISSING/INVALID
records. Successful record shape and Phase B prior-report admission are unchanged.
Only the runner source pin changes; task/scoring/contract pins remain fixed.
No prompts, content, raw responses, headers, credential references, exception text
or arbitrary unknown values are added to diagnostics.

## Maintainer validation

The dedicated validator scopes seven files against the pre-slice commit, compares
chat acceptance AST after removing only the diagnostic reset/observation, preserves
existing adapter definitions outside the diagnostic surface, and checks frozen
source pins. Tests cover every category, non-stop rejection, stop acceptance,
null function-call compatibility, ordering, reset, corrupted state, observation
faults, canary suppression, evaluation projection and synthetic TLS custody.
Existing REMOTE, KiSSKI, LOCAL, chunked, evaluation and architecture regressions
remain included, followed by typing, lint, format and whitespace checks.

From the repository root with the existing locked uv environment, no additional
environment variables:

```powershell
uv run --locked --offline --no-sync python .\validate_openai_compat_finish_reason_shape_diagnostic_1.py
if ($LASTEXITCODE -ne 0) { throw 'Finish-reason diagnostic validation failed' }
```

Expected only after successful maintainer validation:

```text
OPENAI-COMPAT-FINISH-REASON-SHAPE-DIAGNOSTIC-1 LOCALLY QUALIFIED;
DIAGNOSTICS ONLY;
FINISH_REASON ACCEPTANCE UNCHANGED;
NO LIVE EXECUTION AUTHORIZED
```

No checks, builds or providers were run by the implementation agent. A new live
diagnostic requires implementation, maintainer validation, commit and fresh explicit
authorization. Do not retry Phase A under this slice. No model quality is qualified.

Proposed commit: `feat(diagnostics): classify finish reasons without changing acceptance`.
