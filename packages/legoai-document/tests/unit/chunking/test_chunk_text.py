"""Behavioral contract for document.chunking, ported from both DocuMind
oracles (DocuMind-SK and DocuMind-AgentFramework ChunkingServiceTests --
byte-identical in both repos). See CHUNKING-CAPABILITY-DESIGN.md SS12.

The DocuMind `Chunk_AllChunksHaveCorrectDocumentId` case is deliberately
NOT ported: document correlation was removed from the pure semantic
result (SS2, SS9 of the design document), so there is nothing analogous
to assert here -- a caller attaching its own document identity after the
fact is not this capability's concern.
"""

from __future__ import annotations

from legoai_document.chunking import ChunkingRequest, ChunkingResult, chunk_text


def test_empty_text_returns_empty_result() -> None:
    result = chunk_text(ChunkingRequest(text=""))
    assert result == ChunkingResult(chunks=())


def test_short_text_returns_single_chunk() -> None:
    text = " ".join(["word"] * 100)
    result = chunk_text(ChunkingRequest(text=text, chunk_size=512))

    assert len(result.chunks) == 1
    assert result.chunks[0].index == 0
    assert result.chunks[0].word_count == 100


def test_long_text_produces_multiple_non_blank_chunks() -> None:
    text = " ".join(["word"] * 1000)
    result = chunk_text(ChunkingRequest(text=text, chunk_size=100, overlap=10))

    assert len(result.chunks) > 1
    assert all(chunk.content.strip() != "" for chunk in result.chunks)


def test_overlap_consecutive_chunks_share_words() -> None:
    words = [f"word{i}" for i in range(1, 201)]
    text = " ".join(words)
    result = chunk_text(ChunkingRequest(text=text, chunk_size=100, overlap=20))

    chunk0_last_20 = result.chunks[0].content.split(" ")[-20:]
    chunk1_first_20 = result.chunks[1].content.split(" ")[:20]
    assert chunk0_last_20 == chunk1_first_20


def test_chunk_indexes_are_sequential() -> None:
    text = " ".join(["word"] * 500)
    result = chunk_text(ChunkingRequest(text=text, chunk_size=100, overlap=10))

    assert [chunk.index for chunk in result.chunks] == list(range(len(result.chunks)))


def test_word_count_matches_content_word_count() -> None:
    text = " ".join(["word"] * 500)
    result = chunk_text(ChunkingRequest(text=text, chunk_size=100, overlap=10))

    for chunk in result.chunks:
        assert chunk.word_count == len(chunk.content.split(" "))


def test_result_and_chunks_are_immutable() -> None:
    request = ChunkingRequest(text="a b c")
    result = chunk_text(request)

    assert isinstance(result.chunks, tuple)
    for attribute in ("text", "chunk_size", "overlap"):
        try:
            setattr(request, attribute, "mutated")  # noqa: B010
        except AttributeError:
            pass
        else:
            raise AssertionError(f"ChunkingRequest.{attribute} was mutable")

    chunk = result.chunks[0]
    try:
        chunk.content = "mutated"  # type: ignore[misc]  # noqa: B010
    except AttributeError:
        pass
    else:
        raise AssertionError("Chunk.content was mutable")


def test_same_request_produces_same_result() -> None:
    request = ChunkingRequest(text=" ".join(["word"] * 250), chunk_size=64, overlap=8)
    assert chunk_text(request) == chunk_text(request)


def test_chunk_text_does_not_mutate_request() -> None:
    request = ChunkingRequest(text="alpha beta gamma", chunk_size=2, overlap=0)
    before = (request.text, request.chunk_size, request.overlap)

    chunk_text(request)

    assert (request.text, request.chunk_size, request.overlap) == before
