"""document.chunking v1 -- sliding-window word-count chunking.

Behavior (see CHUNKING-CAPABILITY-DESIGN.md SS4, SS12 for the full
characterization this implementation is required to match):

- window unit: words
- default chunk_size: 512, default overlap: 50
- splitting rule for word boundaries: ASCII U+0020 space only, empty
  entries removed -- deliberately NOT ``str.split()`` (general Unicode
  whitespace), to preserve parity with the characterized DocuMind
  behavior for tabs, newlines and non-breaking/ideographic spaces.
- the empty-input guard uses a broader whitespace-only test (mirroring
  .NET's ``string.IsNullOrWhiteSpace``), which is intentionally not the
  same rule as the word splitter -- this dual behavior is exactly what
  both DocuMind oracles implement and is preserved deliberately, not by
  oversight.
- output order is stable; indices are zero-based and gapless.
- parameters are validated before any computation; invalid parameters
  raise ChunkingValidationError rather than reproducing the source
  oracle's defects (a crash for chunk_size <= 0, silent word loss for
  overlap < 0, and an infinite loop for overlap >= chunk_size).

Pure, stateless, effect-free: no I/O, no persistence, no network access,
and the input ``ChunkingRequest`` is never mutated.
"""

from __future__ import annotations

from legoai_document.chunking.errors import ChunkingValidationError
from legoai_document.chunking.values import Chunk, ChunkingRequest, ChunkingResult


def chunk_text(request: ChunkingRequest) -> ChunkingResult:
    """Split ``request.text`` into overlapping ASCII-space-delimited word windows.

    Raises:
        ChunkingValidationError: if ``chunk_size <= 0``, ``overlap < 0``,
            or ``overlap >= chunk_size``.
    """
    if request.chunk_size <= 0:
        raise ChunkingValidationError(
            f"chunk_size must be a positive integer, got {request.chunk_size!r}"
        )
    if request.overlap < 0:
        raise ChunkingValidationError(
            f"overlap must not be negative, got {request.overlap!r}"
        )
    if request.overlap >= request.chunk_size:
        raise ChunkingValidationError(
            "overlap must be strictly less than chunk_size, got "
            f"overlap={request.overlap!r} chunk_size={request.chunk_size!r}"
        )

    if request.text.strip() == "":
        return ChunkingResult(chunks=())

    words = [word for word in request.text.split(" ") if word != ""]
    step = request.chunk_size - request.overlap

    chunks: list[Chunk] = []
    start = 0
    index = 0
    total = len(words)
    while start < total:
        end = min(start + request.chunk_size, total)
        window = words[start:end]
        chunks.append(
            Chunk(index=index, content=" ".join(window), word_count=len(window))
        )
        index += 1
        start += step

    return ChunkingResult(chunks=tuple(chunks))
