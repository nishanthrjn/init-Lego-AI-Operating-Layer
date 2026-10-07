"""Closed host composition and offline provider-portability rows A-C."""

import asyncio
import dataclasses
import inspect
from unittest.mock import patch

import pytest

from legoai.execution.ports import ExecutionTransitionError
from legoai.execution.values import ExecutionState
from legoai.intelligence.model.ports import (
    ModelPreflightError,
    ModelResponseRejectedError,
    ModelResponseRetryableRejectedError,
    ModelResponseUncertainError,
)
from legoai.intelligence.model.values import (
    ChatResult,
    EmbeddingRequest,
    EmbeddingResult,
    ModelId,
    ProviderId,
)
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory, Recoverability
from legoai.kernel.versions import Version
from legoai.plugins.values import PluginId
from legoai.reference.model import ollama_declaration, ollama_plugin_id, ollama_release
from legoai.reference.model_capabilities import (
    model_capability_version,
    model_chat_offer,
    model_embedding_offer,
)
from legoai.reference.model_fake import FixedModel
from legoai.reference.model_openai_compatible import (
    OpenAICompatibleModelAdapter,
    openai_compatible_declaration,
)
from legoai.runtime.api import (
    GovernedHost,
    HostError,
    HostFailure,
    ModelBindingConfig,
    ModelDeployment,
    ModelPurpose,
    OllamaSettings,
    OpenAICompatibleSettings,
    TrustedModelContribution,
)
from legoai.runtime.local import open_local_host
from tests.integration.composition.test_local_host import (
    NOW,
    PROFILE,
    FakeModel,
    chat_request,
    fake_binding,
    host_config,
    selection,
)
from tests.support.openai_http import Script, chat_payload, embedding_payload, server
from tests.unit.reference.test_model import _FakeResponse


def settings(url: str = "http://127.0.0.1:8000/v1") -> OpenAICompatibleSettings:
    return OpenAICompatibleSettings(
        url,
        "chat-model",
        None,
        1.0,
        None,
        ProviderId("endpoint"),
        ModelDeployment.LOCAL,
    )


def binding(config: OpenAICompatibleSettings) -> ModelBindingConfig:
    return ModelBindingConfig("openai", PROFILE, config)


def open_provider(config: OpenAICompatibleSettings) -> GovernedHost:
    return open_local_host(
        host_config(binding(config)), selection("openai"), clock=lambda: NOW
    )


def test_public_settings_types_and_required_deployment() -> None:
    config = settings()
    assert not hasattr(config, "__dict__")
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.chat_model = "changed"
    assert (
        inspect.signature(OpenAICompatibleSettings).parameters["deployment"].default
        is inspect.Parameter.empty
    )
    assert set(ModelDeployment) == {ModelDeployment.LOCAL, ModelDeployment.REMOTE}
    assert set(f.name for f in dataclasses.fields(config)) == {
        "base_url",
        "chat_model",
        "embedding_model",
        "timeout_seconds",
        "max_output_tokens",
        "provider_id",
        "deployment",
    }
    assert config.base_url not in repr(config)
    assert set(f.name for f in dataclasses.fields(OllamaSettings)) == {
        "base_url",
        "chat_model",
        "embedding_model",
        "timeout_seconds",
        "provider_id",
    }


@pytest.mark.parametrize(
    "name, value",
    [
        ("base_url", ""),
        ("base_url", "file:///tmp"),
        ("base_url", "http://u:p@localhost/v1"),
        ("base_url", "http://localhost:0/v1"),
        ("base_url", "http://localhost/v1?q=x"),
        ("base_url", "http://localhost/v1#fragment"),
        ("base_url", "http://localhost:bad/v1"),
        ("base_url", "http://local host/v1"),
        ("base_url", "http://localhost/\x7f"),
        ("chat_model", ""),
        ("chat_model", " "),
        ("chat_model", "x" * 257),
        ("chat_model", "x\nx"),
        ("embedding_model", ""),
        ("embedding_model", "\t"),
        ("timeout_seconds", 0),
        ("timeout_seconds", -1),
        ("timeout_seconds", float("nan")),
        ("timeout_seconds", float("inf")),
        ("max_output_tokens", 0),
        ("max_output_tokens", -1),
        ("max_output_tokens", 2**31),
    ],
)
def test_invalid_settings_at_open(name: str, value: object) -> None:
    with pytest.raises(HostError) as error:
        open_provider(dataclasses.replace(settings(), **{name: value}))
    assert error.value.failure is HostFailure.INVALID_CONFIGURATION


@pytest.mark.parametrize(
    "name, value",
    [
        ("base_url", 1),
        ("chat_model", None),
        ("embedding_model", False),
        ("timeout_seconds", True),
        ("max_output_tokens", True),
        ("max_output_tokens", 1.0),
        ("provider_id", "endpoint"),
        ("deployment", "local"),
        ("deployment", None),
    ],
)
def test_wrong_settings_types(name: str, value: object) -> None:
    with pytest.raises(TypeError):
        dataclasses.replace(settings(), **{name: value})


def test_provider_union() -> None:
    assert binding(settings()).provider == settings()
    with pytest.raises(TypeError):
        ModelBindingConfig("bad", PROFILE, object())
    with pytest.raises(ValueError):
        ProviderId("")


def test_remote_refused_before_admission_or_construction() -> None:
    with (
        patch("legoai.runtime.local.admit") as admit,
        patch("legoai.runtime.local.OpenAICompatibleModelAdapter") as construct,
        patch("urllib.request.OpenerDirector.open") as transport,
        pytest.raises(HostError) as error,
    ):
        open_provider(
            dataclasses.replace(settings(), deployment=ModelDeployment.REMOTE)
        )
    assert error.value.failure is HostFailure.UNSUPPORTED_COMPOSITION
    admit.assert_not_called()
    construct.assert_not_called()
    transport.assert_not_called()


def test_local_attestation_not_hostname_and_inert_open() -> None:
    with patch("urllib.request.OpenerDirector.open") as transport:
        open_provider(settings("https://operator-declared-local.example/v1"))
    transport.assert_not_called()


def test_selected_adapter_constructed_once() -> None:
    script = Script(chat_payload())
    with (
        server(script) as url,
        patch(
            "legoai.runtime.local.OpenAICompatibleModelAdapter",
            wraps=OpenAICompatibleModelAdapter,
        ) as construct,
    ):
        host = open_provider(settings(url))
        assert construct.call_count == 1 and not script.requests

        async def scenario() -> None:
            for _ in range(2):
                result = await host.governed_chat(
                    host.model_execution(ModelPurpose.CHAT), chat_request()
                )
                assert result.response is not None

        asyncio.run(scenario())
        assert construct.call_count == 1
    assert len(script.requests) == 2


def test_chat_only_purpose_unavailable() -> None:
    script = Script(chat_payload())
    with server(script) as url:
        host = open_provider(settings(url))
        assert not script.requests
        with pytest.raises(HostError) as error:
            host.model_execution(ModelPurpose.EMBEDDING)
        assert error.value.failure is HostFailure.PURPOSE_UNAVAILABLE
        result = asyncio.run(
            host.governed_chat(host.model_execution(ModelPurpose.CHAT), chat_request())
        )
    assert result.response is not None
    assert len(script.requests) == 1


def test_embedding_purpose_and_governed_result() -> None:
    script = Script(embedding_payload())
    with server(script) as url:
        host = open_provider(
            dataclasses.replace(settings(url), embedding_model="embed-model")
        )
        result = asyncio.run(
            host.governed_embed(
                host.model_execution(ModelPurpose.EMBEDDING),
                EmbeddingRequest(("a", "b")),
            )
        )
    assert result.execution.final_state is ExecutionState.SUCCEEDED
    assert result.response is not None
    assert result.response.model_identity == ModelId("embed-model")
    assert len(script.requests) == 1


def test_neutral_offers_and_plugin_identity() -> None:
    chat = model_chat_offer()
    embedding = model_embedding_offer()
    assert chat.capability.value == "legoai.intelligence.model.chat"
    assert embedding.capability.value == "legoai.intelligence.model.embedding"
    assert (
        chat.version
        == embedding.version
        == model_capability_version()
        == Version(1, 0, 0)
    )
    assert ollama_plugin_id() == PluginId("legoai.reference", "ollama-model-adapter")
    assert ollama_release() == Version(1, 0, 0)
    assert ollama_declaration().offers == (chat, embedding)
    assert openai_compatible_declaration(embedding=True).offers == (chat, embedding)
    assert openai_compatible_declaration(embedding=False).offers == (chat,)
    assert (
        openai_compatible_declaration(embedding=False).plugin_id != ollama_plugin_id()
    )


@pytest.mark.parametrize("purpose", list(ModelPurpose))
@pytest.mark.parametrize(
    "status, mode, effect, recoverability",
    [
        (401, "complete", EffectExtent.NONE, Recoverability.TERMINAL),
        (403, "complete", EffectExtent.NONE, Recoverability.TERMINAL),
        (429, "complete", EffectExtent.NONE, Recoverability.POTENTIALLY_RETRYABLE),
        (503, "complete", EffectExtent.NONE, Recoverability.POTENTIALLY_RETRYABLE),
        (500, "complete", EffectExtent.NONE, Recoverability.TERMINAL),
        (200, "truncated", EffectExtent.UNKNOWN, Recoverability.REQUIRES_INTERVENTION),
    ],
)
def test_governed_effects_no_retry_or_fallback(
    purpose: ModelPurpose,
    status: int,
    mode: str,
    effect: EffectExtent,
    recoverability: Recoverability,
) -> None:
    script = Script(b"private body", status, mode)
    fallback = FakeModel()
    constructions: list[str] = []
    with server(script) as url:
        config = host_config(
            binding(dataclasses.replace(settings(url), embedding_model="embed-model")),
            fake_binding(fallback, constructions=constructions),
        )
        host = open_local_host(config, selection("openai"), clock=lambda: NOW)
        context = host.model_execution(purpose)

        async def scenario() -> None:
            async def invoke():
                if purpose is ModelPurpose.CHAT:
                    return await host.governed_chat(context, chat_request())
                return await host.governed_embed(context, EmbeddingRequest(("a", "b")))

            result = await invoke()
            assert result.response is None
            assert result.execution.final_state is ExecutionState.FAILED
            assert result.execution.effect is effect
            assert result.execution.error is not None
            assert result.execution.error.category is ErrorCategory.DEPENDENCY_FAILURE
            assert result.execution.error.recoverability is recoverability
            with pytest.raises(ExecutionTransitionError):
                await invoke()

        asyncio.run(scenario())
    assert len(script.requests) == 1
    assert constructions == [] and fallback.chat_calls == fallback.embed_calls == 0


@pytest.mark.parametrize("purpose", list(ModelPurpose))
@pytest.mark.parametrize(
    "error, effect, recovery",
    [
        (
            ModelPreflightError(),
            EffectExtent.NONE,
            Recoverability.POTENTIALLY_RETRYABLE,
        ),
        (ModelResponseRejectedError(), EffectExtent.NONE, Recoverability.TERMINAL),
        (
            ModelResponseRetryableRejectedError(),
            EffectExtent.NONE,
            Recoverability.POTENTIALLY_RETRYABLE,
        ),
        (
            ModelResponseUncertainError(),
            EffectExtent.UNKNOWN,
            Recoverability.REQUIRES_INTERVENTION,
        ),
    ],
)
def test_trusted_failure_contract(
    purpose: ModelPurpose,
    error: Exception,
    effect: EffectExtent,
    recovery: Recoverability,
) -> None:
    model = FakeModel()
    model.error = error
    host = open_local_host(
        host_config(fake_binding(model)), selection(), clock=lambda: NOW
    )
    context = host.model_execution(purpose)
    result = asyncio.run(
        host.governed_chat(context, chat_request())
        if purpose is ModelPurpose.CHAT
        else host.governed_embed(context, EmbeddingRequest(("a",)))
    )
    assert result.execution.effect is effect
    assert result.execution.error.recoverability is recovery
    assert model.chat_calls + model.embed_calls == 1
    assert issubclass(ModelResponseRetryableRejectedError, ModelResponseRejectedError)


async def application(host: GovernedHost) -> tuple[ChatResult, EmbeddingResult]:
    """Unmodified provider-neutral application for every conformance row."""
    chat = await host.governed_chat(
        host.model_execution(ModelPurpose.CHAT), chat_request()
    )
    embedding = await host.governed_embed(
        host.model_execution(ModelPurpose.EMBEDDING), EmbeddingRequest(("a", "b"))
    )
    for result in (chat, embedding):
        assert result.execution.final_state is ExecutionState.SUCCEEDED
        assert result.execution.effect is EffectExtent.COMPLETED
    assert chat.response is not None and embedding.response is not None
    return chat.response, embedding.response


@pytest.mark.parametrize("row", ["A", "B", "C"])
def test_portability_rows(row: str) -> None:
    if row == "A":
        model = FixedModel(
            ChatResult("hello", ModelId("chat-model"), ProviderId("endpoint"), None),
            EmbeddingResult(
                ((1.0, 0.0), (0.0, 1.0)),
                2,
                ModelId("embed-model"),
                ProviderId("endpoint"),
            ),
        )
        config = ModelBindingConfig(
            "row",
            PROFILE,
            TrustedModelContribution(
                PluginId("test", "fixed"),
                ProviderId("endpoint"),
                ModelId("chat-model"),
                frozenset(ModelPurpose),
                lambda: model,
            ),
        )
        host = open_local_host(host_config(config), selection("row"), clock=lambda: NOW)
        results = asyncio.run(application(host))
        assert model.chat_calls == model.embedding_calls == 1
    elif row == "B":
        config = ModelBindingConfig(
            "row",
            PROFILE,
            OllamaSettings(
                "http://unused.invalid",
                "chat-model",
                "embed-model",
                1.0,
                ProviderId("endpoint"),
            ),
        )
        host = open_local_host(host_config(config), selection("row"), clock=lambda: NOW)
        # Ollama deliberately retains configured identity, not returned identity.
        with patch(
            "urllib.request.urlopen",
            side_effect=[
                _FakeResponse({"message": {"content": "hello"}, "model": "different"}),
                _FakeResponse({"embeddings": [[1, 0], [0, 1]], "model": "different"}),
            ],
        ) as calls:
            results = asyncio.run(application(host))
        assert calls.call_count == 2
    else:
        script = Script(
            {
                "/v1/chat/completions": chat_payload(),
                "/v1/embeddings": embedding_payload(),
            },
            mode="by-path",
        )
        with server(script) as url:
            host = open_provider(
                dataclasses.replace(settings(url), embedding_model="embed-model")
            )
            results = asyncio.run(application(host))
        assert len(script.requests) == 2
    assert results[0].content == "hello"
    assert results[0].model_identity == ModelId("chat-model")
    assert results[1].model_identity == ModelId("embed-model")
    assert results[1].vectors == ((1.0, 0.0), (0.0, 1.0))
    assert all(r.provider_identity == ProviderId("endpoint") for r in results)
