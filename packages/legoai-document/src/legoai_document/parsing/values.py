"""Immutable value types for the document.parsing capability.

These types carry only what the pure parsing computation itself produces or
consumes. Document identity, tenant scope, persistence keys, timestamps,
filenames, MIME-type strings, and any provider/model metadata are
deliberately absent: they belong to a caller's Execution/orchestration
layer, not to this capability's semantic result. See
DOCUMENT-PARSING-CAPABILITY-DESIGN.md SS9-11 for the entity-separation and
input-representation rationale.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DocumentFormat(Enum):
    """Closed set of formats document.parsing v1 can realize.

    Resolving a MIME type, file extension, or sniffed content into one of
    these values is the caller's responsibility -- this capability trusts
    the declared value and performs no sniffing (see the design document's
    format-selection-mechanism section).
    """

    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"


@dataclass(frozen=True, slots=True)
class DocumentParsingRequest:
    """Immutable input to the document.parsing capability.

    No filename/document-identity/tenant field -- a deliberate exclusion,
    not an oversight (mirrors ChunkingRequest's exclusion of document_id
    in Batch 1, for the same entity-separation reasons).
    """

    content: bytes
    format: DocumentFormat


@dataclass(frozen=True, slots=True)
class ParsedPage:
    """A single physical page's extracted text.

    index is zero-based, matching this repository's convention (Chunk.index
    in legoai_document.chunking is also zero-based) and pypdf's own page
    indexing. A non-paginated source (TEXT/MARKDOWN/HTML) is represented as
    exactly one page. A blank or image-only PDF page is represented with
    text == "" -- it is never omitted (see SS9 of the design document).
    """

    index: int
    text: str


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """Immutable, page-ordered output of document.parsing."""

    pages: tuple[ParsedPage, ...]
