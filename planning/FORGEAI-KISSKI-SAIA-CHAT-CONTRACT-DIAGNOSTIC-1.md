# FORGEAI-KISSKI-SAIA-CHAT-CONTRACT-DIAGNOSTIC-1

Status: Implemented diagnostic slice; maintainer validation pending.
Verification: NOT RUN — Awaiting user execution.

## Evidence and qualification boundary

Maintainer-supplied execution `exec-bb47ed9c86cf404b8d9e5c373cb85fe0` used
KiSSKI/SAIA at https://chat-ai.academiccloud.de/v1, exact qwen3-coder-next,
stream=false and `Return the exact token KISSKI_OK.` Discovery completed with
HTTP 200. Chat attempt completed with HTTP 200; TLS connected, request fully sent,
first byte seen and headers complete. HTTP/1.1 chunked, no Content-Length,
638 encoded bytes observed, 626 decoded bytes, one chunk, terminal seen, no
trailers. body_complete=true; parser_rejected=false; cap_reached=false;
read_error=false. First byte: 275 ms; headers-to-complete: 3 ms; total: 279 ms.
The next-layer result was DependencyFailure/terminal, protocol_incompatible,
effect NONE and CHAT_CONTRACT_REJECTED. No raw body was inspected or retained
by this task and the earlier attempt is not replayed.

The descriptive statement **SAIA T2 live transport interoperability observed**
applies to that exact response. It is an observation, not a new qualification
enum or gate. T2 framing succeeded; HTTP completed; the OpenAI-compatible
contract failed; no Model semantic result was obtained; ForgeAI was not invoked;
coding quality was not measured. NONE is the existing result mapping, not proof
of no provider-side computation. KISSKI-SAIA LIVE CONNECTIVITY QUALIFIED is not
established. No live execution is authorized here.

## Exact call graph and decision tree

1. `_CredentialFlight.receive` returns complete decoded `HttpResponse` bytes.
2. `_Invocation.exchange` in `runtime/_composition/remote_model.py` settles the
   exact durable attempt and Secret use, captures complete HTTP status, then
   returns `(status, body)` to the per-invocation adapter. Diagnostics cannot
   change this already-settled transport truth.
3. `OpenAICompatibleModelAdapter.chat` calls `_request`, with stream=false and
   the configured exact model. Supplied exchange bypasses LOCAL `_post` I/O.
4. `_payload`: 429/503 are retryable-rejection categories without automatic
   retries. Other non-2xx map to request/model-unavailable categories, not chat
   schema diagnoses. Complete 200 enters `_json_body`.
5. `_json_body`: JSON decoding rejects invalid syntax/encoding, duplicate keys
   at any depth, NaN/Infinity constants, excessive parser recursion and other
   caught ValueError/UnicodeError/RecursionError conditions: JSON_INVALID.
   Valid JSON null/array/scalar fails ROOT_NOT_OBJECT. Chat retains the existing
   float decoder; this slice does not introduce finite-number enforcement there.
6. `chat` checks in this exact short-circuit order:
   - model missing -> MODEL_FIELD_MISSING;
   - model not exact str -> MODEL_FIELD_NOT_STRING;
   - model not equal to configured name -> MODEL_ID_MISMATCH;
   - choices missing -> CHOICES_MISSING;
   - choices not list -> CHOICES_NOT_LIST;
   - count not exactly one -> CHOICE_COUNT_INVALID;
   - sole choice not dict -> CHOICE_NOT_OBJECT;
   - finish_reason missing -> FINISH_REASON_MISSING;
   - finish_reason != stop -> FINISH_REASON_INVALID;
   - message missing -> MESSAGE_MISSING;
   - message not dict -> MESSAGE_NOT_OBJECT;
   - role != assistant (including absent) -> ROLE_INVALID;
   - content missing -> CONTENT_MISSING;
   - content null -> CONTENT_NULL;
   - content not exact str -> CONTENT_NOT_STRING;
   - tool_calls key present, even null/empty -> TOOL_CALL_PRESENT;
   - function_call key present, even null/empty -> FUNCTION_CALL_PRESENT.
7. Every rejection above still uses the same `_reject` and unchanged
   ModelResponseRejectedError/PROTOCOL_INCOMPATIBLE. Optional diagnostics record
   the first reason; they neither continue inspection nor choose acceptance.
8. Usage is optional. A nondict/absent value yields usage=None. A dict produces
   ModelUsage with nonnegative exact integers, otherwise None per token count.
   Thus USAGE_INVALID is not an existing chat rejection path and is not added.
9. Construct ChatResult with exact configured/confirmed ModelId, configured
   ProviderId, string content and normalized usage. Validated inputs satisfy
   constructor invariants. Unexpected construction faults are tagged
   RESULT_CONSTRUCTION_FAILED and re-raised unchanged, not converted into a
   new protocol error. Success records VALIDATED (not a rejection).
10. Governed composition still checks returned identities against the binding
    and performs its existing effect/error mapping. This later defensive identity
    check is not `_reject`; its default failure is provider_execution_failure,
    so it does not explain the observed protocol_incompatible label here.
11. Runner checks exact KISSKI_OK only after protocol success. Wrong token yields
    CONTENT_REJECTED without changing transport completion or adapter acceptance.

For this known path, complete HTTP 200 plus the adapter's protocol rejection
supports the inference that bytes reached the JSON decoding attempt; it does
not establish json_valid=true. There was no per-gate observation in the old run.

## Observability matrix

| Candidate | Current classification | Evidence limit |
|---|---|---|
| TLS/connect/send/framing failure, incomplete body, cap or timeout | EXCLUDED | Complete bounded transport diagnostics in this run |
| Invalid JSON or invalid root | POSSIBLE | Exact choice NOT OBSERVABLE FROM CURRENT EVIDENCE |
| Missing/nonstring/mismatched model | POSSIBLE | Exact choice NOT OBSERVABLE FROM CURRENT EVIDENCE |
| Missing/invalid choices, count, choice | POSSIBLE | NOT OBSERVABLE FROM CURRENT EVIDENCE |
| Finish reason missing or not stop | POSSIBLE | NOT OBSERVABLE FROM CURRENT EVIDENCE |
| Message/role/content shape violation | POSSIBLE | NOT OBSERVABLE FROM CURRENT EVIDENCE |
| Tool/function key present | POSSIBLE | NOT OBSERVABLE FROM CURRENT EVIDENCE |
| Malformed optional usage alone | EXCLUDED | Existing parser ignores/normalizes it |
| Harmless extra fields alone | EXCLUDED | Existing parser ignores them |
| Reasoning field replacing required content | POSSIBLE | Required content may be absent/null; actual shape NOT OBSERVABLE |
| Reasoning field alongside valid required fields | EXCLUDED as sole cause | No reasoning interpretation or extra-field rejection |
| Wrong synthetic token alone | EXCLUDED as cause of protocol_incompatible | Valid string is adapter-compatible; runner applies separate smoke test |
| Unexpected constructor fault | EXCLUDED as ordinary protocol rejection | Exceptions propagate; no existing `_reject` there |

## Identity, finish, content and unknown fields

ADR-014 §14.11 requires exact, case-sensitive response model equality. Aliases,
backend-normalized names and provider substitutions remain rejected. Diagnostics
report only the equality relationship, never the raw returned model string.
If mismatch is observed, a subsequent scoped identity/alias decision will need
authoritative exact requested/served identity evidence; this slice supplies no
alias allowance and collects no provider-selected model text.

Only finish_reason=stop is accepted. length, tool_calls, content_filter, null,
missing and arbitrary provider values are refused. An absent or nonstring content
is refused; empty string is accepted by the adapter but fails the fixed-token
smoke test. Lists/content parts/text-style choice fields do not substitute for
choices[0].message.content. Tool/function keys are refused by presence, not truthiness.

Unknown root/choice/message fields are ignored after strict JSON decoding.
Duplicate fields and invalid numeric constants still fail decoding even inside
otherwise ignored structures. reasoning_content alongside valid content is ignored;
it is not interpreted, exposed in diagnostics or accepted as replacement content.
No first-party SAIA model-specific schema was established in this task. No external
network research was necessary to instrument these deterministic gates, and none
was performed under the no-network constraint. Upstream Qwen behavior is not
assumed to describe SAIA. Any special live reasoning schema remains unknown.

## Private diagnostic schema and ownership

The adapter owns `_ChatContractReason`, `_record_contract`, `_contract_reject`
and `_chat_contract_items`. JSON diagnosis is emitted by the same `_json_body`
decision, not a second parser. Existing guards preserve rejection order and
acceptance. Embeddings, model discovery and non-2xx status mapping are unchanged.

| Field | Closed values and availability |
|---|---|
| rejection_reason | The enum cases in the tree plus VALIDATED and RESULT_CONSTRUCTION_FAILED; first terminal observation only |
| json_valid | false for JSON_INVALID; true after decoding otherwise; absent if parsing was never observed |
| returned_model_matches_requested | false on MODEL_ID_MISMATCH; true only after that check passed; absent when unknown |
| expected_token_match | Runner-only true/false after a valid ChatResult for the fixed TINY_PROMPT; absent on contract rejection |

No arbitrary structural scan follows a failure. Later choices, role, content and
finish fields remain unknown after an earlier rejection. No raw model ID, content,
reasoning, tool argument, provider field/key, digest, credential, SecretRef or
request ID is collected. No content length is needed for first-gate diagnosis.

REMOTE composition copies the closed projection after the per-invocation adapter
finishes/raises, keyed by exact ExecutionId. The private local-host accessor
enforces host type, thread confinement and minted execution identity as existing
receive diagnostics do. At most one tuple per attempted execution is retained,
bounded by the existing attempt capacity. Nothing is persisted in custody.
Each adapter chat resets its reason; collection/projection/access failures are
isolated and cannot replace result/error/effect truth. The runner prints only
this projection for its fixed tiny prompt. Existing --receive-diagnostic disables
JSON Stage 3 and retains both receive and contract diagnostics, including on
successful tiny responses.

## Synthetic coverage and design review

`scripts/tests/test_kisski_saia_contract_diagnostics.py` exercises every rejection
reason, malformed/duplicate/nonfinite/deep JSON, non-object roots, count and finish
policies, required message fields, empty tool keys, optional usage, exact/wrong
tokens, harmless/reasoning extras, construction exception identity, stale-state
reset, corrupted enum refusal and callback failures. Synthetic chunked TLS tests
exercise the existing adapter, runner, custody/effects, one discovery plus one
chat, partial transport, canary containment and diagnostic failures at each layer.
No real provider payload is needed. The validator also runs existing independent
adapter, T2, SRCP-1, custody, LOCAL and architecture regressions.

SRP/SoC: parser decisions own contract evidence; T2 remains separate. OCP: no
provider-name branch. LSP: unchanged accepted responses/errors. ISP/DIP: no
ModelPort/ForgeAI API. DRY: reason derives at the existing gate, no second parser.
KISS/YAGNI: one closed reason and two facts, no introspection framework. Private
immutable tuples cross the diagnostic boundary; upper layers do not traverse
parser state. T2, Secret, disclosure, custody and retry implementations unchanged.

## Future single live diagnostic and decision matrix

No new call is authorized. After local validation, explicit maintainer authorization
may permit one new --live --receive-diagnostic run of scripts.kisski_saia_qualification:
one discovery, exact qwen3-coder-next selection, stream=false, fixed KISSKI_OK
prompt, one approved chat, receive plus contract diagnostics, no JSON Stage 3,
no retries/fallback. Existing hidden S1 prompts and exact live authorization remain.

| New evidence | Next action, not an automatic behavior change |
|---|---|
| JSON_INVALID / ROOT_NOT_OBJECT | Investigate provider/API contract |
| MODEL_ID_MISMATCH or missing identity | Exact identity/alias architecture review; no relaxation |
| Null/alternate content or message shape | Response-shape compatibility decision |
| Missing/invalid finish reason | Finish-reason compatibility decision |
| Tool/function/required reasoning-shape failure | Capability/profile review |
| VALIDATED + expected_token_match=false | Protocol connectivity observed; semantic smoke fails; no final qualification |
| VALIDATED + expected_token_match=true | Candidate for exact endpoint/model/run live connectivity qualification; coding quality separate |
| Diagnostic unavailable or construction fault | Inspect local instrumentation/implementation evidence; do not guess or replay |

## Maintainer validation

Working directory: repository root. Prerequisites: existing locked uv development
environment and Git. No credential/environment setup. Tests use synthetic loopback
TLS only; no provider calls, external network, builds or install checks.

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_kisski_saia_chat_contract_diagnostic_1.py
if ($LASTEXITCODE -ne 0) { throw 'KiSSKI SAIA chat contract diagnostic validation failed' }
```

Expected: local checks pass for safe diagnostics only. No exact historical live
cause or Model/live connectivity qualification is claimed. Paste results before
the next milestone. No tests or validators were run internally.

Final conclusion: SAFE_CONTRACT_DIAGNOSTICS_REQUIRED
