# lq1-hidden-acceptance: temperature-units
import pytest

from units.temperature import to_celsius


def test_hidden_kelvin() -> None:
    assert to_celsius(0, "K") == pytest.approx(-273.15)


def test_hidden_case_insensitive() -> None:
    assert to_celsius(212, "f") == pytest.approx(100.0)
    assert to_celsius(5, "c") == 5


def test_hidden_fahrenheit_still_works() -> None:
    assert to_celsius(32, "F") == pytest.approx(0.0)


@pytest.mark.parametrize("unit", ["X", "", "R"])
def test_hidden_unknown_units_rejected(unit: str) -> None:
    with pytest.raises(ValueError):
        to_celsius(1, unit)
