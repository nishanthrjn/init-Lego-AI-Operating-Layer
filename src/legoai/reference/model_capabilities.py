"""Private provider-neutral v1 Model offers (ADR-014 §14.13)."""

from legoai.capabilities.values import CapabilityId, CapabilityOffer
from legoai.kernel.versions import Version


def model_capability_version() -> Version:
    return Version(1, 0, 0)


def model_chat_capability_id() -> CapabilityId:
    return CapabilityId("legoai.intelligence.model.chat")


def model_embedding_capability_id() -> CapabilityId:
    return CapabilityId("legoai.intelligence.model.embedding")


def model_chat_offer() -> CapabilityOffer:
    return CapabilityOffer(model_chat_capability_id(), model_capability_version())


def model_embedding_offer() -> CapabilityOffer:
    return CapabilityOffer(model_embedding_capability_id(), model_capability_version())
