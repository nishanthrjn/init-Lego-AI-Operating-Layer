"""HTTP routes receive an explicitly composed service."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from assessment_starter.api.schemas import AskRequest, AskResponse
from assessment_starter.application.answer_service import AnswerService
from assessment_starter.model import (
    ModelPreflightError,
    ModelResponseRejectedError,
    ModelResponseUncertainError,
)


def create_router(service: AnswerService) -> APIRouter:
    router = APIRouter()

    def provide_service() -> AnswerService:
        return service

    @router.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.post("/api/v1/ask", response_model=AskResponse)
    async def ask(
        request: AskRequest,
        answers: Annotated[AnswerService, Depends(provide_service)],
    ) -> AskResponse:
        try:
            return AskResponse(answer=await answers.answer(request.question))
        except (
            ModelPreflightError,
            ModelResponseRejectedError,
            ModelResponseUncertainError,
        ):
            raise HTTPException(
                status_code=502,
                detail="Model request failed. Check backend model configuration and availability.",
            ) from None

    return router
