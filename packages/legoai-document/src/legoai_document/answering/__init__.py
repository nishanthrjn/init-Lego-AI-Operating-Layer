"""Public surface of the document.answering capability.

Deliberately exports only the supported names below -- no wildcard
re-export and no aggregate "import everything" module.
"""

from __future__ import annotations

from legoai_document.answering.api import GovernedChat, answer_question
from legoai_document.answering.values import (
    AnsweringRequest,
    AnsweringResult,
    AnswerProvenance,
    Citation,
)

__all__ = [
    "AnswerProvenance",
    "AnsweringRequest",
    "AnsweringResult",
    "Citation",
    "GovernedChat",
    "answer_question",
]
