# FORGEAI-KISSKI-SAIA-FUNCTION-CALL-SHAPE-DIAGNOSTIC-1

Status: implemented; NOT RUN — awaiting maintainer validation.
No provider calls, credentials, tests or validators were executed by the agent.
This is private diagnostic instrumentation, not a new acceptance decision.

## Historical evidence

Maintainer-provided execution `exec-70e5a0f9e74943879ee65e7d408d2dcf`
selected `qwen3-coder-next` through kisski-saia, stream=false, SYNTHETIC only.
HTTP 200 / HTTP/1.1 chunked reception completed: 626 decoded bytes, terminal
chunk seen, parser_rejected=false. JSON was valid and returned model matched.
The exact rejection was `FUNCTION_CALL_PRESENT`, with completed attempt,
effect none, DependencyFailure / terminal, ModelFailure.PROTOCOL_INCOMPATIBLE,
and final `CHAT_CONTRACT_REJECTED; NO RETRY`.

That evidence does not reveal the field's value category. No null, empty object,
tool execution intent or successful Model result can be inferred. New shape
diagnostics characterize future attempts only; historical results are unchanged.

## Existing rejection path and ownership

`src/legoai/reference/model_openai_compatible.py` owns the single strict JSON
decode and response contract. `OpenAICompatibleModelAdapter.chat` validates model,
choices, finish_reason, message object, role and string content in that order.
It then rejects `"tool_calls" in message` before `"function_call" in message`.
Both checks use key presence alone: null, {}, [] and all other present values
remain rejected. The checks are separate, with TOOL_CALL_PRESENT taking priority
when both fields exist. No tool or function execution capability is introduced.

The new observation runs after the content gate and immediately before these
presence checks. Both fields are classified independently from the already
decoded message. Earlier rejection leaves both observations unavailable, not
ABSENT. A caught observation failure leaves them unavailable and does not change
the existing acceptance, exception, custody, effect, timeout or retry behavior.

The existing local composition callback, bounded per-execution projection and
qualification runner already carry and print closed diagnostic tuples. They are
reused without source changes. The invocation plane still imports no concrete
adapter. There are no new Ports, public APIs, dependencies or provider branches.

## Shape taxonomy and safe fields

Private `_CallFieldShape` values:
ABSENT, NULL, EMPTY_OBJECT, NONEMPTY_OBJECT, EMPTY_ARRAY, NONEMPTY_ARRAY,
STRING, NUMBER, BOOLEAN, OTHER.

Boolean is classified before numbers. OTHER is defensive for non-JSON objects;
it is not a normal decoded JSON value. Empty/nonempty containers are distinguished
without traversing their entries. Strings are not inspected or distinguished by
length. No object key count is necessary.

The only additional diagnostic fields are:

| Field | Domain |
| --- | --- |
| function_call_present | true / false |
| function_call_shape | closed shape enum |
| tool_calls_present | true / false |
| tool_calls_shape | closed shape enum |

Only enums are retained on the adapter, reset for every chat. Projection accepts
exact enum instances; raw values are not retained. No key names, names, arguments,
content, reasoning, raw JSON, model IDs, hashes or lengths enter these fields.
The runner's existing tiny-prompt path prints these tuples without new parsing.

## Synthetic matrix and verification

The new test module covers each field independently: absent, null, {}, name-only
object, arguments-only object, both-key object, empty/nonempty strings, empty
array, nonempty synthetic array, integer zero, float and false. Both fields
present prove independent shapes and preserved tool-first rejection. Canary
values prove no payload exposure. Additional tests cover observation failure,
earlier failure, stale-state reset, defensive OTHER, and synthetic loopback TLS
runner output with unchanged completed custody, effect none and no retry.

Existing contract fixtures remain independent and unchanged. The maintainer
validator runs shape and acceptance tests, adapter/SRCP-1/custody/effect suites,
T2 chunked tests, KiSSKI runner regressions, LOCAL/Ollama and architecture checks,
mypy, Ruff and working/staged whitespace checks. Its scope pins the pre-slice
commit and compares the chat AST after removing only exact new diagnostic/reset
statements, guarding against altered acceptance. Synthetic TLS uses loopback;
there are no external network or provider calls and no real credentials.

## Compatibility evidence limits and future decisions

No first-party response schema was needed to implement observation. No new web
research was performed, and SAIA documentation coverage of explicit null fields
remains unestablished. OpenAI documentation is not used to infer SAIA behavior.

| Future observation | Decision to consider separately |
| --- | --- |
| NULL | Whether explicit null is equivalent to absent |
| EMPTY_OBJECT | Whether an empty object is harmless or invalid |
| NONEMPTY_OBJECT | Legacy field contains a payload; shape alone does not validate its semantics; keep rejection pending a separate capability/compatibility decision |
| Scalar or array in function_call | Provider response incompatibility under the current contract |
| NONEMPTY_ARRAY in tool_calls | Tool-call field contains entries; no execution intent or valid schema established by shape alone; keep rejected pending separate capability design |
| ABSENT or unavailable | Do not infer a shape from historical attempts or earlier failures |

None of these decisions is made in this slice. All present fields remain rejected.

## Maintainer handoff and future live design

Use the existing locked environment from the repository root, with no additional
environment variables or credentials. Run:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_kisski_saia_function_call_shape_diagnostic_1.py
if ($LASTEXITCODE -ne 0) { throw 'KiSSKI SAIA function-call shape diagnostic validation failed' }
```

Expected: all local phases pass, acceptance unchanged, no live qualification.
The agent must stop and wait for maintainer results.

Only after successful local validation and fresh explicit maintainer authorization,
one future diagnostic may use the existing `--live --receive-diagnostic` flow:
one discovery, exact `qwen3-coder-next` selection, one separately approved chat,
stream=false, `Return the exact token KISSKI_OK.`, two hidden separate-purpose
S1 provisions, receive + contract + shape diagnostics, no JSON stage, no retry,
fallback or reselection. This document does not authorize that execution.
No repository disclosure/mutation or generated-code execution is involved.

Final conclusion: FUNCTION_CALL_SHAPE_DIAGNOSTIC_READY
