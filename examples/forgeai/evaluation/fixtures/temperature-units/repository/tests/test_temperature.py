from units.temperature import to_celsius


def test_celsius_is_unchanged() -> None:
    assert to_celsius(100, "C") == 100
