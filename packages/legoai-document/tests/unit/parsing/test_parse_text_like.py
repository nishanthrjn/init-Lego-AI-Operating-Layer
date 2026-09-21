"""Behavioral tests for TEXT/MARKDOWN/HTML parsing, derived from the live
verification evidence in DOCUMENT-PARSING-CAPABILITY-DESIGN.md SS18a, SS23.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from legoai_document.parsing import (
    DocumentFormat,
    DocumentParsingRequest,
    MalformedDocumentError,
    ParsedDocument,
    ParsedPage,
    parse_document,
)


@pytest.mark.parametrize(
    "fmt", [DocumentFormat.TEXT, DocumentFormat.MARKDOWN, DocumentFormat.HTML]
)
def test_empty_utf8_is_one_empty_page(
    fixture_bytes: Callable[[str], bytes], fmt: DocumentFormat
) -> None:
    content = fixture_bytes("01_empty_utf8.txt")
    result = parse_document(DocumentParsingRequest(content=content, format=fmt))
    assert result == ParsedDocument(pages=(ParsedPage(index=0, text=""),))


def test_ascii_text_preserved_exactly(fixture_bytes: Callable[[str], bytes]) -> None:
    content = fixture_bytes("02_ascii.txt")
    result = parse_document(
        DocumentParsingRequest(content=content, format=DocumentFormat.TEXT)
    )
    assert result.pages == (ParsedPage(index=0, text="Hello world"),)


def test_unicode_text_preserved_exactly(fixture_bytes: Callable[[str], bytes]) -> None:
    content = fixture_bytes("03_unicode_utf8.txt")
    result = parse_document(
        DocumentParsingRequest(content=content, format=DocumentFormat.TEXT)
    )
    assert result.pages[0].text == content.decode("utf-8")
    assert "café" in result.pages[0].text
    assert "日本語" in result.pages[0].text
    assert "\U0001f600" in result.pages[0].text


def test_multiline_text_newlines_preserved(
    fixture_bytes: Callable[[str], bytes],
) -> None:
    content = fixture_bytes("04_multiline.txt")
    result = parse_document(
        DocumentParsingRequest(content=content, format=DocumentFormat.TEXT)
    )
    assert result.pages[0].text == "line1\nline2\nline3"


def test_leading_trailing_whitespace_not_trimmed(
    fixture_bytes: Callable[[str], bytes],
) -> None:
    content = fixture_bytes("05_leading_trailing_ws.txt")
    result = parse_document(
        DocumentParsingRequest(content=content, format=DocumentFormat.TEXT)
    )
    assert result.pages[0].text == "  \n  hello  \n  "


def test_markdown_remains_opaque_no_rendering(
    fixture_bytes: Callable[[str], bytes],
) -> None:
    content = fixture_bytes("06_markdown_opaque.md")
    result = parse_document(
        DocumentParsingRequest(content=content, format=DocumentFormat.MARKDOWN)
    )
    assert result.pages[0].text == content.decode("utf-8")
    assert "#" in result.pages[0].text
    assert "*emphasis*" in result.pages[0].text


def test_html_remains_opaque_no_stripping(
    fixture_bytes: Callable[[str], bytes],
) -> None:
    content = fixture_bytes("07_html_opaque.html")
    result = parse_document(
        DocumentParsingRequest(content=content, format=DocumentFormat.HTML)
    )
    assert result.pages[0].text == content.decode("utf-8")
    assert "<html>" in result.pages[0].text
    assert "<b>world</b>" in result.pages[0].text


@pytest.mark.parametrize(
    "fmt", [DocumentFormat.TEXT, DocumentFormat.MARKDOWN, DocumentFormat.HTML]
)
def test_invalid_utf8_raises_malformed_document_error(
    fixture_bytes: Callable[[str], bytes], fmt: DocumentFormat
) -> None:
    content = fixture_bytes("15_invalid_utf8.txt")
    with pytest.raises(MalformedDocumentError) as excinfo:
        parse_document(DocumentParsingRequest(content=content, format=fmt))
    assert isinstance(excinfo.value.__cause__, UnicodeDecodeError)
