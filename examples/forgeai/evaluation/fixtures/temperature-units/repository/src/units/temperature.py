"""Temperature conversion to degrees Celsius."""


def to_celsius(value: float, unit: str) -> float:
    """Convert ``value`` given in ``unit`` ("C" or "F") to degrees Celsius."""
    if unit == "C":
        return value
    return (value - 32) * 5 / 9
