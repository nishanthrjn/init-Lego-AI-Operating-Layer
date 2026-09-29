"""Stock reservation for a small inventory."""


def reserve(available: int, requested: int) -> int:
    """Return the stock left after reserving ``requested`` units."""
    return available - requested
