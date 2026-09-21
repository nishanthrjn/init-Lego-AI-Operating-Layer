"""Behavioral tests for PDF parsing, derived from the live verification
evidence in DOCUMENT-PARSING-CAPABILITY-DESIGN.md SS18a, SS23 -- including
the regression test (SS"blank page, no OCR") documenting why this
capability's contract deliberately differs from DocuMind-AgentFramework's
20-characters-per-page OCR heuristic, which was confirmed live to misfire
on this exact fixture shape.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from legoai_document.parsing import (
    DocumentFormat,
    DocumentParsingRequest,
    EncryptedDocumentError,
    MalformedDocumentError,
    parse_document,
)
from legoai_document.parsing.errors import DocumentParsingError


def _pdf_request(content: bytes) -> DocumentParsingRequest:
    return DocumentParsingRequest(content=content, format=DocumentFormat.PDF)


def test_one_page_pdf(fixture_bytes: Callable[[str], bytes]) -> None:
    result = parse_document(_pdf_request(fixture_bytes("08_one_page_text.pdf")))
    assert len(result.pages) == 1
    assert result.pages[0].index == 0
    assert result.pages[0].text == "Hello world from page one.\n"


def test_multi_page_pdf_order_and_isolation(
    fixture_bytes: Callable[[str], bytes],
) -> None:
    result = parse_document(_pdf_request(fixture_bytes("09_multi_page_text.pdf")))
    assert len(result.pages) == 3
    assert [p.index for p in result.pages] == [0, 1, 2]
    assert result.pages[0].text == "Page one line A\nPage one line B\n"
    assert result.pages[1].text == "Page two line A\nPage two line B\n"
    assert result.pages[2].text == "Page three only line\n"
    # No cross-page merging: page 0's text does not leak into page 1's.
    assert "Page two" not in result.pages[0].text
    assert "Page one" not in result.pages[1].text


def test_blank_page_is_preserved_not_omitted(
    fixture_bytes: Callable[[str], bytes],
) -> None:
    """Regression test for the DocuMind (MAF) defect: a genuine 3-page PDF
    with one blank page in the middle was confirmed live to trip MAF's
    20-chars/page OCR-fallback heuristic (44 chars / 3 pages ~= 14.7 < 20),
    incorrectly routing a real, valid-text document through OCR. This
    capability has no OCR dependency at all, so that failure mode is
    structurally impossible here -- the deterministic parser MUST succeed,
    preserve all three pages including the blank one, and never invoke any
    model/network call."""
    result = parse_document(_pdf_request(fixture_bytes("10_blank_page_middle.pdf")))

    assert len(result.pages) == 3
    assert result.pages[0].text == "First page has text.\n"
    assert result.pages[1].index == 1
    assert result.pages[1].text == ""  # blank page preserved, not dropped
    assert result.pages[2].text == "Third page has text.\n"


def test_unicode_pdf_text_preserved(fixture_bytes: Callable[[str], bytes]) -> None:
    result = parse_document(_pdf_request(fixture_bytes("11_unicode_pdf.pdf")))
    text = result.pages[0].text
    assert "café" in text
    assert "naïve" in text
    assert "über" in text


def test_image_only_pdf_returns_empty_text_not_error(
    fixture_bytes: Callable[[str], bytes],
) -> None:
    """Image-only/scanned PDFs are not a parsing error: no OCR is invoked,
    and empty extracted text is a valid, successful result."""
    result = parse_document(_pdf_request(fixture_bytes("12_image_only.pdf")))
    assert len(result.pages) == 1
    assert result.pages[0].index == 0
    assert result.pages[0].text == ""


@pytest.mark.parametrize(
    "fixture_name", ["13_malformed_truncated.pdf", "13b_malformed_garbage.pdf"]
)
def test_malformed_pdf_raises_malformed_document_error(
    fixture_bytes: Callable[[str], bytes], fixture_name: str
) -> None:
    with pytest.raises(MalformedDocumentError) as excinfo:
        parse_document(_pdf_request(fixture_bytes(fixture_name)))
    assert excinfo.value.__cause__ is not None


def test_encrypted_pdf_raises_encrypted_document_error(
    fixture_bytes: Callable[[str], bytes],
) -> None:
    with pytest.raises(EncryptedDocumentError) as excinfo:
        parse_document(_pdf_request(fixture_bytes("14_encrypted.pdf")))
    assert excinfo.value.__cause__ is not None


def test_encrypted_pdf_is_not_misclassified_as_malformed(
    fixture_bytes: Callable[[str], bytes],
) -> None:
    """EncryptedDocumentError, not the broader MalformedDocumentError, must
    be raised -- verifies the FileNotDecryptedError-before-PdfReadError
    ordering (SS13 of the design document)."""
    with pytest.raises(DocumentParsingError) as excinfo:
        parse_document(_pdf_request(fixture_bytes("14_encrypted.pdf")))
    assert type(excinfo.value) is EncryptedDocumentError
    assert not isinstance(excinfo.value, MalformedDocumentError)
