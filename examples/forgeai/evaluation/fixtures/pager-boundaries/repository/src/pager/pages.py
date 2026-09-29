"""Page slicing for simple listings."""


def page(items: list[str], number: int, size: int) -> list[str]:
    """Return page ``number`` (1-based) of ``items``, ``size`` items per page."""
    start = number * size
    return items[start : start + size]


def page_count(total: int, size: int) -> int:
    """Return how many pages are needed to show ``total`` items."""
    return total // size
