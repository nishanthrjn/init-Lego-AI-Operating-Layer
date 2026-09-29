# lq1-hidden-acceptance: pager-boundaries
from pager.pages import page, page_count

ITEMS = ["a", "b", "c", "d", "e"]


def test_hidden_first_page() -> None:
    assert page(ITEMS, 1, 2) == ["a", "b"]


def test_hidden_last_partial_page() -> None:
    assert page(ITEMS, 3, 2) == ["e"]


def test_hidden_page_beyond_end_is_empty() -> None:
    assert page(ITEMS, 4, 2) == []


def test_hidden_page_count_rounding() -> None:
    assert page_count(5, 2) == 3
    assert page_count(4, 2) == 2
    assert page_count(0, 3) == 0
