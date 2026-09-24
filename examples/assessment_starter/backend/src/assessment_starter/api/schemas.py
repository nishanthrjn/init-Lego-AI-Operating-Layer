"""Closed API request and response shapes."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from assessment_starter.application.answer_service import MAX_QUESTION_LENGTH


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    question: str = Field(min_length=1, max_length=MAX_QUESTION_LENGTH)

    @field_validator("question")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question must not be empty")
        return value.strip()


class AskResponse(BaseModel):
    answer: str
