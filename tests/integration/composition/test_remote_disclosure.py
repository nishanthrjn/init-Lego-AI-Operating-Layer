"""ADR-024 REMOTE-DISCLOSURE-GOVERNANCE-1: host configuration and open-time
validation. Disclosure configuration is validated for consistency only; it
enables nothing. REMOTE stays refused, LOCAL is unchanged, nothing is called.
"""

import dataclasses
from dataclasses import replace
from typing import Any
from unittest.mock import patch

import pytest

from legoai.governance.disclosure import DisclosureClass
from legoai.intelligence.model.values import ProviderId
from legoai.runtime.api import (
    GovernedHost,
    HostError,
    HostFailure,
    LocalHostConfig,
    ModelBindingConfig,
    ModelDeployment,
    ModelPurpose,
    OpenAICompatibleSettings,
    RemoteDisclosureConfig,
)
from legoai.runtime.local import open_local_host
from tests.integration.composition.test_local_host import (
    NOW,
    PROFILE,
    FakeModel,
    fake_binding,
    host_config,
    ollama_binding,
    selection,
)
from tests.unit.governance.test_disclosure import admission, declaration

REMOTE_URL = "https://models.example.org/v1"


def remote_settings(**changes: Any) -> OpenAICompatibleSettings:
    value = OpenAICompatibleSettings(
        REMOTE_URL,
        "model-a",
        None,
        5.0,
        None,
        ProviderId("remote-endpoint"),
        ModelDeployment.REMOTE,
    )
    return replace(value, **changes)


def remote_binding(**changes: Any) -> ModelBindingConfig:
    return ModelBindingConfig("remote", PROFILE, remote_settings(**changes))


def disclosure(**changes: Any) -> RemoteDisclosureConfig:
    value = RemoteDisclosureConfig((declaration(),), (admission(),))
    return replace(value, **changes)


def configured(
    *bindings: ModelBindingConfig, disclosure_config: RemoteDisclosureConfig | None
) -> LocalHostConfig:
    return replace(host_config(*bindings), disclosure=disclosure_config)


def open_with(config: LocalHostConfig, binding: str = "fake") -> GovernedHost:
    return open_local_host(config, selection(binding), clock=lambda: NOW)


# LOCAL is unchanged


def test_disclosure_is_optional_and_defaults_to_none() -> None:
    config = host_config(fake_binding(FakeModel()))
    assert config.disclosure is None
    field = {f.name: f for f in dataclasses.fields(LocalHostConfig)}["disclosure"]
    assert field.default is None
    open_with(config)  # existing LOCAL configuration opens unchanged


def test_valid_disclosure_with_local_selection_opens_inertly() -> None:
    config = configured(
        fake_binding(FakeModel()), remote_binding(), disclosure_config=disclosure()
    )
    with patch("urllib.request.OpenerDirector.open") as transport:
        host = open_with(config)
    transport.assert_not_called()
    # The LOCAL host is fully usable; disclosure config changed nothing for it.
    assert host.model_execution(ModelPurpose.CHAT).execution_id.value


def test_ollama_and_openai_local_do_not_need_disclosure() -> None:
    open_with(host_config(ollama_binding()), "ollama")
    local = ModelBindingConfig(
        "openai",
        PROFILE,
        remote_settings(
            base_url="http://127.0.0.1:8000/v1", deployment=ModelDeployment.LOCAL
        ),
    )
    open_with(host_config(local), "openai")


# REMOTE remains refused, however complete the disclosure configuration


def test_remote_still_refused_with_valid_declaration_and_admission() -> None:
    config = configured(remote_binding(), disclosure_config=disclosure())
    with (
        patch("legoai.runtime.local.admit") as admit,
        patch("legoai.runtime.local.OpenAICompatibleModelAdapter") as construct,
        patch("urllib.request.OpenerDirector.open") as transport,
        pytest.raises(HostError) as error,
    ):
        open_with(config, "remote")
    assert error.value.failure is HostFailure.UNSUPPORTED_COMPOSITION
    admit.assert_not_called()
    construct.assert_not_called()
    transport.assert_not_called()


def test_remote_still_refused_without_disclosure() -> None:
    with pytest.raises(HostError) as error:
        open_with(host_config(remote_binding()), "remote")
    assert error.value.failure is HostFailure.UNSUPPORTED_COMPOSITION


# Open-time consistency validation


@pytest.mark.parametrize(
    "build",
    [
        lambda: disclosure(admissions=(admission(declaration_id="missing"),)),
        lambda: disclosure(admissions=(admission(declaration_revision="r0"),)),
        lambda: disclosure(admissions=(admission(bindings=frozenset({"absent"})),)),
        lambda: disclosure(admissions=(admission(bindings=frozenset({"fake"})),)),
        lambda: disclosure(admissions=(admission(bindings=frozenset({"ollama"})),)),
        lambda: disclosure(
            admissions=(admission(bindings=frozenset({"local-openai"})),)
        ),
        lambda: disclosure(admissions=(admission(models=frozenset({"model-b"})),)),
        lambda: disclosure(
            admissions=(admission(purposes=frozenset({"chat", "embedding"})),)
        ),
        lambda: disclosure(admissions=(admission(purposes=frozenset({"summarize"})),)),
        lambda: disclosure(declarations=(declaration(provider_id="other"),)),
        lambda: disclosure(
            declarations=(declaration(endpoint_origin="https://elsewhere.example"),)
        ),
        lambda: disclosure(declarations=(declaration(api_root="/v2"),)),
    ],
    ids=[
        "declaration-missing",
        "declaration-revision",
        "binding-missing",
        "binding-trusted",
        "binding-ollama",
        "binding-local",
        "model-not-served",
        "embedding-unserved",
        "purpose-unknown",
        "declaration-provider",
        "declaration-endpoint",
        "declaration-api-root",
    ],
)
def test_inconsistent_disclosure_is_invalid_configuration(
    build: object,
) -> None:
    local_openai = ModelBindingConfig(
        "local-openai",
        PROFILE,
        remote_settings(deployment=ModelDeployment.LOCAL),
    )
    config = configured(
        fake_binding(FakeModel()),
        remote_binding(),
        ollama_binding(),
        local_openai,
        disclosure_config=build(),  # type: ignore[operator]
    )
    with pytest.raises(HostError) as error:
        open_with(config)
    assert error.value.failure is HostFailure.INVALID_CONFIGURATION


@pytest.mark.parametrize(
    "changes",
    [
        {"provider_id": ProviderId("other-endpoint")},
        {"base_url": "https://elsewhere.example.org/v1"},
        {"base_url": "https://models.example.org/v2"},
        {"base_url": "http://models.example.org/v1"},
    ],
    ids=["provider", "endpoint", "api-root", "plaintext"],
)
def test_binding_must_match_admission(changes: dict[str, object]) -> None:
    config = configured(
        fake_binding(FakeModel()),
        remote_binding(**changes),
        disclosure_config=disclosure(),
    )
    with pytest.raises(HostError) as error:
        open_with(config)
    assert error.value.failure is HostFailure.INVALID_CONFIGURATION


def test_structural_conflicts_and_bounds() -> None:
    twin_declaration = (declaration(), declaration())
    with pytest.raises(HostError) as error:
        RemoteDisclosureConfig(twin_declaration, (admission(),))
    assert error.value.failure is HostFailure.CONTRIBUTION_CONFLICT
    with pytest.raises(HostError) as error:
        RemoteDisclosureConfig((declaration(),), (admission(), admission()))
    assert error.value.failure is HostFailure.CONTRIBUTION_CONFLICT
    with pytest.raises(HostError) as error:  # two admissions for one binding
        RemoteDisclosureConfig(
            (declaration(),), (admission(), admission(admission_id="other"))
        )
    assert error.value.failure is HostFailure.CONTRIBUTION_CONFLICT
    for empty in ((), (admission(),)), ((declaration(),), ()):
        with pytest.raises(HostError) as error:
            RemoteDisclosureConfig(*empty)
        assert error.value.failure is HostFailure.INVALID_CONFIGURATION
    with pytest.raises(TypeError):
        RemoteDisclosureConfig([declaration()], (admission(),))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        replace(host_config(fake_binding(FakeModel())), disclosure=object())  # type: ignore[arg-type]


def test_synthetic_only_admission_is_valid_configuration() -> None:
    probe = admission(frozenset({DisclosureClass.SYNTHETIC}))
    config = configured(
        fake_binding(FakeModel()),
        remote_binding(),
        disclosure_config=disclosure(admissions=(probe,)),
    )
    open_with(config)


# Authority: nothing at runtime can create or widen an admission


def test_host_exposes_no_way_to_add_or_change_disclosure() -> None:
    members = {name for name in vars(GovernedHost) if not name.startswith("_")}
    for name in members:
        lowered = name.lower()
        assert not any(
            word in lowered for word in ("disclos", "admission", "declaration")
        ), name
    config = configured(remote_binding(), disclosure_config=disclosure())
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.disclosure = None  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        disclosure().admissions = ()  # type: ignore[misc]
