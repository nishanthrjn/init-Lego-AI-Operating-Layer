# lq1-hidden-acceptance: text-slug
from textkit.slug import slugify


def test_hidden_basic() -> None:
    assert slugify("Hello World") == "hello-world"


def test_hidden_collapses_runs() -> None:
    assert slugify("a  --  b") == "a-b"


def test_hidden_strips_edges() -> None:
    assert slugify("  Hi!  ") == "hi"


def test_hidden_keeps_digits() -> None:
    assert slugify("Room 101") == "room-101"


def test_hidden_only_separators() -> None:
    assert slugify("!!!") == ""
