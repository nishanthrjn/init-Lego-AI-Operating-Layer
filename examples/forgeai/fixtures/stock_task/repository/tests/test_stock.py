from inventory.stock import reserve


def test_reserve_reduces_stock() -> None:
    assert reserve(10, 3) == 7
