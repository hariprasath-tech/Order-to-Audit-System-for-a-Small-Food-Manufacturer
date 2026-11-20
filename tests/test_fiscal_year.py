"""
Unit tests for Indian Financial Year (FY) calculation and boundaries.
"""

from datetime import date

import pytest

from apps.core.fiscal_year import fy_bounds, fy_label


class TestFiscalYear:
    """Verifies FY boundaries, edge cases, and labels."""

    def test_fy_boundary_march_31_vs_april_1(self):
        """
        31 March belongs to the preceding fiscal year;
        1 April begins the new fiscal year.
        """
        # March 31, 2026 is the last day of FY 2025-26
        assert fy_label(date(2026, 3, 31)) == "2025-26"

        # April 1, 2026 is the first day of FY 2026-27
        assert fy_label(date(2026, 4, 1)) == "2026-27"

        # Mid-year dates
        assert fy_label(date(2026, 11, 20)) == "2026-27"
        assert fy_label(date(2027, 1, 15)) == "2026-27"

    def test_fy_bounds_calculation(self):
        """Verifies start and end date bounds for a given label."""
        start_date, end_date = fy_bounds("2026-27")
        assert start_date == date(2026, 4, 1)
        assert end_date == date(2027, 3, 31)

        start_date, end_date = fy_bounds("2025-26")
        assert start_date == date(2025, 4, 1)
        assert end_date == date(2026, 3, 31)

    def test_invalid_fy_label_error(self):
        """Malformed FY labels must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid FY label format"):
            fy_bounds("2026")

        with pytest.raises(ValueError, match="Invalid FY label format"):
            fy_bounds("2026/27")

        with pytest.raises(ValueError, match="Invalid year in FY label"):
            fy_bounds("invalid-27")
