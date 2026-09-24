"""Composition root. Each application gets its own configured model instance."""

from fastapi import FastAPI

from assessment_starter.api.routes import create_router
from assessment_starter.application.answer_service import AnswerService
from assessment_starter.core.config import Settings
from assessment_starter.model import ModelPort
from assessment_starter.model_factory import make_model


def create_app(
    settings: Settings | None = None, model: ModelPort | None = None
) -> FastAPI:
    config = settings if settings is not None else Settings()
    provider = model if model is not None else make_model(config)
    application = FastAPI(title=config.title)
    application.include_router(create_router(AnswerService(provider)))
    return application


app = create_app(Settings.from_startup())
