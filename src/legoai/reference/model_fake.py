"""Deterministic ModelPort double for offline consumers; no I/O or authority."""

from legoai.intelligence.model.ports import (
    ModelPreflightError,
    ModelResponseRejectedError,
)
from legoai.intelligence.model.values import (
    ChatRequest,
    ChatResult,
    EmbeddingRequest,
    EmbeddingResult,
)


class FixedModel:
    """Return explicit fixture results, with per-instance invocation counts.

    This is test support, not a production provider or governance bypass.
    No prompts are retained. Missing embedding fixtures fail before effects.
    """

    def __init__(
        self, chat_result: ChatResult, embedding_result: EmbeddingResult | None = None
    ) -> None:
        if type(chat_result) is not ChatResult:
            raise TypeError("FixedModel requires ChatResult")
        if (
            embedding_result is not None
            and type(embedding_result) is not EmbeddingResult
        ):
            raise TypeError("FixedModel requires EmbeddingResult or None")
        self._chat_result = chat_result
        self._embedding_result = embedding_result
        self.chat_calls = 0
        self.embedding_calls = 0

    async def chat(self, request: ChatRequest) -> ChatResult:
        if type(request) is not ChatRequest:
            raise TypeError("chat requires ChatRequest")
        if request.response_format is not None:
            # ADR-022: a fixed reply cannot honor a schema; refuse, never ignore.
            raise ModelPreflightError(
                "structured output is not supported by FixedModel"
            )
        self.chat_calls += 1
        return self._chat_result

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        if type(request) is not EmbeddingRequest:
            raise TypeError("embed requires EmbeddingRequest")
        if self._embedding_result is None:
            raise ModelPreflightError("No embedding fixture configured")
        self.embedding_calls += 1
        if len(request.inputs) != len(self._embedding_result.vectors):
            raise ModelResponseRejectedError(
                "Embedding fixture count does not match request"
            )
        return self._embedding_result
