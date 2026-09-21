"""Invariant checks over a range of chunk_size/overlap combinations.

Ordinary pytest parametrization is used rather than a property-testing
library, per the authorized decision to avoid adding a new test
dependency solely for this batch (the repository does not already use
one).
"""

from __future__ import annotations

import pytest

from legoai_document.chunking import ChunkingRequest, chunk_text

WORD_COUNTS = [0, 1, 7, 100, 999]
CHUNK_SIZES = [1, 5, 50, 512]
OVERLAPS = [0, 1, 4, 49]


@pytest.mark.parametrize("word_count", WORD_COUNTS)
@pytest.mark.parametrize("chunk_size", CHUNK_SIZES)
@pytest.mark.parametrize("overlap", OVERLAPS)
def test_indices_are_zero_based_and_gapless(
    word_count: int, chunk_size: int, overlap: int
) -> None:
    if overlap >= chunk_size:
        pytest.skip("invalid combination covered by characterization tests")
    text = " ".join(f"w{i}" for i in range(word_count))

    result = chunk_text(
        ChunkingRequest(text=text, chunk_size=chunk_size, overlap=overlap)
    )

    assert [chunk.index for chunk in result.chunks] == list(range(len(result.chunks)))


@pytest.mark.parametrize("word_count", WORD_COUNTS)
@pytest.mark.parametrize("chunk_size", CHUNK_SIZES)
@pytest.mark.parametrize("overlap", OVERLAPS)
def test_every_produced_chunk_is_non_empty(
    word_count: int, chunk_size: int, overlap: int
) -> None:
    if overlap >= chunk_size:
        pytest.skip("invalid combination covered by characterization tests")
    text = " ".join(f"w{i}" for i in range(word_count))

    result = chunk_text(
        ChunkingRequest(text=text, chunk_size=chunk_size, overlap=overlap)
    )

    assert all(chunk.content != "" and chunk.word_count > 0 for chunk in result.chunks)


@pytest.mark.parametrize("word_count", WORD_COUNTS)
@pytest.mark.parametrize("chunk_size", CHUNK_SIZES)
@pytest.mark.parametrize("overlap", OVERLAPS)
def test_word_count_matches_ascii_space_delimited_words(
    word_count: int, chunk_size: int, overlap: int
) -> None:
    if overlap >= chunk_size:
        pytest.skip("invalid combination covered by characterization tests")
    text = " ".join(f"w{i}" for i in range(word_count))

    result = chunk_text(
        ChunkingRequest(text=text, chunk_size=chunk_size, overlap=overlap)
    )

    for chunk in result.chunks:
        assert chunk.word_count == len([w for w in chunk.content.split(" ") if w != ""])


@pytest.mark.parametrize("chunk_size", CHUNK_SIZES)
@pytest.mark.parametrize("overlap", OVERLAPS)
def test_every_valid_invocation_terminates(chunk_size: int, overlap: int) -> None:
    # A valid (overlap < chunk_size) request over non-trivial input must
    # make forward progress and terminate; this guards against
    # regressing the source oracle's overlap>=chunk_size infinite loop
    # defect for the boundary just inside the valid range.
    if overlap >= chunk_size:
        pytest.skip("invalid combination covered by characterization tests")
    text = " ".join(f"w{i}" for i in range(2000))

    result = chunk_text(
        ChunkingRequest(text=text, chunk_size=chunk_size, overlap=overlap)
    )

    assert len(result.chunks) >= 1


@pytest.mark.parametrize("word_count", [0, 1, 50, 500])
def test_same_request_produces_same_result_across_calls(word_count: int) -> None:
    request = ChunkingRequest(
        text=" ".join(f"w{i}" for i in range(word_count)), chunk_size=17, overlap=3
    )
    assert chunk_text(request) == chunk_text(request)
