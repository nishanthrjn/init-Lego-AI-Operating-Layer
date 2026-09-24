# Model routing — M6.5

**LOCAL VALIDATION COMPLETE** — user-supplied evidence: 1,425 Core tests,
two DocuMind tests, mypy/lint/format, build/fresh install and example passed.

Future consumers request a logical Chat profile such as
`ModelRequirement("engineering-reasoning")`. They do not select provider names
or construct clients. Routing selects configuration; governed execution decides
whether a call is allowed; ModelPort and its adapter perform the call.

## Contract

Import ModelBinding, ModelRequirement, ModelRouteStatus and ModelRouteDecision
from `legoai.intelligence.model.routing`, and ModelRouterPort from
`legoai.intelligence.model.ports`. DeterministicModelRouter lives in
`legoai.reference.model_routing`.

- A binding contains a binding ID, logical requirement, ModelId and ProviderId.
  These are inert configured expectations, not live clients or health evidence.
  ModelId and ProviderId retain their existing meanings on observed ChatResult.
- A router takes one explicit ConfigurationRevisionRef and an immutable tuple
  of 0–256 bindings. Duplicate binding IDs, including identical duplicates, fail.
- Profiles and binding IDs are exact built-in strings of 1–256 code points;
  blank labels fail. Matching is case-sensitive, without normalization.
- `route(requirement, tenant_context)` requires explicit matching tenant scope.
  Zero matches return NO_MATCH, one RESOLVED, multiple AMBIGUOUS. Candidates
  retain configuration order, which never implies preference. `selected` is
  None unless exactly one match exists. Status is derived, not independently set.
- Values and router are frozen/slotted with strict construction validation.
  Invalid types/configuration raise TypeError/ValueError; misses are normal results.
  Routing performs no I/O, model call, authorization, health query or discovery.

Only Chat is routed. Existing ChatRequest/Result, EmbeddingRequest/Result,
ModelUsage, ModelPort and model phase exceptions are unchanged. No model-quality,
cost, latency, context-window, vision, structured-output or tool-calling ranking
is provided. There are no priorities, retries, default providers or fallback.

## Pins and governed composition

The decision retains its exact revision, requirement and complete matching
bindings. The operator supplies immutable configuration and must allocate a new
revision for changed meaning. Constructing a reference does not publish it.
ConfigurationStorePort remains the existing normalization-specific store;
routing neither uses it nor introduces a replacement configuration service.

Private `runtime._composition.model_governed.ConfiguredModelBinding` connects
one revision and selected binding to an exact CatalogEntry and an already
configured ModelPort. Unlike the public routing data, this runtime association
owns an adapter reference. It is trusted operator wiring, not an Agent-facing
service locator or public authoring facade.

`invoke_routed_chat` checks the decision's revision and full selected binding,
the permit's exact catalog entry and configuration subject. Tenant scope and the
existing v1 `legoai.intelligence.model.chat` offer are validated by the association.
Mismatches fail before any provider call. It then uses the **same** invocation
claim, phase mapping and settlement implementation as existing governed Chat:
preflight failure NONE; uncertain response UNKNOWN; complete rejected response
NONE; success COMPLETED. Response identities must match the configured expectation;
a mismatch is rejected without retry or fallback. The extent describes the
existing usable-result contract, not proof of zero provider cost or disclosure.

Catalog resolution, Plugin admission, authorization and dispatch remain separate.
The integration test exercises them before invocation with a fake ModelPort,
including a different admitted Plugin supplying the same Chat contract. No new
provider implementation or multi-provider production qualification is claimed.

No mutable adapter registry is consulted after selection. Existing associations
retain their adapter reference; replacing configuration creates new associations.
The trusted operator must not mutate an adapter's configuration behind a binding.
This does not attest hostile Python code, provider truthfulness, or immutable
weights behind a mutable model alias. Existing in-process replay, cancellation,
durability and dispatch-to-invocation currentness limits remain unchanged.
Routing is not a new execution supervisor or an authorization token.

Routing data has no credential, endpoint, callable, session or metadata field.
Operator labels/IDs must not be used to smuggle secret material; opaque strings
cannot prove whether their contents are sensitive. Credentials remain a future
qualified adapter/composition concern. No Evidence is automatically created.

## Local validation required

Run from the repository root and stop on any nonzero exit. These commands follow
the existing [Core workflow](development.md#commands). None were run internally.

```powershell
uv sync --locked --group dev --no-install-project
uv sync --locked --group dev --no-build-isolation

# Focused M6.5 contracts and architecture
uv run --locked --no-sync python -m pytest -q tests/unit/reference/test_model_routing.py tests/architecture/test_model_routing.py
# Existing Model and governed integration, including routed Chat
uv run --locked --no-sync python -m pytest -q tests/unit/intelligence/test_model_values.py tests/unit/reference/test_model.py tests/integration/composition/test_model_governed.py
# Full applicable Core suite, including wheel/sdist and fresh offline installation
uv run --locked --no-sync python -m pytest
uv run --locked --no-sync python -m mypy src tests examples/model_routing.py
uv run --locked --no-sync ruff check .
uv run --locked --no-sync ruff format --check .
uv build --no-build-isolation
uv run --locked --no-sync python examples/model_routing.py
git diff --check
```

The full suite's `tests/architecture/test_package_install.py` builds wheel/sdist,
checks exact inventories, installs the wheel offline into a fresh environment,
and exercises routing, governed invocation and the example outside the checkout.
It is the install qualification; a source import alone is insufficient.

Shared Chat invocation code changed, so require the existing DocuMind regression
against its fake HTTP boundary. No live Ollama is needed:

```powershell
Push-Location examples/documind
try {
    uv sync --locked --group dev --no-install-project
    if ($LASTEXITCODE -ne 0) { throw 'DocuMind dependency sync failed' }
    uv sync --locked --group dev --no-build-isolation
    if ($LASTEXITCODE -ne 0) { throw 'DocuMind sync failed' }
    uv run --locked --no-sync python -m pytest -q tests/integration/test_end_to_end.py
    if ($LASTEXITCODE -ne 0) { throw 'DocuMind regression failed' }
} finally {
    Pop-Location
}
```

Expected: focused and existing tests pass, Core suite/build/fresh install pass,
mypy/Ruff/format clean, and no skipped M6.5 semantics. Example output:

```text
engineering-reasoning: resolved
reasoning-local: demo-provider/demo-model
configuration: r1
```

Engineering/M6 source, dependencies and boundary tests are untouched, so its
Docker suite is not required. Document Pack source is untouched; DocuMind's
end-to-end regression covers its integration with the shared Chat path.
No separate full Document Pack run is required for this change.
M7 now consumes these contracts; its separate qualification is recorded in agent.md.
