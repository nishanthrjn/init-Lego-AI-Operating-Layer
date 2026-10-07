# Configuration-selected Model composition proof

This is the first narrow reference implementation of configuration-driven
composition, not a complete application manifest/runtime product. See
[ADR-019](../adrs/ADR-019.md).

## Development direction

Build minimum stable primitives, prove an end-to-end runtime slice through a real
consumer, then generalize from repeated evidence. Accepted canonical documents
and ADRs remain authoritative. The assessment app exposed a platform gap; its
dotenv convenience and dependency-free export are not proof of governed platform
composition. This increment adds the private reusable mechanism and an executable
offline consumer proof; migrating the assessment HTTP composition is separate.

Next use Career Inbox Assistant to drive actual Email/Gmail and Notification/
Telegram needs; Job Discovery and then ForgeAI provide broader consumers.
Do not prebuild those adapters now. Apply the Rule of Two except where accepted
foundational invariants already justify a mechanism. Prefer deterministic logic,
then one model invocation, before workflows or autonomous Agents. Additional
Agents require distinct responsibility, context, authority, lifecycle and evaluation.

## Input and ownership

A host captures input, for example:

    {"revision": "composition-1", "binding": "offline"}

Changing binding to ollama selects the other known compatible contribution in
the offline proof. These labels are local operator bindings, not global provider
names. The host supplies the expected owner-issued ConfigurationRevisionRef;
input cannot publish a revision or select another tenant by changing a string.

Inside Core composition, use capture_model_selection, then compose_model in the private
legoai.runtime._composition.model_selection module. Pass an explicit
CapabilityRequirement, trusted contribution tuple, Catalog and evaluation time.
The resulting route and configured association feed existing invoke_routed_chat
after the normal authorization and coordinator path. Construction grants no
permission to invoke.

Each contribution pins the full CatalogEntry, ModelBinding, configuration
revision and Plugin lifecycle record. The Catalog remains the admitted published
candidate source. Explicit selection can choose among compatible candidates but
does not erase ambiguity from the retained resolver result. Failed selection
does not call a constructor or another provider.

Environment/.env are optional host input mechanisms only. They must be captured
and validated into explicit values; semantic modules do not read them implicitly.
No database/service or generic precedence/merge language is added. Configuration
cannot import a Python class, install a Plugin, provide admission, or issue
authority. Known host constructors are executable code supplied by the operator,
not data. Raw Secret values are not supported in this input.

## Verification

Run from the repository root:

    uv run --locked --no-sync python -m pytest -q tests/integration/composition/test_model_selection.py tests/integration/composition/test_model_governed.py tests/unit/reference/test_model.py tests/unit/reference/test_model_foundation.py tests/architecture/test_import_boundaries.py
    uv run --locked --no-sync python -m mypy src tests examples/model_routing.py

| Requirement | Evidence / limit |
|---|---|
| Same consumer, changed binding | FixedModel and actual Ollama adapter with mocked transport; exact provider identity and classification JSON asserted |
| Unknown binding | Explicit unknown-binding failure before construction |
| Unavailable/unpublished contribution | Exact entry absent from Catalog fails before construction |
| Incompatible provider | Capability version mismatch rejected, regardless of ModelPort shape |
| Invalid data / executable configuration | Closed fields, types, bounds and duplicates rejected; import/class/tenant/admission/Secret fields rejected |
| Unadmitted Plugin | Validation alone and non-active admission cannot publish Catalog contributions |
| Cancellation | Cancellation propagates, claims are not replayed; provider cessation is not claimed |
| Disabled Plugin | Non-active lifecycle rejected even if a stale Catalog entry remains |
| Missing dependency | Constructor ImportError becomes explicit missing-dependency failure; no fallback |
| Initialization failure | Explicit failure, safe category and preserved restricted cause |
| Invocation failure | Actual mocked transport refusal/timeout retain existing NONE/UNKNOWN mapping and single invocation |
| Stale configuration | Full expected revision association checked; mismatches fail without latest substitution |
| Restart pin | Two fresh processes reconstruct the same exact selection; different expected revision rejected |
| Secret reference missing | Not applicable to the two credential-free fixtures; authenticated providers unsupported, not silently satisfied |
| Error/timeout/resource/evidence contract | Existing Model/governed tests retained; no new budget, transport or evidence guarantees |
| Behavioral evaluation | Deterministic classification/schema regression only; live quality, tool behavior, latency and cost qualification still required |

Ollama response buffering and worker cancellation limitations remain as documented
in [ports and adapters](ports-and-adapters.md). Cancellation does not prove that
the provider stopped. No retries, fallback, generation limits, generalized tool
support or live-reload mechanism is introduced.

Only trusted in-process wiring is covered. Lifecycle values and Catalog facts
are not cryptographic attestations against hostile Python code. The host must
manage current records/withdrawal. Restart proof is configuration reconstruction,
not durable in-flight recovery or revival of an old authorization.

## Follow-up acceptance gates

Before claiming production substitution, use executable real-consumer evaluations
for quality, hallucination, structured outputs, requested tool behavior, latency,
usage/cost and regressions, alongside adapter contracts and security negatives.
Reject unsupported required capabilities explicitly. Retain provider-specific
extensions behind declared contracts instead of weakening the common interface.
Implement Secret-reference access only with explicit purpose/consumer/tenant and
current authorization. Configuration grants none of these.

No new foundational abstraction or configuration storage service follows from
this proof. Expand only when the next real consumer supplies concrete evidence.

Local validation: the focused composition/Model/architecture suite passed 333 tests.
This is scoped offline evidence, not full-platform or live-provider qualification.

## OPENAI-COMPATIBLE-MODEL-1 (ADR-014 §14)

Implemented; **LOCALLY QUALIFIED** by operator validation. Applications use only
`legoai.runtime.api` and, at their composition root, `open_local_host` from
`legoai.runtime.local`. Domain code receives `GovernedHost` and owner contracts.
The closed provider union is `OllamaSettings | OpenAICompatibleSettings |
TrustedModelContribution`. Trusted contributions remain supported; no import
strings, registry, fallback, automatic retry or per-call routing is introduced.

`OpenAICompatibleSettings` is frozen/slotted and requires these explicit fields:
`base_url`, `chat_model`, `embedding_model`, `timeout_seconds`,
`max_output_tokens`, `provider_id`, and `deployment`. Optional values are expressed
as `None`. `ModelDeployment` has LOCAL and REMOTE; REMOTE fails at open with
`HostFailure.UNSUPPORTED_COMPOSITION` before admission or adapter construction.
LOCAL is an operator attestation about processing location, never inferred from
the URL. A loopback tunnel to a remote service is REMOTE and unsupported.

The API root includes its version prefix: `http://127.0.0.1:8000/v1` becomes
`http://127.0.0.1:8000/v1/chat/completions`, never `/v1/v1/chat/completions`.
Chat sends only `model`, plain-text `messages`, `stream: false`, and `max_tokens`
when configured. `max_output_tokens` accepts an exact integer in 1..2**31-1,
or None (omitted); the representation bound is not provider capacity or a cost
budget. Models use the existing 1..256-character identity bound, with blank,
control-character and non-UTF-8 names rejected. Timeouts must be positive and
finite. Full semantic settings validation happens at host open; Python type
errors are rejected at value construction, consistent with Ollama settings.

Chat requires exactly one choice, an assistant message with string content,
the exact configured response model, and `finish_reason == "stop"`. `length`,
missing/other finish reasons, tools, malformed success and streaming are rejected.
Usage counts are optional nonnegative integers; missing/invalid counts remain
unknown, never fabricated zeros. No alias resolution is performed.

Embeddings are available only when `embedding_model` is configured. The request
is `POST {base_url}/embeddings` with `model` and `input`. Response model must match
exactly; count and ordered indexes must match inputs; vectors must have consistent
positive dimensions and finite numeric components. Empty input/result has the
existing dimension 0 contract. With no embedding model, the host publishes only
CHAT and refuses EMBEDDING with PURPOSE_UNAVAILABLE before dispatch.

| Observation | Governed effect / recoverability |
| --- | --- |
| Connection refused or DNS failure before send | NONE / POTENTIALLY_RETRYABLE |
| Timeout, reset, incomplete body (including an error body) | UNKNOWN / REQUIRES_INTERVENTION |
| Complete 429 or 503 | NONE / POTENTIALLY_RETRYABLE |
| Other non-2xx, malformed success, wrong identity, invalid vectors or finish reason | NONE / TERMINAL |

`ModelResponseRetryableRejectedError` subclasses `ModelResponseRejectedError`;
composition classifies it before its terminal base class, for both chat and
embedding. No status causes retry or fallback. Redirects are rejected and ambient
proxies are disabled. No Authorization header, credential fields, environment
secret lookup, new dependency or provider SDK is used. Constructor/host open
perform no HTTP; only chat/embed perform I/O.

Offline conformance rows A-C use the same governed application with a FixedModel
contribution, Ollama over mocked HTTP, and OpenAI-compatible over a process-local
stdlib server. They test contracts and effects, not output-quality equivalence.
The Ollama protocol and configured-identity behavior remain unchanged; capability
IDs/version are shared neutral helpers, with separate provider plugin identities.

Locally qualified scope: credential-free LOCAL OpenAI-compatible endpoints. Remote,
credentials, KISSKI hosted, authenticated vLLM, cloud APIs, automatic routing,
retries and VTO remain unsupported. The existing blocking-to-thread cancellation
and complete-response buffering limitations remain; cancellation does not prove
provider cessation. No live endpoint is qualified by these tests. The next
separately authorized slice is SECRET-REF-1;
REMOTE-MODEL-DISCLOSURE-1 is also required before remote use.

Run from the repository root using installed project environments:

```powershell
uv run python .\validate_openai_compatible_model_1.py
```

The validator has 52 phases: scope and accepted ADR; public settings and closed
union; deployment/credential controls; neutral offers; private adapter and stdlib
boundaries; inert construction; chat wire, identity, usage and truncation;
HTTP/effect matrix; embeddings and purposes; no retry/fallback; conformance A-C;
runtime/Model/Agent/DocuMind/ForgeAI regressions; mypy, Ruff and diff checks.
It makes no provider connection beyond the process-local scripted server.

Implementation verification (2026-10-07): the offline 52-phase validator run
passed, including 88 runtime, 100 Model, 53 Agent, 16 DocuMind and 89 ForgeAI
regressions. Final focused verification passed all 161 new tests after tightening
malformed-JSON diagnostic isolation and identity/construction tests. Operator
qualification is now **LOCALLY QUALIFIED**: running
`uv run python .\validate_openai_compatible_model_1.py` from the repository root
passed **52/52 validator phases**, including conformance rows A–C. The 161 focused
tests had already passed during implementation verification. Qualification is
offline/process-local contract and conformance evidence only. No external or live
provider was contacted, no Docker was invoked, and no remote endpoint or
credentialed provider was used. No live model quality was measured or live
output-quality equivalence established; remote/credential support remains absent.
