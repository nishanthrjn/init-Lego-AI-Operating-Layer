"""Single application model-selection point. Construction performs no I/O."""

from legoai.intelligence.model.values import ProviderId
from legoai.reference.model import OllamaModelAdapter, OllamaModelConfig

from assessment_starter.core.config import Settings
from assessment_starter.fixtures import make_model as make_fixed_model
from assessment_starter.model import ModelPort


def make_model(settings: Settings) -> ModelPort:
    if settings.model_provider == "fixed":
        return make_fixed_model()
    return OllamaModelAdapter(
        OllamaModelConfig(
            base_url=settings.ollama_base_url,
            chat_model=settings.ollama_model,
            # Existing adapter contract requires this field; this app never embeds.
            embedding_model="unused-by-assessment-starter",
            timeout_seconds=settings.model_timeout_seconds,
        ),
        ProviderId("assessment-ollama"),
    )
