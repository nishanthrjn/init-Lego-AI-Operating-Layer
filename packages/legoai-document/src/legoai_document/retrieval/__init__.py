"""Public surface of the document.retrieval capability.

Deliberately exports only the supported names below -- no wildcard
re-export and no aggregate "import everything" module.
"""

from __future__ import annotations

from legoai_document.retrieval.api import hybrid_search
from legoai_document.retrieval.errors import (
    RetrievalStoreError,
    RetrievalValidationError,
)
from legoai_document.retrieval.store import SQLiteRetrievalStore
from legoai_document.retrieval.values import (
    IndexedChunk,
    RetrievalCandidate,
    RetrievalQuery,
    RetrievalResult,
    RetrievalScope,
)

__all__ = [
    "IndexedChunk",
    "RetrievalCandidate",
    "RetrievalQuery",
    "RetrievalResult",
    "RetrievalScope",
    "RetrievalStoreError",
    "RetrievalValidationError",
    "SQLiteRetrievalStore",
    "hybrid_search",
]
