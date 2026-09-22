"""`format_for_path` extension-to-`DocumentFormat` mapping."""

from __future__ import annotations

from pathlib import Path

import pytest
from legoai_document.parsing.values import DocumentFormat

from documind_app.app import UnrecognizedFileExtensionError, format_for_path


@pytest.mark.parametrize(
    ("suffix", "expected"),
    [
        (".txt", DocumentFormat.TEXT),
        (".TEXT", DocumentFormat.TEXT),
        (".md", DocumentFormat.MARKDOWN),
        (".markdown", DocumentFormat.MARKDOWN),
        (".html", DocumentFormat.HTML),
        (".htm", DocumentFormat.HTML),
        (".pdf", DocumentFormat.PDF),
    ],
)
def test_format_for_path_recognizes_supported_extensions(
    suffix: str, expected: DocumentFormat
) -> None:
    assert format_for_path(Path(f"document{suffix}")) is expected


def test_format_for_path_rejects_unrecognized_extension() -> None:
    with pytest.raises(UnrecognizedFileExtensionError, match="docx"):
        format_for_path(Path("document.docx"))
