"""LegoAI v0.1: `legoai.intelligence.model.values` construction/validation."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from legoai.intelligence.model.values import (
    ChatMessage,
    ChatRequest,
    ChatResult,
    ChatRole,
    EmbeddingRequest,
    EmbeddingResult,
    ModelId,
    ModelUsage,
    ProviderId,
)


def test_model_id_and_provider_id_validate_text() -> None:
    assert ModelId("llama3.2").value == "llama3.2"
    assert ProviderId("ollama-local").value == "ollama-local"
    with pytest.raises(TypeError):
        ModelId(123)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        ModelId("")


def test_chat_message_requires_role_and_string_content() -> None:
    message = ChatMessage(ChatRole.USER, "hello")
    assert message.content == "hello"
    with pytest.raises(TypeError):
        ChatMessage("user", "hello")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        ChatMessage(ChatRole.USER, 123)  # type: ignore[arg-type]


def test_chat_role_exact_three_members() -> None:
    assert {role.value for role in ChatRole} == {"system", "user", "assistant"}


def test_chat_request_requires_nonempty_message_tuple() -> None:
    request = ChatRequest((ChatMessage(ChatRole.USER, "hi"),))
    assert len(request.messages) == 1
    with pytest.raises(ValueError, match="at least one message"):
        ChatRequest(())
    with pytest.raises(TypeError):
        ChatRequest([ChatMessage(ChatRole.USER, "hi")])  # type: ignore[arg-type]


def test_chat_request_immutable() -> None:
    request = ChatRequest((ChatMessage(ChatRole.USER, "hi"),))
    with pytest.raises(FrozenInstanceError):
        setattr(request, "messages", ())  # noqa: B010


def test_model_usage_accepts_none_or_nonnegative_ints() -> None:
    usage = ModelUsage(prompt_tokens=10, completion_tokens=None)
    assert usage.prompt_tokens == 10
    assert usage.completion_tokens is None
    with pytest.raises(TypeError):
        ModelUsage(prompt_tokens=-1, completion_tokens=None)
    with pytest.raises(TypeError):
        ModelUsage(prompt_tokens=1.5, completion_tokens=None)  # type: ignore[arg-type]


def test_chat_result_requires_model_and_provider_identity() -> None:
    result = ChatResult(
        "an answer", ModelId("llama3.2"), ProviderId("ollama-local"), None
    )
    assert result.content == "an answer"
    with pytest.raises(TypeError):
        ChatResult("x", "llama3.2", ProviderId("ollama-local"), None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        ChatResult("x", ModelId("llama3.2"), "ollama-local", None)  # type: ignore[arg-type]


def test_embedding_request_requires_tuple_of_str() -> None:
    request = EmbeddingRequest(("one", "two"))
    assert request.inputs == ("one", "two")
    with pytest.raises(TypeError):
        EmbeddingRequest(["one", "two"])  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        EmbeddingRequest((1, 2))  # type: ignore[arg-type]


def test_embedding_request_empty_batch_is_valid() -> None:
    # Symmetric empty-in/empty-out is a legitimate shape
    # (EMBEDDING-CAPABILITY-DESIGN.md SS25's live-verified array-empty case).
    request = EmbeddingRequest(())
    assert request.inputs == ()


def test_embedding_result_enforces_uniform_positive_dimension() -> None:
    result = EmbeddingResult(
        ((1.0, 2.0), (3.0, 4.0)),
        2,
        ModelId("nomic-embed-text"),
        ProviderId("ollama-local"),
    )
    assert result.dimension == 2

    with pytest.raises(ValueError, match="positive"):
        EmbeddingResult(((1.0, 2.0),), 0, ModelId("m"), ProviderId("p"))

    with pytest.raises(ValueError, match="length must equal dimension"):
        EmbeddingResult(((1.0, 2.0), (3.0,)), 2, ModelId("m"), ProviderId("p"))


def test_embedding_result_empty_batch_requires_dimension_zero() -> None:
    # EMBEDDING-CAPABILITY-DESIGN.md SS26's open question, resolved: an
    # empty result honestly reports dimension 0 rather than fabricating one.
    result = EmbeddingResult((), 0, ModelId("m"), ProviderId("p"))
    assert result.vectors == ()
    assert result.dimension == 0
    with pytest.raises(ValueError, match="must be exactly 0"):
        EmbeddingResult((), 5, ModelId("m"), ProviderId("p"))


def test_embedding_result_rejects_non_finite_components() -> None:
    with pytest.raises(ValueError, match="finite"):
        EmbeddingResult(((1.0, float("nan")),), 2, ModelId("m"), ProviderId("p"))
    with pytest.raises(ValueError, match="finite"):
        EmbeddingResult(((1.0, float("inf")),), 2, ModelId("m"), ProviderId("p"))


def test_embedding_result_immutable() -> None:
    result = EmbeddingResult(((1.0,),), 1, ModelId("m"), ProviderId("p"))
    with pytest.raises(FrozenInstanceError):
        setattr(result, "dimension", 2)  # noqa: B010
    assert replace(result, dimension=1) == result
