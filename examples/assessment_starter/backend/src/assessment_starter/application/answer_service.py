"""Application logic depends on the Model port, never its provider."""

from dataclasses import dataclass

from assessment_starter.model import ChatMessage, ChatRequest, ChatRole, ModelPort

MAX_QUESTION_LENGTH = 4000


@dataclass(frozen=True, slots=True)
class AnswerService:
    model: ModelPort

    async def answer(self, question: str) -> str:
        if type(question) is not str or not question.strip():
            raise ValueError("Question must not be empty")
        if len(question) > MAX_QUESTION_LENGTH:
            raise ValueError("Question is too long")
        result = await self.model.chat(
            ChatRequest((ChatMessage(ChatRole.USER, question.strip()),))
        )
        return result.content
