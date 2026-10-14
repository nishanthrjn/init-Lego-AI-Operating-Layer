# OPENAI-COMPAT-FUNCTION-CALL-NULL-COMPATIBILITY-REVIEW-1

Date: 2026-10-14.
Status: documentary review complete; maintainer validation pending.
Decision: ACCEPT_FUNCTION_CALL_NULL_EQUIVALENCE
Scope: legacy function_call absent or JSON null only.
Production acceptance remains unchanged in this review.
No implementation or live execution is authorized by this review.

## Latest live evidence and limits

Maintainer-provided execution: exec-8425fb5a51484bc0b15d08e53dc5e095.
Provider/model: kisski-saia / qwen3-coder-next; stream=false; synthetic prompt.
HTTP 200; HTTP/1.1 chunked; body complete; 626 decoded body bytes;
terminal chunk seen; parser_rejected=false; JSON valid; returned model matches.
Observed: function_call_present=true; function_call_shape=NULL.
Observed: tool_calls_present=false; tool_calls_shape=ABSENT.
Historical result: FUNCTION_CALL_PRESENT; ModelFailure.PROTOCOL_INCOMPATIBLE;
CHAT_CONTRACT_REJECTED; NO RETRY; completed attempt; chat effect none.

No function name, arguments or callable payload were observed. JSON null contains
no callable request payload. This does not infer model intent, prove the expected
KISSKI_OK token, establish coding quality, or retroactively accept this attempt.
Earlier attempts retain their own evidence and must not inherit this shape.

## Existing contract and reason for strictness

Sources reviewed:

- `src/legoai/reference/model_openai_compatible.py`: `_json_body`, `_reject`,
  `_optional_tokens`, `_record_call_shapes`, `_chat_contract_items`, `chat`.
- `src/legoai/intelligence/model/values.py`: `ChatResult`, `ModelUsage`.
- `src/legoai/runtime/_composition/remote_model.py`: `_Invocation.exchange`.
- `src/legoai/runtime/_composition/model_governed.py`: governed result settlement.
- `scripts/kisski_saia_qualification.py`: fixed-token acceptance after Model result.
- `scripts/tests/test_kisski_saia_contract_diagnostics.py` and
  `scripts/tests/test_kisski_saia_function_call_shapes.py`: presence rejection,
  separate shapes, ordering, safe projection and failure isolation fixtures.
- `adrs/ADR-014.md` sections 14.8, 14.11 and 14.12; `architecture/ARCHITECTURE.md`
  authority boundaries and Action Mediation ownership.

Current policy: any tool_calls key presence rejects, then any function_call key presence rejects, regardless of value.
The adapter first decodes strict JSON, requires exact model identity, one choice,
finish_reason=stop, message object, assistant role and string content. It records
shapes, applies those two independent presence gates, extracts optional usage,
and constructs a plain-text ChatResult. There is no function dispatch branch.

ADR-014 section 14.12 excludes tools/function calling from the minimal common
subset; section 14.8 preserves stop-only completion and fail-closed malformed
responses. Presence rejection is the implementation's conservative mechanism for
excluding unsupported payloads, demonstrated by existing null/empty tests. The
ADR does not separately mandate rejection of a null-valued legacy key. No claim
about the original author's undocumented motivation is necessary.

## Decision and security/authority analysis

Accept null equivalence for a future adapter-local implementation. Both absent
and explicit JSON null provide no callable payload to interpret. ChatResult
carries content, identities and optional usage only; it contains no executable
tool request or authority grant. Content remains untrusted data under the existing
deterministic authorization and Action Mediation boundaries.

No tool execution, function dispatch, new host action, disclosure admission, Secret-use permission, custody schema or retry policy is introduced.
The future rule is provider-neutral; no provider-name or model-name branch.
The future legacy-field gate may use message.get("function_call") is None.
Use identity with None, never truthiness: false, 0, empty strings and containers
are non-null and must remain rejected. No function names or arguments are read.

Tool_calls policy unchanged: every present tool_calls value remains rejected.
Keep that gate before the legacy gate, including when function_call is null.
Non-null function_call values remain rejected: {}, nonempty objects, [], nonempty arrays, strings, numbers, booleans and every other non-null value.

Transport custody completes before parsing; existing INTENDED/outcome facts and
uncertainty handling are not altered. A future otherwise-valid null response
would use the existing success path instead of the current rejection path.
Future accepted responses use existing SUCCEEDED/COMPLETED mapping; historical rejected/NONE results are not rewritten.
This is an intentional result-category change, not a new effect mapping. The
governed disclosure observation already records COMPLETED for both a complete
rejected response and a successful Model response; admission stays unchanged.
Unknown transport completion remains UNKNOWN; no retry, fallback or replay is added.

## Compatibility basis and governance

The maintainer's safe live observation proves that this SAIA response serialized
the optional legacy field as null. It is a plausible absence serialization with
no payload, not proof of every provider's schema or full protocol conformance.
No external documentation was used; no public web or provider API calls were made.
No OpenAI documentation is being used to infer SAIA behavior. This is a local
compatibility decision grounded in observed structure and inspected control flow.

Governance assessment: no new ADR required for this null-only adapter compatibility rule.
This preserves ADR-014's exclusion of function-calling capability, its identity
and stop-only gates, and the existing public architecture. It creates no Port,
authority, ownership or effect-semantic change. Accepted ADRs remain untouched.
If later work proposes non-null support or new dispatch, that is outside this
decision and requires separate architectural review. Architecture documentation
does not become inaccurate because production behavior is unchanged here.

## Complete response gate and diagnostic truth

All other response checks remain required: strict JSON, exact model identity,
exactly one dictionary choice, finish_reason=stop, message object, assistant role,
string content, absent tool_calls, no non-null function_call, and valid ChatResult
construction. Governed binding identity and the runner's exact KISSKI_OK check
still apply. Null alone cannot establish success or expected-token agreement.

Usage semantics unchanged: missing/non-object usage becomes None; invalid individual token counts become None; only nonnegative exact integers are retained.
This records actual `_optional_tokens` behavior, rather than inventing a new
usage-validation gate or claiming that current malformed usage rejects.

Diagnostics preserve function_call_present=true and function_call_shape=NULL after future acceptance.
Do not normalize evidence to ABSENT. Shape collection remains separate from
acceptance and content-free. Preserve tool_calls presence/shape independently;
earlier failures leave later observations unavailable. No raw response, function
name, arguments, provider key names, credentials or Secret material may be logged.

## Required future synthetic acceptance matrix

All accepted rows require every other gate to pass. These are future tests,
not changes to the currently rejecting fixtures in this documentary slice.

| ID | Input or invariant | Required future result |
| --- | --- | --- |
| A | function_call absent | Accept if all else valid |
| B | function_call null | Accept if all else valid |
| C | function_call {} | Reject |
| D | function_call nonempty object | Reject without reading name/arguments |
| E | function_call [] | Reject |
| F | function_call nonempty array | Reject |
| G | function_call string, including empty | Reject |
| H | function_call number, including zero | Reject |
| I | function_call boolean, including false | Reject |
| J | tool_calls absent plus function_call null | Accept if all else valid |
| K | tool_calls present plus function_call null | TOOL_CALL_PRESENT wins for null/empty/nonempty tool values |
| L | Accepted explicit null diagnostics | Present true, shape NULL; no raw content |
| M | Authority and dispatch | No tool/function execution path; content remains data |
| N | Effects and custody | Existing success/rejection/UNKNOWN mappings and completed transport facts preserved |
| O | Otherwise malformed response with null | Reject at existing first gate |

O includes invalid/duplicate JSON, model mismatch, invalid choice count/shape,
missing/non-stop finish_reason, invalid message/role and non-string/null content.
Exercise LOCAL and REMOTE with synthetic transport, no real credentials, and
preserve canary, stale-state and observation-failure tests. Add non-null falsey
regressions to prevent accidental truthiness acceptance. Preserve T2, SRCP-1,
Secret isolation, disclosure, runner and architecture regression suites.

## Handoff and next slice

Next slice: OPENAI-COMPAT-FUNCTION-CALL-NULL-1
Separate implementation instruction required; minimal generic adapter-local gate
change only. Reuse the single decoded object and existing diagnostics. No worker,
CodingAgent, ModelPort, tool_calls, T2, custody, dependencies or public API changes.
SRP/SoC keep observation distinct from acceptance; DRY keeps one null rule;
KISS/YAGNI avoid a tool subsystem; LSP preserves all previously accepted replies;
OCP/ISP/DIP require no provider branch, new interface or ForgeAI coupling.

The companion validator checks documents and Git scope only, including positive
and negative documentary fixtures. It does not execute production, tests, builds,
Ruff, mypy, network requests or credential access. The two-file scope leaves all
production, existing tests, accepted ADRs and dependency files unchanged.
Document checks cannot establish runtime or live qualification.

From the repository root with the existing locked environment, no additional
environment variables or credentials:

```powershell
uv run --locked --offline --no-sync python .\validate_openai_compat_function_call_null_compatibility_review_1.py
if ($LASTEXITCODE -ne 0) { throw 'OpenAI-compatible function_call null compatibility review failed' }
```

Verification: NOT RUN — awaiting maintainer execution.
No live connectivity or coding quality is qualified by this review.
