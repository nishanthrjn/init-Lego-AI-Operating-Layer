"""Exact canonical decimals, independent of the ambient decimal context.

Everything here works on the ``(sign, digits, exponent)`` tuple with Python
integers. No ``Decimal`` arithmetic runs, so the thread's precision,
rounding mode and traps cannot change a result. Bounds are checked on the
tuple before any digit expansion, so a huge exponent or coefficient is
rejected without being materialized.
"""

from decimal import Decimal

MAX_INTEGER_DIGITS = 64
MAX_FRACTION_DIGITS = 64

_ZERO = Decimal((0, (0,), 0))


def canonical(sign: int, digits: tuple[int, ...], exponent: int) -> Decimal | None:
    """Return the exact canonical Decimal, or None outside the bounds.

    Canonical form: no leading zeros, no trailing fractional zeros, exponent
    zero for integers, and zero is always unsigned ``0``. Its fixed-point
    text has at most ``MAX_INTEGER_DIGITS`` integer and
    ``MAX_FRACTION_DIGITS`` fraction digits.
    """
    first = next((index for index, digit in enumerate(digits) if digit != 0), None)
    if first is None:
        return _ZERO
    end = len(digits)
    while digits[end - 1] == 0:
        end -= 1
    exponent += len(digits) - end
    coefficient = digits[first:end]
    if exponent >= 0:
        if len(coefficient) + exponent > MAX_INTEGER_DIGITS:
            return None
        return Decimal((sign, coefficient + (0,) * exponent, 0))
    if -exponent > MAX_FRACTION_DIGITS:
        return None
    if len(coefficient) + exponent > MAX_INTEGER_DIGITS:
        return None
    return Decimal((sign, coefficient, exponent))


def canonical_of(value: Decimal) -> Decimal | None:
    """Canonical form of a finite Decimal; None if non-finite or out of bounds."""
    if not value.is_finite():
        return None
    parts = value.as_tuple()
    exponent = parts.exponent
    if type(exponent) is not int:
        return None
    return canonical(parts.sign, parts.digits, exponent)


def is_canonical(value: Decimal) -> bool:
    result = canonical_of(value)
    return result is not None and result.as_tuple() == value.as_tuple()


def scaled(value: Decimal) -> int:
    """Exact integer ``value * 10**MAX_FRACTION_DIGITS`` of a canonical value."""
    parts = value.as_tuple()
    exponent = parts.exponent
    if type(exponent) is not int:
        raise ValueError("canonical decimal required")
    # Canonical exponents are >= -MAX_FRACTION_DIGITS, so this power is integral.
    factor: int = 10 ** (exponent + MAX_FRACTION_DIGITS)
    magnitude = int("".join(str(digit) for digit in parts.digits)) * factor
    return -magnitude if parts.sign else magnitude


def is_integral(value: Decimal) -> bool:
    exponent = value.as_tuple().exponent
    return type(exponent) is int and exponent >= 0


def text(value: Decimal) -> str:
    """Fixed-point text of a canonical value, built from its digits."""
    parts = value.as_tuple()
    exponent = parts.exponent
    if type(exponent) is not int:
        raise ValueError("canonical decimal required")
    digits = "".join(str(digit) for digit in parts.digits)
    if exponent < 0:
        places = -exponent
        digits = digits.rjust(places + 1, "0")
        digits = digits[:-places] + "." + digits[-places:]
    return "-" + digits if parts.sign else digits
