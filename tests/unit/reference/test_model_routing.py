"""M6.5 exact-profile selection, invalid configuration and immutable pins."""

from dataclasses import FrozenInstanceError, replace

import pytest

from legoai.intelligence.model.ports import ModelRouterPort
from legoai.intelligence.model.routing import (
    ModelBinding,
    ModelRequirement,
    ModelRouteDecision,
    ModelRouteStatus,
)
from legoai.intelligence.model.values import ModelId, ProviderId
from legoai.kernel.context import TenantContext
from legoai.kernel.identity import ApplicationId, TenantId
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.reference.model_routing import DeterministicModelRouter


def _revision(value: str = "r1") -> ConfigurationRevisionRef:
    return ConfigurationRevisionRef(
        ConfigurationRef(
            ApplicationRef(
                ReferenceScope("operator", TenantId("tenant")), ApplicationId("app")
            ),
            "models",
        ),
        value,
        Version(1, 0, 0),
    )


def _binding(name: str = "z") -> ModelBinding:
    return ModelBinding(
        name,
        ModelRequirement("engineering-reasoning"),
        ModelId(f"model-{name}"),
        ProviderId(f"provider-{name}"),
    )


def test_unique_route_through_contract_is_provider_independent() -> None:
    binding = _binding()
    router: ModelRouterPort = DeterministicModelRouter(_revision(), (binding,))
    decision = router.route(binding.requirement, TenantContext(TenantId("tenant")))
    assert decision.status is ModelRouteStatus.RESOLVED
    assert decision.selected == binding
    assert decision.configuration_revision == _revision()


@pytest.mark.parametrize("bindings", [(), (_binding(),)])
def test_no_match_has_no_default(bindings: tuple[ModelBinding, ...]) -> None:
    decision = DeterministicModelRouter(_revision(), bindings).route(
        ModelRequirement("Engineering-Reasoning"), TenantContext(TenantId("tenant"))
    )
    assert decision.status is ModelRouteStatus.NO_MATCH
    assert decision.candidates == ()
    assert decision.selected is None
    assert decision.configuration_revision == _revision()


def test_ambiguity_preserves_configuration_order_without_preference() -> None:
    first, second = _binding("z"), _binding("a")
    unrelated = replace(_binding("other"), requirement=ModelRequirement("other"))
    router = DeterministicModelRouter(_revision(), (first, unrelated, second))
    tenant = TenantContext(TenantId("tenant"))
    decision = router.route(first.requirement, tenant)
    assert decision == router.route(first.requirement, tenant)
    assert decision.status is ModelRouteStatus.AMBIGUOUS
    assert decision.candidates == (first, second)
    assert decision.selected is None
    reversed_decision = replace(router, bindings=(second, first)).route(
        first.requirement, tenant
    )
    assert reversed_decision.candidates == (second, first)
    assert reversed_decision.selected is None


@pytest.mark.parametrize("changed", [False, True])
def test_duplicate_binding_identity_is_rejected(changed: bool) -> None:
    binding = _binding()
    duplicate = replace(binding, model_id=ModelId("other")) if changed else binding
    with pytest.raises(ValueError, match="duplicate"):
        DeterministicModelRouter(_revision(), (binding, duplicate))
    with pytest.raises(ValueError, match="duplicate"):
        ModelRouteDecision(binding.requirement, _revision(), (binding, duplicate))


def test_new_configuration_does_not_change_old_decision() -> None:
    original = _binding()
    router = DeterministicModelRouter(_revision(), (original,))
    tenant = TenantContext(TenantId("tenant"))
    old = router.route(original.requirement, tenant)
    replacement = replace(original, model_id=ModelId("replacement"))
    new = DeterministicModelRouter(_revision("r2"), (replacement,)).route(
        original.requirement, tenant
    )
    assert old.selected == original
    assert old.configuration_revision == _revision("r1")
    assert new.selected == replacement
    assert new.configuration_revision == _revision("r2")
    for value, attribute in (
        (original, "model_id"),
        (original.requirement, "profile"),
        (router, "bindings"),
        (old, "candidates"),
    ):
        assert not hasattr(value, "__dict__")
        with pytest.raises(FrozenInstanceError):
            setattr(value, attribute, None)


def test_tenant_is_explicit_and_never_inferred() -> None:
    router = DeterministicModelRouter(_revision(), (_binding(),))
    with pytest.raises(ValueError, match="tenant"):
        router.route(_binding().requirement, TenantContext(TenantId("other")))
    with pytest.raises(TypeError, match="TenantContext"):
        router.route(_binding().requirement, None)  # type: ignore[arg-type]


def test_configuration_and_decision_validate_exact_types_and_scope() -> None:
    binding = _binding()
    with pytest.raises(TypeError):
        DeterministicModelRouter(_revision(), [binding])  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        DeterministicModelRouter(_revision(), (object(),))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        DeterministicModelRouter("r1", ())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        replace(binding, model_id="model")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        replace(binding, provider_id="provider")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        replace(binding, requirement="profile")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="match"):
        ModelRouteDecision(ModelRequirement("other"), _revision(), (binding,))
    with pytest.raises(TypeError):
        DeterministicModelRouter(_revision(), ()).route(
            "profile", TenantContext(TenantId("tenant"))  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("label", ["", " ", "x" * 257])
def test_invalid_logical_labels_are_rejected(label: str) -> None:
    with pytest.raises(ValueError):
        ModelRequirement(label)
    with pytest.raises(ValueError):
        replace(_binding(), binding_id=label)


def test_configuration_size_is_bounded() -> None:
    bindings = tuple(_binding(str(index)) for index in range(256))
    assert len(DeterministicModelRouter(_revision(), bindings).bindings) == 256
    with pytest.raises(ValueError, match="256"):
        DeterministicModelRouter(_revision(), (*bindings, _binding("extra")))
