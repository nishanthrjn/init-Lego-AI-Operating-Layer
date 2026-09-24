"""Offline composition using valid, existing LegoAI values."""

from legoai.intelligence.model.values import ChatResult, ModelId, ModelUsage, ProviderId
from legoai.reference.model_fake import FixedModel


def make_model() -> FixedModel:
    return FixedModel(
        ChatResult(
            "This is a deterministic offline answer. Replace the injected model to add a real provider.",
            ModelId("assessment-fixture"),
            ProviderId("offline-fixture"),
            ModelUsage(0, 0),
        )
    )
