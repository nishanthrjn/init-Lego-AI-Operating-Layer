"""Public surface of the document.parsing capability.

Deliberately exports only the supported names below -- no wildcard
re-export and no aggregate "import everything" module.
"""

from __future__ import annotations

from legoai_document.parsing.api import flatten_pages, parse_document
from legoai_document.parsing.errors import (
    DocumentParsingError,
    EncryptedDocumentError,
    MalformedDocumentError,
    UnsupportedDocumentFormatError,
)
from legoai_document.parsing.values import (
    DocumentFormat,
    DocumentParsingRequest,
    ParsedDocument,
    ParsedPage,
)

__all__ = [
    "DocumentFormat",
    "DocumentParsingError",
    "DocumentParsingRequest",
    "EncryptedDocumentError",
    "MalformedDocumentError",
    "ParsedDocument",
    "ParsedPage",
    "UnsupportedDocumentFormatError",
    "flatten_pages",
    "parse_document",
]
