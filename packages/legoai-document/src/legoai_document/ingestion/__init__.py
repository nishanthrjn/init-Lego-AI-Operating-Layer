"""Public surface of the document.ingestion composition.

Deliberately exports only the supported names below -- no wildcard
re-export and no aggregate "import everything" module.
"""

from __future__ import annotations

from legoai_document.ingestion.api import ingest_document
from legoai_document.ingestion.values import IngestionRequest, IngestionResult

__all__ = [
    "IngestionRequest",
    "IngestionResult",
    "ingest_document",
]
