"""
Unit tests and property-based verification for unit conversions.
"""

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from apps.core.errors import UnitMismatch
from apps.core.units import convert


class TestUnits:
    """Verifies mass, volume, and count conversions and rejection of incompatible kinds."""

    def test_mass_conversions(self):
        """Verifies kg <-> g conversions."""
        assert convert("1.5", "kg", "g") == Decimal("1500.0000")
        assert convert("250", "g", "kg") == Decimal("0.2500")
        assert convert("40", "kg", "g") == Decimal("40000.0000")
        assert convert("120000", "g", "kg") == Decimal("120.0000")

    def test_volume_conversions(self):
        """Verifies l <-> ml conversions."""
        assert convert("10.5", "litre", "ml") == Decimal("10500.0000")
        assert convert("750", "ml", "litre") == Decimal("0.7500")
        assert convert("19.5", "l", "ml") == Decimal("19500.0000")

    def test_count_conversions(self):
        """Verifies count unit identity."""
        assert convert(188, "packet", "pc") == Decimal("188.0000")
        assert convert("6", "pouch", "piece") == Decimal("6.0000")

    def test_incompatible_unit_mismatch(self):
        """Converting across incompatible dimensional kinds must raise UnitMismatch."""
        with pytest.raises(UnitMismatch, match="Cannot convert between incompatible"):
            convert("10", "kg", "litre")

        with pytest.raises(UnitMismatch, match="Cannot convert between incompatible"):
            convert("5", "ml", "g")

        with pytest.raises(UnitMismatch, match="Cannot convert between incompatible"):
            convert("100", "pc", "kg")

    def test_unknown_unit_error(self):
        """Unknown units must raise UnitMismatch."""
        with pytest.raises(UnitMismatch, match="Unknown source unit"):
            convert("10", "unknown_unit", "g")

        with pytest.raises(UnitMismatch, match="Unknown target unit"):
            convert("10", "kg", "unknown_unit")

    @given(st.decimals(min_value=Decimal("0.0001"), max_value=Decimal("999999.9999"), places=4))
    def test_hypothesis_round_trip_mass(self, q):
        """Hypothesis property test: round-trip conversion (kg -> g -> kg) preserves exact quantity."""
        converted = convert(convert(q, "kg", "g"), "g", "kg")
        assert converted == q

    @given(st.decimals(min_value=Decimal("0.0001"), max_value=Decimal("999999.9999"), places=4))
    def test_hypothesis_round_trip_volume(self, q):
        """Hypothesis property test: round-trip conversion (l -> ml -> l) preserves exact quantity."""
        converted = convert(convert(q, "l", "ml"), "ml", "l")
        assert converted == q
