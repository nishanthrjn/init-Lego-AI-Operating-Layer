# Foundational ports and adapters

This iteration reuses existing contracts rather than introducing another runtime.
Application logic accepts a `ModelPort` through constructor injection; concrete
wiring supplies `OllamaModelAdapter` or the offline `FixedModel`.
See [model_port.py](../examples/model_port.py) for a runnable offline example:
`uv run --locked python examples/model_port.py`.

## Public contracts and composition

- `legoai.intelligence.model.ports.ModelPort` retains async `chat` and `embed`.
  ChatRequest/ChatResult and embedding values are immutable, provider-neutral
  contracts. Embedding already exists for DocuMind; this iteration adds no capability.
- `legoai.reference.model_fake.FixedModel` accepts explicit fixture results and
  exposes per-instance call counts. It does no I/O and retains no request text.
  Missing embedding fixtures fail before effects; a wrong vector count rejects
  the fixture. Instantiate separately for each test; it is not a live provider.
- `OllamaModelConfig` remains explicit and immutable. Supply endpoint, model
  identities and a finite positive timeout at the composition root. No environment
  variables are read implicitly. Endpoints use ASCII HTTP(S) URLs and cannot carry credentials, query strings
  or fragments. Authenticated provider support requires the existing governed
  Secret-reference design; do not put credentials into these fields.
- Invalid configuration raises TypeError consistently with existing constructors.
  ModelPreflightError means demonstrably no send; ModelResponseUncertainError
  preserves ambiguous effects; ModelResponseRejectedError denotes an unusable
  complete response. No automatic retry occurs. Error messages omit provider error
  bodies; chained transport causes are restricted diagnostics, not safe user output.

The example is an offline dependency-injection demonstration, not an authorized
live execution path. Production calls keep the existing governed Chat composition
in `legoai.runtime._composition.model_governed`; constructor injection grants no
authority. Model contracts never import their adapters.

## Bound governed execution (ADR-026)

`legoai.runtime.api.GovernedExecutionConfig` contains trusted operator bootstrap
values. `legoai.runtime.local.open_governed_execution(config)` returns the concrete
`GovernedExecution` facade. Runtime owns their integration semantics; Model and
Generative Media are the two intended invoking-plane consumers. Private controls
can change without changing owner request/result contracts. There is one reference
realization, so no new Protocol or parallel contribution/context model is added.

The config pins one configuration revision, Principal, policy, independent
`OperatorGrant`, `PluginDeclaration` and exact `CapabilityOffer`. Opening is an
explicit trusted operator admission act using existing Plugin lifecycle and Catalog
controls, not permission inferred from a declaration. The initial closed profile
selects only v1 Model chat/embedding and media text-to-image/virtual-try-on offers.
A declaration may describe 1–4 offers and no dependencies; only the exact selected
offer is published by this handle. It loads no code or provider.

The owner calls `establish()`, `coordinate(context)`, then
`claim(context, ready, configuration=..., contribution=...)` with the pinned
configuration and Catalog entry exposed by the handle. Claim rechecks current
authorization, expiry/deadline and publication, then consumes the existing
coordinator's one-shot invocation guard. Copied/foreign contexts and receipts are
rejected; the originating objects are retained as process-local lineage. Operator
`revoke_authority()` and `retire_contribution()` invalidate only this handle's
bound grant/publication; neither can replace or widen the binding.

Invocation is **owner code outside the facade**. `settle(context, observed)` takes
canonical `ExecutionResult` facts from the trusted invoking owner, after claim,
and validates lineage and terminal transition. Model response meaning, media job
state, uploads/disclosure, retrieval and retention stay outside Core. UNKNOWN is
preserved; deadlines/cancellation/absent receipts never establish effect NONE.
An accepted local claim is not exactly-once remote execution or authority for a
subsequent protected send. Untrusted model/task output must never settle directly.

All state is finite and process-local: 1–100,000 lifetime contexts, execution
timeout greater than zero and at most one day, preparation timeout at most 60
seconds and shutdown timeout at most 30 seconds (both positive). Exhaustion fails
closed; settlement does not release capacity or evict claim history. Preparation
uses the existing coordinator supervisor with a bounded timeout. Cancellation
cleanup still depends on cooperative local controls; bounded close reports any
preparation that has not ceased instead of pretending it finished.

`await close()` stops new contexts/coordination/claims, cancels active preparation,
and waits only within the configured shutdown bound. It returns canonical
ExecutionIds for still-preparing or READY/unsettled executions. These are control
obligations, not invented effect results. Owner invocations are not supervised or
cancelled here; their caller retains that duty. Late `settle` remains available,
as does repeated close. Retain this handle and owner custody until unresolved
obligations are discharged; no durable restart/recovery guarantee is added.

The realization is single-operator, explicit-tenant, trusted-process and confined
to its opening thread and first async event loop. It is not hostile-plugin
isolation or multi-tenant IAM. The facade grants no Secret-use, provider-access,
image-disclosure or transport authority and offers no generic callbacks, dispatch
or workflow hosting. Closed `HostFailure` additions describe closed handles,
duplicate claims, wrong state, unauthorized claims and expired deadlines.

Existing Model `GovernedHost` behavior is unchanged. Generative Media has **not**
migrated: M-01 stays open until `GENERATIVE-MEDIA-PUBLIC-EXECUTION-MIGRATION-1`.
H-01 remains open, ADR-027 remains Proposed, and remote VTO remains unsupported.
`GOVERNED-EXECUTION-PUBLIC-FACADE-1` is implemented with maintainer validation
pending; no live or credentialed media is qualified.

## Persistence boundary

The existing domain-specific repository is
`legoai.application.ports.ConfigurationStorePort`: scoped immutable revision
reads, expected-revision publication, operation reconciliation and outstanding
duties. Use `SQLiteConfigurationStore` for durable reference persistence.
`tests/support/configuration_store.py:InMemoryConfigurationStore` is the
deterministic test implementation, included in the source distribution, deliberately
not shipped as a production fallback in the wheel. Shared
`tests/contract/test_configuration_store.py` vectors run against both.
Consumers can reuse those vectors from the source distribution when implementing
another adapter. The fake is single-threaded and non-durable.

No universal CRUD interface or second persistence model is needed. Existing
configuration composition captures explicit inputs into revision-bound effective
values; no global mutable configuration is introduced.

## Governing requirements and limits

This implements intent's Ports & Adapters/AI-optional principles and IA-001;
SPEC §4.12 and §10; ADR-001/002 (Python and dependency ownership), ADR-003
(explicit configuration), ADR-004 (durable owner-local state), ADR-015
(effect uncertainty), and ADR-016 (reusable Python delivery). Secret material
remains outside public contracts (SEC-057–059); tests support CONF-021
(adapter substitution) and CONF-062 (visible evidence scope).
Evaluation evidence is not authorization or a general conformance certification.

The existing urllib timeout bounds blocking socket operations, not total
generation time. Cancelling the awaiting coroutine does not stop its worker or
prove no provider effect. Responses remain buffered; transport allocation,
generation tokens/cost, bounded worker supervision and live-provider qualification
are outside this increment. Broader deployment requires that resource/supervision
work before claiming bounded end-to-end operation.

No streaming, tools, new embedding features, Agent/Workflow/plugin machinery,
registry, retries, fallback, DI framework or runtime dependency is added.
