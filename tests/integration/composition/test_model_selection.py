"""Configuration substitution through real admission, resolution and execution.

Transport is mocked. These vectors prove an offline application contract, not
live model quality, latency, cost or general behavioral equivalence.
"""

import asyncio
import json
import subprocess
import sys
import urllib.error
from dataclasses import replace
from unittest.mock import patch

import pytest

from legoai.capabilities.ports import CatalogPublicationError
from legoai.capabilities.values import CapabilityRequirement, CapabilityVersionRange
from legoai.execution.ports import ExecutionTransitionError
from legoai.execution.values import ExecutionState
from legoai.intelligence.model.ports import ModelPort
from legoai.intelligence.model.routing import ModelBinding, ModelRequirement
from legoai.intelligence.model.values import (
    ChatMessage,
    ChatRequest,
    ChatResult,
    ChatRole,
    ModelId,
    ProviderId,
)
from legoai.kernel.effects import EffectExtent
from legoai.kernel.references import ConfigurationRevisionRef
from legoai.kernel.versions import Version
from legoai.plugins.ports import PluginAdmissionId, PluginLifecycleState
from legoai.plugins.values import PluginId
from legoai.reference.model import (
    OllamaModelAdapter,
    OllamaModelConfig,
    ollama_chat_capability_id,
    ollama_declaration,
)
from legoai.reference.model_fake import FixedModel
from legoai.reference.plugins import activate, admit, initialize, inspect, validate
from legoai.runtime._composition.model_governed import invoke_routed_chat
from legoai.runtime._composition.model_selection import (
    CompositionFailure,
    DesiredModelBinding,
    ModelCompositionError,
    ModelContribution,
    capture_model_selection,
    compose_model,
)
from tests.integration.composition.test_model_governed import (
    _EPOCH,
    _Environment,
    _target,
)
from tests.support.execution import ImmediateSecurityContextResolver
from tests.unit.reference.test_model import _FakeResponse

_REQUIREMENT = CapabilityRequirement(
    ollama_chat_capability_id(), CapabilityVersionRange(Version(1, 0, 0))
)
_PROFILE = ModelRequirement("classification")
_REVISION = ConfigurationRevisionRef(_target(), "composition-1", Version(1, 0, 0))
_CONTENT = '{"category":"application_received"}'


def _world() -> tuple[_Environment, tuple[ModelContribution, ...]]:
    env = _Environment()
    contributions: list[ModelContribution] = []
    for name in ("offline", "ollama"):
        declaration = ollama_declaration()
        if name == "offline":
            declaration = replace(
                declaration, plugin_id=PluginId("legoai.test", "fixed-classification")
            )
        validation = validate(inspect(declaration), declaration, evaluated_at=_EPOCH)
        activation = activate(
            initialize(
                admit(
                    validation,
                    env.chat_entry.tenant_context,
                    PluginAdmissionId("admission-" + name),
                    established_at=_EPOCH,
                ),
                established_at=_EPOCH,
            ),
            established_at=_EPOCH,
        )
        entry = (
            env.chat_entry
            if name == "ollama"
            else env.catalog.publish(
                activation, declaration, declaration.offers[0], established_at=_EPOCH
            )
        )
        binding = ModelBinding(
            name, _PROFILE, ModelId("fixture-chat"), ProviderId(name)
        )
        if name == "offline":

            def make_fixed() -> ModelPort:
                return FixedModel(
                    ChatResult(
                        _CONTENT, ModelId("fixture-chat"), ProviderId("offline"), None
                    )
                )

            construct = make_fixed
        else:

            def make_ollama() -> ModelPort:
                return OllamaModelAdapter(
                    OllamaModelConfig(
                        base_url="http://127.0.0.1:11434",
                        chat_model="fixture-chat",
                        embedding_model="unused",
                        timeout_seconds=1.0,
                    ),
                    ProviderId("ollama"),
                )

            construct = make_ollama
        contributions.append(
            ModelContribution(_REVISION, binding, entry, activation, construct)
        )
    return env, tuple(contributions)


def _selection(binding: str = "offline") -> DesiredModelBinding:
    return capture_model_selection(
        {"revision": _REVISION.revision, "binding": binding}, pinned_revision=_REVISION
    )


@pytest.mark.parametrize("binding", ["offline", "ollama"])
def test_same_consumer_different_configuration(binding: str) -> None:
    async def consumer() -> None:
        env, contributions = _world()
        selected = compose_model(
            _REQUIREMENT,
            _selection(binding),
            catalog=env.catalog,
            contributions=contributions,
            resolved_at=_EPOCH,
        )
        # Complete candidate set remains visible; explicit data selects one.
        assert len(selected.resolution.candidates) == 2
        assert (
            selected.activation
            == contributions[0 if binding == "offline" else 1].activation
        )
        expected_type = FixedModel if binding == "offline" else OllamaModelAdapter
        assert type(selected.configured.adapter) is expected_type
        coordinator = env.coordinator(
            ImmediateSecurityContextResolver(env.security_context(grant=env.grant()))
        )
        ready = await coordinator.coordinate(
            env.coordination_request(selected.configured.entry)
        )
        request = ChatRequest(
            (ChatMessage(ChatRole.USER, "Your application has been received."),)
        )
        with patch(
            "urllib.request.urlopen",
            return_value=_FakeResponse(
                {
                    "model": "fixture-chat",
                    "message": {"content": _CONTENT},
                }
            ),
        ) as transport:
            execution, result = await invoke_routed_chat(
                coordinator, ready, request, selected.route, selected.configured
            )
        assert execution.final_state is ExecutionState.SUCCEEDED
        assert execution.effect is EffectExtent.COMPLETED
        assert result is not None
        assert json.loads(result.content) == {"category": "application_received"}
        assert result.provider_identity == ProviderId(binding)
        assert transport.call_count == (1 if binding == "ollama" else 0)

    asyncio.run(consumer())


@pytest.mark.parametrize(
    ("case", "failure"),
    [
        ("unknown", CompositionFailure.UNKNOWN_BINDING),
        ("unavailable", CompositionFailure.UNAVAILABLE_PROVIDER),
        ("incompatible", CompositionFailure.INCOMPATIBLE_PROVIDER),
        ("disabled", CompositionFailure.INACTIVE_PLUGIN),
        ("unadmitted", CompositionFailure.UNAVAILABLE_PROVIDER),
        ("stale", CompositionFailure.STALE_CONFIGURATION),
        ("duplicate", CompositionFailure.INVALID_CONFIGURATION),
        ("dependency", CompositionFailure.MISSING_DEPENDENCY),
        ("initialization", CompositionFailure.INITIALIZATION_FAILURE),
        ("bad_port", CompositionFailure.INITIALIZATION_FAILURE),
    ],
)
def test_failure_before_invocation(case: str, failure: CompositionFailure) -> None:
    env, contributions = _world()
    desired = _selection()
    requirement = _REQUIREMENT
    calls: list[str] = []

    def constructor() -> ModelPort:
        calls.append(case)
        if case == "dependency":
            raise ModuleNotFoundError("private dependency diagnostic")
        if case == "initialization":
            raise RuntimeError("private initialization diagnostic")
        if case == "bad_port":
            return object()  # type: ignore[return-value]
        return contributions[1].construct()

    first = replace(contributions[0], construct=constructor)
    contributions = (first, contributions[1])
    if case == "unknown":
        desired = replace(desired, binding_id="not-installed")
    elif case in {"unavailable", "unadmitted"}:
        env.catalog.withdraw(
            first.entry.plugin_id,
            first.entry.release,
            first.entry.offer,
            first.entry.tenant_context,
        )
    elif case == "incompatible":
        requirement = replace(
            requirement, version_range=CapabilityVersionRange(Version(2, 0, 0))
        )
    elif case == "disabled":
        state = (
            PluginLifecycleState.STOPPED
            if case == "disabled"
            else PluginLifecycleState.VALIDATED
        )
        contributions = (
            replace(first, activation=replace(first.activation, state=state)),
        )
    elif case == "stale":
        desired = replace(
            desired, configuration_revision=replace(_REVISION, revision="other")
        )
    elif case == "duplicate":
        contributions = (first, first)
    with pytest.raises(ModelCompositionError) as caught:
        compose_model(
            requirement,
            desired,
            catalog=env.catalog,
            contributions=contributions,
            resolved_at=_EPOCH,
        )
    assert caught.value.failure is failure
    assert "private" not in str(caught.value)
    assert len(calls) == (
        1 if case in {"dependency", "initialization", "bad_port"} else 0
    )


@pytest.mark.parametrize(
    "extra",
    ["python_class", "module", "secret", "secret_reference", "tenant", "admission"],
)
def test_configuration_cannot_load_code_or_supply_authority_or_secrets(
    extra: str,
) -> None:
    with pytest.raises(ModelCompositionError) as caught:
        capture_model_selection(
            {"revision": _REVISION.revision, "binding": "offline", extra: "untrusted"},
            pinned_revision=_REVISION,
        )
    assert caught.value.failure is CompositionFailure.INVALID_CONFIGURATION


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"binding": ""},
        {"binding": 1, "revision": "composition-1"},
        {"binding": "", "revision": "composition-1"},
        {"binding": "x" * 257, "revision": "composition-1"},
    ],
)
def test_invalid_configuration(data: dict[str, object]) -> None:
    with pytest.raises(ModelCompositionError):
        capture_model_selection(data, pinned_revision=_REVISION)


def test_restart_recaptures_exact_pin_and_reconstructs_without_latest_substitution() -> (
    None
):
    encoded = json.dumps({"revision": _REVISION.revision, "binding": "offline"})
    adapters: list[ModelPort] = []
    for _ in range(2):
        env, contributions = _world()
        desired = capture_model_selection(
            json.loads(encoded), pinned_revision=_REVISION
        )
        composed = compose_model(
            _REQUIREMENT,
            desired,
            catalog=env.catalog,
            contributions=contributions,
            resolved_at=_EPOCH,
        )
        assert composed.configured.configuration_revision == _REVISION
        adapters.append(composed.configured.adapter)
    assert adapters[0] is not adapters[1]
    with pytest.raises(ModelCompositionError) as caught:
        capture_model_selection(
            json.loads(encoded),
            pinned_revision=replace(_REVISION, revision="composition-2"),
        )
    assert caught.value.failure is CompositionFailure.STALE_CONFIGURATION


def test_activation_from_another_admission_is_rejected() -> None:
    _, contributions = _world()
    with pytest.raises(ModelCompositionError) as caught:
        replace(contributions[0], activation=contributions[1].activation)
    assert caught.value.failure is CompositionFailure.ACTIVATION_MISMATCH


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("uncertain transport"),
        urllib.error.URLError(ConnectionRefusedError("not sent")),
    ],
)
def test_selected_provider_invocation_failure_retains_governed_effect(
    error: Exception,
) -> None:
    async def scenario() -> None:
        env, contributions = _world()
        composed = compose_model(
            _REQUIREMENT,
            _selection("ollama"),
            catalog=env.catalog,
            contributions=contributions,
            resolved_at=_EPOCH,
        )
        coordinator = env.coordinator(
            ImmediateSecurityContextResolver(env.security_context(grant=env.grant()))
        )
        ready = await coordinator.coordinate(
            env.coordination_request(composed.configured.entry)
        )
        with patch("urllib.request.urlopen", side_effect=error) as transport:
            execution, result = await invoke_routed_chat(
                coordinator,
                ready,
                ChatRequest((ChatMessage(ChatRole.USER, "classify"),)),
                composed.route,
                composed.configured,
            )
        assert result is None
        assert execution.final_state is ExecutionState.FAILED
        assert execution.effect is (
            EffectExtent.UNKNOWN
            if isinstance(error, TimeoutError)
            else EffectExtent.NONE
        )
        assert transport.call_count == 1

    asyncio.run(scenario())


def test_restart_in_fresh_process_preserves_configuration_selection() -> None:
    script = """
import json, sys
from tests.integration.composition.test_model_selection import _world, _REVISION, _REQUIREMENT, _EPOCH
from legoai.runtime._composition.model_selection import capture_model_selection, compose_model
env, contributions = _world()
desired = capture_model_selection(json.loads(sys.stdin.read()), pinned_revision=_REVISION)
composed = compose_model(_REQUIREMENT, desired, catalog=env.catalog, contributions=contributions, resolved_at=_EPOCH)
print(json.dumps([composed.configured.configuration_revision.revision, composed.configured.binding.binding_id,
                 composed.configured.entry.plugin_id.local_id, composed.activation.admission_id.value]))
"""
    data = json.dumps({"revision": _REVISION.revision, "binding": "offline"})
    outputs = []
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, "-c", script],
            input=data,
            text=True,
            capture_output=True,
            timeout=20,
            check=True,
        )
        outputs.append(json.loads(result.stdout))
    assert (
        outputs
        == [
            [_REVISION.revision, "offline", "fixed-classification", "admission-offline"]
        ]
        * 2
    )


def test_validation_alone_cannot_publish_a_plugin() -> None:
    env, _ = _world()
    declaration = ollama_declaration()
    validation = validate(inspect(declaration), declaration, evaluated_at=_EPOCH)
    with pytest.raises(TypeError):
        env.catalog.publish(
            validation,  # type: ignore[arg-type]
            declaration,
            declaration.offers[0],
            established_at=_EPOCH,
        )
    # Even an existing admission that is not active is not publishable.
    inactive = admit(
        validation,
        env.chat_entry.tenant_context,
        PluginAdmissionId("new"),
        established_at=_EPOCH,
    )
    with pytest.raises(CatalogPublicationError):
        env.catalog.publish(
            inactive, declaration, declaration.offers[0], established_at=_EPOCH
        )


def test_cancellation_is_not_success_or_automatic_retry() -> None:
    async def scenario() -> None:
        env, contributions = _world()
        composed = compose_model(
            _REQUIREMENT,
            _selection(),
            catalog=env.catalog,
            contributions=contributions,
            resolved_at=_EPOCH,
        )
        coordinator = env.coordinator(
            ImmediateSecurityContextResolver(env.security_context(grant=env.grant()))
        )
        ready = await coordinator.coordinate(
            env.coordination_request(composed.configured.entry)
        )
        request = ChatRequest((ChatMessage(ChatRole.USER, "classify"),))
        with patch.object(
            FixedModel, "chat", side_effect=asyncio.CancelledError
        ) as chat:
            with pytest.raises(asyncio.CancelledError):
                await invoke_routed_chat(
                    coordinator, ready, request, composed.route, composed.configured
                )
            with pytest.raises(ExecutionTransitionError):
                await invoke_routed_chat(
                    coordinator, ready, request, composed.route, composed.configured
                )
        assert chat.await_count == 1

    asyncio.run(scenario())


def test_oversized_contribution_collection_is_rejected_before_construction() -> None:
    env, contributions = _world()
    with pytest.raises(ModelCompositionError) as caught:
        compose_model(
            _REQUIREMENT,
            _selection(),
            catalog=env.catalog,
            contributions=contributions * 129,
            resolved_at=_EPOCH,
        )
    assert caught.value.failure is CompositionFailure.INVALID_CONFIGURATION
