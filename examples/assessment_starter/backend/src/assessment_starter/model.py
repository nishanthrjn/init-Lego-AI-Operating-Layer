"""Aliases of existing contracts; no new Model abstraction."""

from legoai.intelligence.model.ports import ModelPort as ModelPort
from legoai.intelligence.model.ports import ModelPreflightError as ModelPreflightError
from legoai.intelligence.model.ports import (
    ModelResponseRejectedError as ModelResponseRejectedError,
)
from legoai.intelligence.model.ports import (
    ModelResponseUncertainError as ModelResponseUncertainError,
)
from legoai.intelligence.model.values import ChatMessage as ChatMessage
from legoai.intelligence.model.values import ChatRequest as ChatRequest
from legoai.intelligence.model.values import ChatResult as ChatResult
from legoai.intelligence.model.values import ChatRole as ChatRole
from legoai.reference.model_fake import FixedModel as FixedModel
