import asyncio

import pytest

from assessment_starter.application.answer_service import AnswerService
from assessment_starter.fixtures import make_model
from assessment_starter.model import (
    ChatRequest,
    ChatResult,
    ChatRole,
    FixedModel,
    ModelPort,
)


class RecordingModel(FixedModel):
    request: ChatRequest | None = None

    async def chat(self, request: ChatRequest) -> ChatResult:
        self.request = request
        return await super().chat(request)


def test_existing_fixed_model() -> None:
    model: ModelPort = make_model()
    assert "offline answer" in asyncio.run(AnswerService(model).answer("Hello"))


def test_request_shape_and_structural_substitution() -> None:
    # Obtain the real fixture result without weakening the contract.
    from assessment_starter.model import ChatMessage

    result = asyncio.run(
        make_model().chat(ChatRequest((ChatMessage(ChatRole.USER, "fixture"),)))
    )
    model = RecordingModel(result)
    port: ModelPort = model
    assert asyncio.run(AnswerService(port).answer("  Question?  ")) == result.content
    assert model.request == ChatRequest((ChatMessage(ChatRole.USER, "Question?"),))
    assert model.chat_calls == 1


@pytest.mark.parametrize("question", ["", "   ", "\n\t", "x" * 4001])
def test_invalid_input_precedes_model(question: str) -> None:
    model = make_model()
    with pytest.raises(ValueError):
        asyncio.run(AnswerService(model).answer(question))
    assert model.chat_calls == 0
