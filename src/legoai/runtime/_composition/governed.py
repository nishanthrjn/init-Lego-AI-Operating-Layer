"""Gate-2 M11: private composition wiring for the first real governed
deterministic capability invocation.

This module -- not `legoai.reference.execution` -- is where the "known
Catalog-published capability identity corresponds to this one known trusted
implementation" correspondence actually lives, and where the deterministic
implementation's typed input/configuration is bound. Two ADR-002 rules force
this split:

  - SS9.2's E-row foreign-target maximum for `legoai.execution`/
    `legoai.reference.execution` is exactly "K, C, T, I, M, A(rtifacts), G,
    R, O, X, V" -- it does not include Application, so that module may never
    import `legoai.application.values` (`EffectiveConfiguration`).
  - SS9's "no reference owner implementation imports another reference
    owner implementation" separately forbids `legoai.reference.execution`
    importing `legoai.reference.deterministic` regardless.

`legoai.runtime._composition` is exactly the location ADR-002 SS9.2
authorizes to import "as needed" across owner values and "selected concrete
[reference] realizations" for wiring -- so the correspondence check and the
`EffectiveConfiguration`-typed call both belong here, not in the Execution
owner's own reference module.

**No generic provider registry.** `_KNOWN_TEXT_NORMALIZATION_ENTRY_MATCHES`
below is the one, narrow, statically-known correspondence this batch needs
("one known capability identity -> one known deterministic trusted
implementation" -- task's own framing). It is not a
`dict[CapabilityId, Callable]`, not a `ProviderRegistry`/`ServiceLocator`,
and not reusable infrastructure for a second capability; a later batch
introducing a second trusted implementation adds its own explicit
correspondence function then, not a generic lookup now.

**Trusted-host scope only.** The Catalog/Plugin declaration data is never
used to determine a Python import path, `eval`/`exec`/`compile` target, or
`importlib`/entry-point discovery input -- the *only* operation performed
against `CatalogEntry` fields here is an exact equality comparison against
this module's own statically-imported, hardcoded identity functions. A
resolved entry that does not match exactly is treated as
`ErrorCategory.DEPENDENCY_FAILURE` (the trusted host does not have the
implementation the resolution named), never as "close enough" and never by
attempting to load or execute anything derived from the entry's own data.
ADR-012 (Plugin isolation/sandboxing) remains completely unresolved and is
not claimed here in any way.
"""

from __future__ import annotations

from collections.abc import Callable

from legoai.application.values import EffectiveConfiguration
from legoai.capabilities.ports import CatalogEntry
from legoai.execution.ports import (
    CoordinationOutcome,
    CoordinationResult,
    GovernedInvocationResult,
)
from legoai.execution.values import ExecutionState
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory, ErrorDetail, Recoverability
from legoai.reference.deterministic import (
    normalize_text,
    text_normalization_offer,
    text_normalization_plugin_id,
    text_normalization_release,
)
from legoai.reference.execution import ExecutionCoordinator


def _known_text_normalization_entry_matches(entry: CatalogEntry) -> bool:
    """The one exact correspondence this batch needs: does the resolved
    Catalog entry name exactly the one Plugin/release/offer this trusted
    host actually implements? No approximate/partial/"similar enough"
    match is performed -- every field participates in the comparison.
    """
    return (
        entry.plugin_id == text_normalization_plugin_id()
        and entry.release == text_normalization_release()
        and entry.offer == text_normalization_offer()
    )


async def invoke_governed_text_normalization(
    coordinator: ExecutionCoordinator,
    result: CoordinationResult,
    text: str,
    effective: EffectiveConfiguration,
    *,
    implementation: Callable[[str, EffectiveConfiguration], str] | None = None,
) -> GovernedInvocationResult:
    """The narrow, explicitly-named M11 invocation boundary for exactly one
    capability (text normalization) -- never a generic `Executor`/
    `RuntimeEngine`/`ProviderManager`. Requires `result.outcome is READY`
    (via `coordinator.invoke_governed`/`settle`'s own structural
    enforcement); it never manufactures a permit or bypasses
    `DispatchArbiterPort`.

    `implementation` defaults to `legoai.reference.deterministic.
    normalize_text`; a caller may supply a different pure callable with the
    identical signature to prove substitutability or to count invocations
    in a test, exactly mirroring F8b's own established
    `compose_direct(normalization_function=...)` pattern -- never a second
    production implementation.

    Reuses the exact `effective` `EffectiveConfiguration` the caller
    already composed for this admitted Execution -- this function does not
    itself compose, fetch, or revalidate configuration currentness: no
    accepted M1-M10 governed-path type (`ExecutionContext`, `CatalogEntry`,
    `DispatchPermit`) carries a pinned `ConfigurationRef`/revision to check
    staleness against, so "configuration revision revalidation at
    invocation" is not implementable here without inventing a new field on
    an already-accepted immutable value. This is a documented residual
    gap, not a silent substitution: supplying a stale `effective` remains
    the caller's own responsibility in this first slice.
    """
    if type(result) is not CoordinationResult:
        raise TypeError(
            "invoke_governed_text_normalization requires CoordinationResult"
        )
    if result.outcome is not CoordinationOutcome.READY:
        raise ValueError(
            "invoke_governed_text_normalization requires a READY CoordinationResult"
        )
    permit = result.permit
    assert permit is not None  # CoordinationResult's own invariant guarantees this

    if not _known_text_normalization_entry_matches(permit.resolved_entry):
        execution_result = await coordinator.settle(
            result,
            final_state=ExecutionState.FAILED,
            effect=EffectExtent.NONE,
            error=ErrorDetail(
                ErrorCategory.DEPENDENCY_FAILURE, Recoverability.TERMINAL, ()
            ),
        )
        return GovernedInvocationResult(execution_result, None)

    active_implementation = (
        implementation if implementation is not None else normalize_text
    )
    return await coordinator.invoke_governed(
        result, lambda: active_implementation(text, effective)
    )
