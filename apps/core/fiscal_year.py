"""
Indian Financial Year (FY) Utilities.
Financial Year runs strictly from 1st April to 31st March.
"""

from datetime import date, datetime


def fy_label(d: date | datetime) -> str:
    """
    Returns the Indian Financial Year label for a given date in YYYY-YY format.
    Examples:
      date(2026, 4, 1)   -> '2026-27'
      date(2026, 3, 31)  -> '2025-26'
    """
    if isinstance(d, datetime):
        d = d.date()

    year = d.year
    if d.month < 4:
        start_year = year - 1
    else:
        start_year = year

    end_year_short = str(start_year + 1)[-2:]
    return f"{start_year}-{end_year_short}"


def fy_bounds(label: str) -> tuple[date, date]:
    """
    Returns the (start_date, end_date) bounding dates for a financial year label.
    Example:
      '2026-27' -> (date(2026, 4, 1), date(2027, 3, 31))
    """
    parts = label.strip().split("-")
    if len(parts) != 2:
        raise ValueError(f"Invalid FY label format: '{label}'. Expected 'YYYY-YY'.")

    try:
        start_year = int(parts[0])
    except ValueError as e:
        raise ValueError(f"Invalid year in FY label: '{label}'") from e

    return (date(start_year, 4, 1), date(start_year + 1, 3, 31))
