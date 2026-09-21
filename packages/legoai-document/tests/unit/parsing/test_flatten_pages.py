"""Tests for the flatten_pages projection helper."""

from __future__ import annotations

from legoai_document.parsing import ParsedDocument, ParsedPage, flatten_pages


def test_flatten_pages_preserves_order_with_default_separator() -> None:
    document = ParsedDocument(
        pages=(
            ParsedPage(index=0, text="first"),
            ParsedPage(index=1, text="second"),
            ParsedPage(index=2, text="third"),
        )
    )
    assert flatten_pages(document) == "first\n\nsecond\n\nthird"


def test_flatten_pages_accepts_explicit_separator() -> None:
    document = ParsedDocument(
        pages=(ParsedPage(index=0, text="a"), ParsedPage(index=1, text="b"))
    )
    assert flatten_pages(document, separator=" | ") == "a | b"


def test_flatten_pages_includes_blank_pages_as_empty_segments() -> None:
    document = ParsedDocument(
        pages=(
            ParsedPage(index=0, text="first"),
            ParsedPage(index=1, text=""),
            ParsedPage(index=2, text="third"),
        )
    )
    assert flatten_pages(document) == "first\n\n\n\nthird"


def test_flatten_pages_does_not_mutate_source_document() -> None:
    pages = (ParsedPage(index=0, text="a"), ParsedPage(index=1, text="b"))
    document = ParsedDocument(pages=pages)
    flatten_pages(document)
    assert document.pages == pages


def test_flatten_pages_single_page() -> None:
    document = ParsedDocument(pages=(ParsedPage(index=0, text="only"),))
    assert flatten_pages(document) == "only"


def test_flatten_pages_empty_document() -> None:
    document = ParsedDocument(pages=())
    assert flatten_pages(document) == ""
