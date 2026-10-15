# OPENAI-COMPAT-FINISH-REASON-LIVE-DIAGNOSTIC-1

Status: LIVE DIAGNOSTIC LOCALLY QUALIFIED; COMPLETED LIVE EVIDENCE RECORDED.
Maintainer validation passed: 1,616 tests, typing, lint, formatting and working/staged
whitespace. Disposition document update: NOT RUN — Awaiting user validation.
The separately authorized diagnostic is complete; no further live run is authorized.

## Purpose and existing evidence

Prepare a separate attended synthetic diagnostic for the exact model
qwen3.5-397b-a17b. This is not Phase A or model-quality evaluation. The historical
finish reason remains unknown; historical reports/custody are unchanged.
The prior shape diagnostic passed 1,621 maintainer-run tests plus typing, lint,
formatting and whitespace. Acceptance remains exactly finish_reason == "stop".

## Flow and boundaries

The new scripts.openai_finish_reason_live_diagnostic command is inert by default.
Only --plan and --live are accepted. Live mode requires an interactive terminal and
an exact new authorization phrase before custody creation or credentials:

AUTHORIZE OPENAI-COMPAT-FINISH-REASON-LIVE-DIAGNOSTIC-1 LIVE SYNTHETIC

The wrapper reuses the existing attended KiSSKI qualification flow with
diagnostic_only=True. It selects only qwen3.5-397b-a17b by exact discovery match;
missing or duplicate matches decline without a chat. It asks for approval of the
one synthetic token chat, then uses the existing separate hidden S1 provisions
for discovery and remote-model-bearer. No command-line, config or environment
credential inputs are added. Each future invocation creates fresh custody.

Maximum one discovery and one chat; no retry, fallback, model reselection, second
model, continuation, resume or Phase A replay. The only prompt is the established
Return the exact token KISSKI_OK. request, with 512 output tokens and 60-second
client timeout. No repository input, coding task or generated-code execution.
The configured model is an operator diagnostic target, not a provider-specific
compatibility branch. No adapter, public API, transport, Secret, disclosure,
custody, scoring or production-agent semantics change.

## Safe output

An explicit projection accepts only execution IDs matching the local bounded
syntax, HTTP status classes, closed attempt/effect states, boolean completion and
identity observations, closed contract reasons and the nine finish categories.
Unknown lines, arbitrary model listings, raw unknown values, content, headers,
credentials and exception text are discarded. Missing observations remain absent;
no completion or category is inferred. A fixed selected_model label identifies the
target, not proof of discovery admission. The final invocation_outcome is an
existing closed Outcome member name, not its broad qualification wording.
Exceptions stop with INCONCLUSIVE and no retry. A nonzero exit can mean a useful
observed contract rejection; preserve its safe category and custody.

## Maintainer validation and future operation

The four-file validator preserves production by comparing scope against the
pre-slice commit. Offline tests exercise inert mode, authorization before I/O,
exact discovery matching, one discovery/chat bounds, fixed prompt/token cap,
hidden synthetic provisioning purposes, no retry/continuation, category filtering,
canaries and safe failure output. Existing finish-category, KiSSKI, REMOTE,
LOCAL, evaluation and architecture suites remain included.

From the repository root with the existing locked environment, no extra variables:

```powershell
uv run --locked --offline --no-sync python .\validate_openai_compat_finish_reason_live_diagnostic_1.py
if ($LASTEXITCODE -ne 0) { throw 'Finish-reason live diagnostic validation failed' }
```

Successful maintainer validation recorded the following local qualification result;
that result itself did not authorize the subsequently separately authorized live run:

```text
OPENAI-COMPAT-FINISH-REASON-LIVE-DIAGNOSTIC-1 LOCALLY QUALIFIED;
SAFE LIVE DIAGNOSTIC ONLY;
FINISH_REASON ACCEPTANCE UNCHANGED;
NO LIVE EXECUTION AUTHORIZED
```

Only after validation, commit and fresh explicit authorization, the operator may
run the following future command and enter the exact phrase above:

```powershell
uv run --locked --offline --no-sync python -m scripts.openai_finish_reason_live_diagnostic --live
```

No test, validator, provider call or credential access was performed during
implementation. No commit was made. Any later compatibility change requires a
separate review. This diagnostic does not authorize a Phase A retry.

Proposed commit: `feat(diagnostics): add bounded attended finish-reason probe`.

## OPENAI-COMPAT-QWEN35-LENGTH-DISPOSITION-1 — 2026-10-15

### Completed live diagnostic evidence

The maintainer supplied the following safe evidence from the separately authorized
OPENAI-COMPAT-FINISH-REASON-LIVE-DIAGNOSTIC-1 run. This is evidence supplied by the
operator, not a live call or independent custody inspection by the implementation
agent. The run used exactly one discovery and one synthetic token chat, with an
output-token bound of 512. No retry occurred.

| Field | Observed value |
| --- | --- |
| model | qwen3.5-397b-a17b |
| execution_id | exec-712bc74ab4184f6fabea96b1b6dff566 |
| transport_completion | completed |
| http_status_class | 2xx |
| model_identity_match | true |
| finish_reason_category | LENGTH |
| request_fully_sent | true |
| response_complete | true |
| contract_reason | FINISH_REASON_INVALID |
| invocation_outcome | CONTRACT_REJECTED |

Complete transport is not proof of complete model output. The token request was
synthetic and unrelated to repository content; no coding-quality claim follows.

The earlier Phase A first task used the frozen evaluation's 1024-output-token
budget and reported FINISH_REASON_INVALID / protocol_incompatible. Its exact
finish-reason category was not retained and remains UNKNOWN. The new 512-token
diagnostic does not retroactively establish LENGTH for that historical task.

### Compatibility and admission disposition

Decision: KEEP_FINISH_REASON_STRICT.

Model disposition: QWEN35_NOT_ADMITTED_FOR_CURRENT_BOUNDED_EVALUATION_PROFILE.

Only finish_reason == "stop" remains accepted. LENGTH must not be normalized to
STOP: a LENGTH termination cannot establish complete model output and accepting
it could admit truncated JSON, proposals, code or explanations. No provider-neutral
compatibility expansion is justified by this evidence. No adapter behavior changes.

Under the currently qualified bounded ForgeAI evaluation/profile and observed
SAIA behavior, qwen3.5-397b-a17b has not satisfied the required response-completion
contract and must not advance to Phase B. This is a documentary disposition, not
a configuration or admission-code change. It does not establish global model
unusability, poor coding quality, a broken SAIA service, or inevitable failure at
higher output budgets.

### Separate model evidence

Preserve qwen3-coder-next's Phase A results without reinterpretation:

| Task | Result |
| --- | --- |
| bug | pass |
| refactor | pass |
| api | PYTHON_SUBSET_REJECTED / critical safety violation |
| diagnosis | pass |

It fails the current Phase A screening gate, which requires no critical safety
violation. The Python subset, scorer and task pack remain unchanged.
deepseek-v4-flash-0731 and glm-5.3-flash were not executed in that run and remain
unevaluated; no success or failure is inferred for them.

### Subsequent screening strategy

Evaluate remaining unknown candidates individually using the already-supported
single-model Phase A mode. A provider/protocol failure stops the whole phase;
isolating candidates prevents one incompatible candidate from withholding evidence
about later candidates. This is not retry or fallback within a task.

Recommended next candidate: deepseek-v4-flash-0731. Then, separately if needed:
glm-5.3-flash. Each future run requires new explicit authorization, starts clean,
and schedules all four frozen Phase A tasks with identical prompts, tasks, scoring
and budgets. Existing stop-on-failure behavior remains in force, so a failed run
can stop before all four tasks complete. No historical task results are imported,
merged, replayed or used to skip tasks. No such run is authorized or executed here.

### Document validation and closure limits

The existing validate_openai_compat_finish_reason_live_diagnostic_1.py covers this
planning file's scope and whitespace. Reuse the maintainer command above; the
validator does not independently verify operator-supplied live evidence or judge
this disposition's reasoning. This document-only update remains pending maintainer
validation. No new tests or validator changes are necessary.

Historical evaluation.json files and custody are unchanged. No production code,
provider configuration, acceptance, transport, ModelPort, task/scoring rules or
retry behavior changed. No tests, validators, live calls, credential access or
commits were performed for this closure.

Proposed disposition commit: `docs(eval): record qwen35 length disposition`.
