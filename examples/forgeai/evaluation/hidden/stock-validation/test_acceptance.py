# lq1-hidden-acceptance: stock-validation
import pytest

from inventory.stock import reserve


def test_hidden_remaining_stock() -> None:
    assert reserve(7, 7) == 0
    assert reserve(9, 1) == 8


@pytest.mark.parametrize(
    ("available", "requested"), [(-5, 1), (3, 0), (3, -1), (3, 4), (0, 1)]
)
def test_hidden_rejects_invalid_requests(available: int, requested: int) -> None:
    with pytest.raises(ValueError):
        reserve(available, requested)
