"""document.parsing v1 -- deterministic text extraction for TEXT, MARKDOWN,
HTML, and text-bearing PDF.

Behavior (see DOCUMENT-PARSING-CAPABILITY-DESIGN.md SS6-10, SS18a for the
full characterization and live-verification evidence this implementation is
required to match):

- TEXT/MARKDOWN/HTML: content bytes -> strict UTF-8 decode -> one ParsedPage.
  No replacement decoding, no HTML/Markdown structural interpretation, no
  whitespace/newline normalization, no trimming. Invalid UTF-8 raises
  MalformedDocumentError.
- PDF: one ParsedPage per physical page, in order, including blank and
  image-only pages (text == "", never omitted). Text is exactly what
  `pypdf`'s `PageObject.extract_text()` returns for that page -- no
  additional LegoAI-side normalization. `pypdf` is used only behind this
  implementation; no `pypdf` type is part of the public API.
- No OCR is invoked at any point -- there is no dependency capable of it.
  An image-only or scanned PDF successfully returns pages with empty text;
  this is a valid result, not a parsing failure.
- Malformed/truncated PDFs and encrypted PDFs raise distinct, pack-local
  exceptions (MalformedDocumentError, EncryptedDocumentError respectively),
  chained from the underlying `pypdf` exception for diagnostics. No
  password-input support exists in v1.

Guarantees: page separation, stable page order, parser-provided textual
order, no additional LegoAI normalization.
Does NOT guarantee: visual layout, column, or table reconstruction; exact
source line-wrap geometry; font/style fidelity; reading-order correctness
for every complex PDF layout.
"""

from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError

from legoai_document.parsing.errors import (
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

_TEXT_LIKE_FORMATS = frozenset(
    {DocumentFormat.TEXT, DocumentFormat.MARKDOWN, DocumentFormat.HTML}
)


def parse_document(request: DocumentParsingRequest) -> ParsedDocument:
    """Extract page-ordered text from request.content per request.format.

    Deterministic, effect-free: no OCR, no network access, no persistence.

    Raises:
        UnsupportedDocumentFormatError: format has no v1 realization.
        MalformedDocumentError: content cannot be parsed as the declared format.
        EncryptedDocumentError: a PDF is encrypted and unreadable without a password.
    """
    if request.format in _TEXT_LIKE_FORMATS:
        return _parse_text_like(request.content)
    if request.format is DocumentFormat.PDF:
        return _parse_pdf(request.content)
    raise UnsupportedDocumentFormatError(
        f"document.parsing has no v1 realization for format {request.format!r}"
    )


def _parse_text_like(content: bytes) -> ParsedDocument:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MalformedDocumentError("content is not valid UTF-8") from exc
    return ParsedDocument(pages=(ParsedPage(index=0, text=text),))


def _parse_pdf(content: bytes) -> ParsedDocument:
    # FileNotDecryptedError is a PdfReadError subclass and MUST be caught
    # first -- otherwise the broader `except PdfReadError` would silently
    # reclassify an encrypted PDF as merely malformed (verified live: pypdf
    # raises this lazily, on first page/text access, not at construction).
    try:
        reader = PdfReader(BytesIO(content))
        pages = tuple(
            ParsedPage(index=index, text=page.extract_text())
            for index, page in enumerate(reader.pages)
        )
    except FileNotDecryptedError as exc:
        raise EncryptedDocumentError(
            "PDF is encrypted and cannot be read without a valid password"
        ) from exc
    except PdfReadError as exc:
        raise MalformedDocumentError(f"PDF could not be parsed: {exc}") from exc
    return ParsedDocument(pages=pages)


def flatten_pages(document: ParsedDocument, *, separator: str = "\n\n") -> str:
    """Project a ParsedDocument to a single string, joining page texts with
    separator. A pure, non-mutating convenience derivation -- not stored
    data. Lives here (not in legoai_document.chunking) because it operates
    purely on ParsedDocument/ParsedPage, which this module already owns."""
    return separator.join(page.text for page in document.pages)
