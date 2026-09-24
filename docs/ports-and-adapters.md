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
