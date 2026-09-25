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

Use capture_model_selection, then compose_model in the private
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
