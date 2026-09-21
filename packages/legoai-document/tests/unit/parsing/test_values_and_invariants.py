"""Value-type and cross-cutting invariant tests for document.parsing."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from legoai_document.parsing import (
    DocumentFormat,
    DocumentParsingRequest,
    ParsedDocument,
    ParsedPage,
    UnsupportedDocumentFormatError,
    parse_document,
)


def test_document_format_is_closed_enum_with_four_members() -> None:
    assert {member.name for member in DocumentFormat} == {
        "TEXT",
        "MARKDOWN",
        "HTML",
        "PDF",
    }


def test_request_is_frozen_and_slotted() -> None:
    request = DocumentParsingRequest(content=b"hi", format=DocumentFormat.TEXT)
    with pytest.raises(AttributeError):
        request.content = b"mutated"  # type: ignore[misc]  # noqa: B010
    with pytest.raises(AttributeError):
        request.new_field = 1  # type: ignore[attr-defined]  # noqa: B010


def test_parsed_page_is_frozen_and_slotted() -> None:
    page = ParsedPage(index=0, text="hi")
    with pytest.raises(AttributeError):
        page.text = "mutated"  # type: ignore[misc]  # noqa: B010


def test_parsed_document_pages_is_a_tuple() -> None:
    document = ParsedDocument(pages=(ParsedPage(index=0, text="hi"),))
    assert isinstance(document.pages, tuple)
    with pytest.raises(AttributeError):
        document.pages = ()  # type: ignore[misc]  # noqa: B010


@pytest.mark.parametrize(
    "fmt", [DocumentFormat.TEXT, DocumentFormat.MARKDOWN, DocumentFormat.HTML]
)
def test_page_indices_are_stable_and_zero_based_for_text(fmt: DocumentFormat) -> None:
    result = parse_document(DocumentParsingRequest(content=b"hi", format=fmt))
    assert [p.index for p in result.pages] == [0]


def test_page_indices_are_stable_and_zero_based_for_pdf(
    fixture_bytes: Callable[[str], bytes],
) -> None:
    result = parse_document(
        DocumentParsingRequest(
            content=fixture_bytes("09_multi_page_text.pdf"), format=DocumentFormat.PDF
        )
    )
    assert [p.index for p in result.pages] == [0, 1, 2]


@pytest.mark.parametrize(
    "fmt", [DocumentFormat.TEXT, DocumentFormat.MARKDOWN, DocumentFormat.HTML]
)
def test_deterministic_repeated_results_for_text(fmt: DocumentFormat) -> None:
    request = DocumentParsingRequest(content=b"the same content", format=fmt)
    assert parse_document(request) == parse_document(request)


def test_deterministic_repeated_results_for_pdf(
    fixture_bytes: Callable[[str], bytes],
) -> None:
    request = DocumentParsingRequest(
        content=fixture_bytes("09_multi_page_text.pdf"), format=DocumentFormat.PDF
    )
    assert parse_document(request) == parse_document(request)


def test_parse_document_does_not_mutate_request() -> None:
    content = b"hello world"
    request = DocumentParsingRequest(content=content, format=DocumentFormat.TEXT)
    parse_document(request)
    assert request.content == content
    assert request.format == DocumentFormat.TEXT


def test_unsupported_format_defensive_path() -> None:
    """The public API only accepts DocumentFormat members, but the
    defensive branch (SS14 of the design document) must still raise
    UnsupportedDocumentFormatError if an unrecognized value somehow reaches
    parse_document -- exercised here via a request built with a value not
    covered by the two recognized branches."""

    class _RogueFormat:
        """Not a DocumentFormat member; simulates a value the closed enum
        does not cover, to exercise the defensive raise path."""

    request = DocumentParsingRequest(
        content=b"irrelevant",
        format=_RogueFormat(),  # type: ignore[arg-type]
    )
    with pytest.raises(UnsupportedDocumentFormatError):
        parse_document(request)
