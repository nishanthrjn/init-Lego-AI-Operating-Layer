"""M1 supplied-text contract: determinism, limits and explicit failures."""

from dataclasses import FrozenInstanceError

import pytest

from legoai_engineering.repository.api import inspect_text
from legoai_engineering.repository.values import (
    InspectionRequest,
    InspectionResult,
    RepositoryMatch,
    RepositoryText,
)


def test_order_first_occurrence_and_unicode_coordinates() -> None:
    files = (
        RepositoryText("z.py", "needle needle\nNEEDLE\nneedle"),
        RepositoryText("a.py", "😀needle\r\nother\u2028needle\n"),
    )
    expected = InspectionResult(
        (
            RepositoryMatch("a.py", 1, 2),
            RepositoryMatch("a.py", 2, 7),
            RepositoryMatch("z.py", 1, 1),
            RepositoryMatch("z.py", 3, 1),
        ),
        False,
    )
    assert inspect_text(InspectionRequest(files, "needle", 10)) == expected
    reversed_request = InspectionRequest(tuple(reversed(files)), "needle", 10)
    assert inspect_text(reversed_request) == expected


@pytest.mark.parametrize("text", ["", "unrelated\n", "NEEDLE"])
def test_no_matches(text: str) -> None:
    result = inspect_text(InspectionRequest((RepositoryText("a", text),), "needle", 1))
    assert result == InspectionResult((), False)
    assert inspect_text(InspectionRequest((), "needle", 1)) == result


def test_literal_query_and_distinct_case_labels() -> None:
    result = inspect_text(
        InspectionRequest(
            (RepositoryText("a", "[.*]"), RepositoryText("A", "[.*]")), "[.*]", 2
        )
    )
    assert tuple(match.path for match in result.matches) == ("A", "a")
    assert not result.truncated


def test_truncation_requires_an_additional_matching_line() -> None:
    exact = InspectionRequest((RepositoryText("a", "x\nx\nno"),), "x", 2)
    extra = InspectionRequest((RepositoryText("a", "x\nx\nx"),), "x", 2)
    assert not inspect_text(exact).truncated
    result = inspect_text(extra)
    assert result.truncated
    assert result.matches == inspect_text(exact).matches
    # A second occurrence on the same line is not an omitted matching line.
    repeated = InspectionRequest((RepositoryText("a", "x x"),), "x", 1)
    assert not inspect_text(repeated).truncated


@pytest.mark.parametrize(
    "path", ["", "/a", "a/", "a//b", ".", "..", "a/../b", "C:/a", "a\\b", "a\x00"]
)
def test_invalid_labels(path: str) -> None:
    with pytest.raises(ValueError):
        RepositoryText(path, "")


def test_text_and_label_bounds() -> None:
    RepositoryText("x" * 240, "x" * 65_536)
    with pytest.raises(ValueError):
        RepositoryText("x" * 241, "")
    with pytest.raises(ValueError):
        RepositoryText("a", "x" * 65_537)


def test_file_count_total_size_and_duplicates() -> None:
    InspectionRequest(tuple(RepositoryText(str(i), "") for i in range(128)), "x", 1)
    with pytest.raises(ValueError):
        oversized = tuple(RepositoryText(str(i), "") for i in range(129))
        InspectionRequest(oversized, "x", 1)
    maximum = tuple(RepositoryText(str(i), "x" * 65_536) for i in range(16))
    InspectionRequest(maximum, "x", 1)
    with pytest.raises(ValueError):
        InspectionRequest((*maximum, RepositoryText("extra", "x")), "x", 1)
    with pytest.raises(ValueError):
        InspectionRequest((RepositoryText("a", "x"), RepositoryText("a", "y")), "x", 1)


@pytest.mark.parametrize("query", ["", "x" * 257, "a\nb", "\r"])
def test_invalid_queries(query: str) -> None:
    with pytest.raises(ValueError):
        InspectionRequest((), query, 1)


@pytest.mark.parametrize("maximum", [0, -1, 1001])
def test_invalid_result_caps(maximum: int) -> None:
    with pytest.raises(ValueError):
        InspectionRequest((), "x", maximum)


def test_supported_extremes() -> None:
    InspectionRequest((), "x" * 256, 1000)
    result = inspect_text(
        InspectionRequest((RepositoryText("a", "x\n" * 1001),), "x", 1000)
    )
    assert len(result.matches) == 1000
    assert result.truncated
    last = inspect_text(
        InspectionRequest((RepositoryText("a", "\n" * 65_535 + "x"),), "x", 1)
    )
    assert last.matches == (RepositoryMatch("a", 65_536, 1),)


def test_wrong_types_are_not_coerced() -> None:
    with pytest.raises(TypeError):
        RepositoryText(1, "")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        RepositoryText("a", b"x")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        InspectionRequest([], "x", 1)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        InspectionRequest(("a",), "x", 1)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        InspectionRequest((), None, 1)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        InspectionRequest((), "x", True)
    with pytest.raises(TypeError):
        inspect_text(object())  # type: ignore[arg-type]


def test_immutable_values_and_safe_diagnostics() -> None:
    item = RepositoryText("sensitive-label", "private source")
    request = InspectionRequest((item,), "private", 1)
    with pytest.raises(FrozenInstanceError):
        item.text = "replacement"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        request.files = ()  # type: ignore[misc]
    result = inspect_text(request)
    for value in (item, request, result, *result.matches):
        assert "private" not in repr(value)
        assert "sensitive-label" not in repr(value)
    with pytest.raises(ValueError) as error:
        RepositoryText("private/../label", "private source")
    assert "private" not in str(error.value)


def test_result_contract_rejects_inconsistent_or_mutable_values() -> None:
    match = RepositoryMatch("a", 1, 1)
    with pytest.raises(TypeError):
        InspectionResult([match], False)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        InspectionResult(("a",), False)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        InspectionResult((), 0)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        InspectionResult((), True)
    with pytest.raises(ValueError):
        InspectionResult((match, match), False)
    with pytest.raises(ValueError):
        InspectionResult((RepositoryMatch("b", 1, 1), match), False)
    with pytest.raises(ValueError):
        InspectionResult((match,) * 1001, False)
    with pytest.raises(TypeError):
        RepositoryMatch("a", True, 1)
    with pytest.raises(ValueError):
        RepositoryMatch("a", 0, 1)
    with pytest.raises(ValueError):
        RepositoryMatch("a", 1, 65_537)
