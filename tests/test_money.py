"""
Unit tests for core monetary and decimal arithmetic.
Strictly verifies float rejection, boolean rejection, non-finite rejection, and statutory ROUND_HALF_UP accuracy.
"""

from decimal import Decimal, getcontext

import pytest

from apps.core.money import money, qty, rate, to_decimal


class TestMoney:
    """Verifies currency conversion, precision, context, and input type rejections."""

    def test_decimal_context_precision(self):
        """Module-level decimal context must be initialized to 28 digits."""
        assert getcontext().prec == 28

    def test_float_strictly_rejected(self):
        """Float inputs must immediately raise TypeError."""
        with pytest.raises(TypeError, match="Float values are strictly prohibited"):
            money(10.5)

        with pytest.raises(TypeError, match="Float values are strictly prohibited"):
            rate(43.125)

        with pytest.raises(TypeError, match="Float values are strictly prohibited"):
            qty(19.5)

        with pytest.raises(TypeError, match="Float values are strictly prohibited"):
            to_decimal(0.005, places=2)

    def test_boolean_strictly_rejected(self):
        """Boolean values (subclass of int) must raise TypeError."""
        with pytest.raises(TypeError, match="Boolean values cannot be converted"):
            money(True)

        with pytest.raises(TypeError, match="Boolean values cannot be converted"):
            money(False)

        with pytest.raises(TypeError, match="Boolean values cannot be converted"):
            rate(True)

        with pytest.raises(TypeError, match="Boolean values cannot be converted"):
            qty(False)

    def test_non_finite_rejected(self):
        """NaN and Infinity must raise ValueError."""
        with pytest.raises(ValueError, match="Non-finite decimal values"):
            money("NaN")

        with pytest.raises(ValueError, match="Non-finite decimal values"):
            money(Decimal("NaN"))

        with pytest.raises(ValueError, match="Non-finite decimal values"):
            rate("Infinity")

        with pytest.raises(ValueError, match="Non-finite decimal values"):
            qty("-Infinity")

    def test_round_half_up_exactness(self):
        """Statutory half-up rounding boundary checks."""
        assert money("0.005") == Decimal("0.01")
        assert money("0.015") == Decimal("0.02")
        assert money("187.495") == Decimal("187.50")
        assert money("187.494") == Decimal("187.49")
        assert money("0.004") == Decimal("0.00")

    def test_rate_precision_four_places(self):
        """Unit costs and rates must preserve 4 decimal places."""
        assert rate("43.125") == Decimal("43.1250")
        assert rate("43.12505") == Decimal("43.1251")
        assert rate("43.12504") == Decimal("43.1250")
        assert rate(140) == Decimal("140.0000")

    def test_qty_precision_four_places(self):
        """Inventory quantities must preserve 4 decimal places."""
        assert qty("19.5") == Decimal("19.5000")
        assert qty("100.12345") == Decimal("100.1235")
        assert qty("100.12344") == Decimal("100.1234")
        assert qty(200) == Decimal("200.0000")

    def test_integer_and_string_inputs(self):
        """Integer and string literals must convert cleanly."""
        assert money(100) == Decimal("100.00")
        assert money("7875.00") == Decimal("7875.00")
        assert money(" -3875.50 ") == Decimal("-3875.50")

    def test_invalid_and_none_inputs(self):
        """None and invalid literals must raise appropriate exceptions."""
        with pytest.raises(TypeError):
            money(None)

        with pytest.raises(ValueError):
            money("invalid-amount")
