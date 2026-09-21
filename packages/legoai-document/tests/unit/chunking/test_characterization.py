"""Characterization tests for behaviors the DocuMind oracles left untested
or defective. See CHUNKING-CAPABILITY-DESIGN.md SS4, SS12 and the
authorized decisions recorded there (invalid-parameter behavior; ASCII-
space-only splitting parity).
"""

from __future__ import annotations

import pytest

from legoai_document.chunking import ChunkingRequest, ChunkingResult, chunk_text
from legoai_document.chunking.errors import ChunkingValidationError


@pytest.mark.parametrize("text", ["", "   ", "\n\n", "\t\t\t", "  \n \t "])
def test_whitespace_only_text_returns_empty_result(text: str) -> None:
    assert chunk_text(ChunkingRequest(text=text)) == ChunkingResult(chunks=())


@pytest.mark.parametrize("chunk_size", [0, -1, -512])
def test_non_positive_chunk_size_is_rejected(chunk_size: int) -> None:
    with pytest.raises(ChunkingValidationError):
        chunk_text(ChunkingRequest(text="a b c", chunk_size=chunk_size))


@pytest.mark.parametrize("overlap", [-1, -50])
def test_negative_overlap_is_rejected(overlap: int) -> None:
    with pytest.raises(ChunkingValidationError):
        chunk_text(ChunkingRequest(text="a b c", chunk_size=10, overlap=overlap))


@pytest.mark.parametrize(("chunk_size", "overlap"), [(50, 50), (50, 51), (10, 100)])
def test_overlap_at_or_above_chunk_size_is_rejected(
    chunk_size: int, overlap: int
) -> None:
    with pytest.raises(ChunkingValidationError):
        chunk_text(
            ChunkingRequest(text="a b c", chunk_size=chunk_size, overlap=overlap)
        )


def test_validation_precedes_computation_even_for_empty_text() -> None:
    # Parameter validation must occur before the empty-text short-circuit,
    # per SS6 of the design document ("validation MUST occur before the
    # main loop"), not merely before the loop body specifically.
    with pytest.raises(ChunkingValidationError):
        chunk_text(ChunkingRequest(text="", chunk_size=0))


def test_ascii_space_only_splitting_parity() -> None:
    # This is the deliberate parity hazard called out in the design
    # document: a naive `text.split()` port would treat tabs/newlines as
    # word boundaries. The characterized v1 behavior does not.
    assert (
        len(chunk_text(ChunkingRequest(text="a b")).chunks[0].content.split(" ")) == 2
    )
    assert chunk_text(ChunkingRequest(text="a b")).chunks[0].word_count == 2

    tab_result = chunk_text(ChunkingRequest(text="a\tb"))
    assert len(tab_result.chunks) == 1
    assert tab_result.chunks[0].word_count == 1
    assert tab_result.chunks[0].content == "a\tb"

    newline_result = chunk_text(ChunkingRequest(text="a\nb"))
    assert len(newline_result.chunks) == 1
    assert newline_result.chunks[0].word_count == 1
    assert newline_result.chunks[0].content == "a\nb"


def test_non_breaking_and_ideographic_space_are_not_split_points() -> None:
    non_breaking = "a b"  # U+00A0 NO-BREAK SPACE
    ideographic = "a　b"  # U+3000 IDEOGRAPHIC SPACE

    for text in (non_breaking, ideographic):
        result = chunk_text(ChunkingRequest(text=text))
        assert len(result.chunks) == 1
        assert result.chunks[0].word_count == 1
        assert result.chunks[0].content == text


def test_unicode_word_content_is_preserved_without_normalization() -> None:
    text = "café 日本語 \U0001f600 näive"
    result = chunk_text(ChunkingRequest(text=text))

    assert len(result.chunks) == 1
    assert result.chunks[0].content == text
    assert result.chunks[0].word_count == 4
