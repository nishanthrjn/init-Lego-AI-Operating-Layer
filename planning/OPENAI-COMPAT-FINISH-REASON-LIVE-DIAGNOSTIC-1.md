# OPENAI-COMPAT-FINISH-REASON-LIVE-DIAGNOSTIC-1

Status: IMPLEMENTED; MAINTAINER VALIDATION PENDING.
Verification: NOT RUN — Awaiting user execution. No live execution authorized.

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

After successful maintainer validation only:

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
