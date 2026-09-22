"""Public surface of the document.rerank capability.

Deliberately exports only the supported names below -- no wildcard
re-export and no aggregate "import everything" module.
"""

from __future__ import annotations

from legoai_document.rerank.api import Reranker, identity_rerank
from legoai_document.rerank.errors import RerankValidationError
from legoai_document.rerank.values import (
    RerankCandidate,
    RerankedCandidate,
    RerankRequest,
    RerankResult,
)

__all__ = [
    "RerankCandidate",
    "RerankRequest",
    "RerankResult",
    "RerankValidationError",
    "Reranker",
    "RerankedCandidate",
    "identity_rerank",
]
