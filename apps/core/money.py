"""
Core Monetary and Decimal Arithmetic Module.
Enforces pure-Decimal math with ROUND_HALF_UP and absolute float rejection.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, getcontext

# Set module-level decimal context with 28 places of precision and statutory half-up rounding
getcontext().prec = 28
getcontext().rounding = ROUND_HALF_UP

# Standard precision quantizers
MONEY_QUANT = Decimal("0.01")
RATE_QUANT = Decimal("0.0001")
QTY_QUANT = Decimal("0.0001")
UNIT_RATE_QUANT = Decimal("0.00000001")


def to_decimal(val, places=2) -> Decimal:
    """
    Converts a value to Decimal with the specified number of decimal places.
    Strictly forbids float inputs, boolean flags, NaN, and Infinity.
    """
    if isinstance(val, bool):
        raise TypeError(
            f"Boolean values cannot be converted to Decimal currency or quantity: {val!r}."
        )

    if isinstance(val, float):
        raise TypeError(
            f"Float values are strictly prohibited in financial calculations: {val!r}. "
            f"Pass Decimal, int, or string."
        )

    if val is None:
        raise TypeError("None cannot be converted to Decimal.")

    try:
        if isinstance(val, Decimal):
            d = val
        elif isinstance(val, (int, str)):
            d = Decimal(str(val).strip())
        else:
            raise TypeError(f"Unsupported type {type(val)} for Decimal conversion: {val!r}")
    except InvalidOperation as e:
        raise ValueError(f"Invalid decimal literal: {val!r}") from e

    if not d.is_finite():
        raise ValueError(f"Non-finite decimal values (NaN, Infinity) are prohibited: {val!r}")

    quant = Decimal("10") ** -places
    return d.quantize(quant, rounding=ROUND_HALF_UP)


def money(val) -> Decimal:
    """Returns Decimal rounded to 2 decimal places (paise/cents)."""
    return to_decimal(val, places=2)


def rate(val) -> Decimal:
    """Returns Decimal rounded to 4 decimal places for selling prices and tax rates."""
    return to_decimal(val, places=4)


def unit_rate(val) -> Decimal:
    """
    Returns Decimal rounded to 8 decimal places for inventory unit costs per base unit.

    PRECISION RULE:
    Costs per base unit (e.g. cost per gram of flour or spice, cost per ml of oil)
    require 8 decimal places of precision so moving weighted-average costs across
    bulk inventory purchases can be represented without truncation error.
    Example: ₹43.125 / kg = ₹0.04312500 / gram.
    4 decimal places truncates this to 0.0431, creating a cumulative ledger error.
    Rule: Intermediate unit costs per base unit use 8 decimal places;
    final total monetary amounts are quantized to 2 decimal places (paise) only at the end.
    """
    return to_decimal(val, places=8)


def qty(val) -> Decimal:
    """Returns Decimal rounded to 4 decimal places for material quantities and stock."""
    return to_decimal(val, places=4)
