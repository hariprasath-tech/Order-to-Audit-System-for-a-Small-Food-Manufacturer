"""
Unit Conversion Module for Food Factory Inventory.
Pure Decimal dimensional conversions between mass, volume, and count units.

IMPORTANT ARCHITECTURAL RULE:
Ledger stock records and inventory ledger movements MUST ALWAYS be stored in
their canonical base units (e.g. grams for mass, millilitres for volume, pieces for count).
Conversions (such as grams to kilograms for UI displays or invoices) are presentation-only.
Never convert quantities to a higher unit and then store back to the database,
as quantizing intermediate values to 4 decimal places can cause truncation loss
for sub-fractional quantities.
"""

from decimal import Decimal

from apps.core.errors import UnitMismatch
from apps.core.money import qty

# Base unit dimensions:
#   mass: g (grams)
#   volume: ml (millilitres)
#   count: pc (pieces / packets)
UNIT_DEFINITIONS = {
    # Mass
    "g": ("mass", Decimal("1")),
    "gram": ("mass", Decimal("1")),
    "grams": ("mass", Decimal("1")),
    "kg": ("mass", Decimal("1000")),
    "kilogram": ("mass", Decimal("1000")),
    "kilograms": ("mass", Decimal("1000")),
    # Volume
    "ml": ("volume", Decimal("1")),
    "millilitre": ("volume", Decimal("1")),
    "millilitres": ("volume", Decimal("1")),
    "milliliter": ("volume", Decimal("1")),
    "l": ("volume", Decimal("1000")),
    "litre": ("volume", Decimal("1000")),
    "litres": ("volume", Decimal("1000")),
    "liter": ("volume", Decimal("1000")),
    "liters": ("volume", Decimal("1000")),
    # Count
    "pc": ("count", Decimal("1")),
    "piece": ("count", Decimal("1")),
    "pieces": ("count", Decimal("1")),
    "packet": ("count", Decimal("1")),
    "packets": ("count", Decimal("1")),
    "pouch": ("count", Decimal("1")),
    "pouches": ("count", Decimal("1")),
}


def convert(quantity, from_unit: str, to_unit: str) -> Decimal:
    """
    Converts a quantity between units of the same dimensional kind using pure Decimal.
    Raises UnitMismatch if units belong to different kinds or are unrecognized.
    """
    q = qty(quantity)
    u_from = str(from_unit).strip().lower()
    u_to = str(to_unit).strip().lower()

    if u_from == u_to:
        return q

    if u_from not in UNIT_DEFINITIONS:
        raise UnitMismatch(from_unit, to_unit, f"Unknown source unit: '{from_unit}'.")
    if u_to not in UNIT_DEFINITIONS:
        raise UnitMismatch(from_unit, to_unit, f"Unknown target unit: '{to_unit}'.")

    kind_from, factor_from = UNIT_DEFINITIONS[u_from]
    kind_to, factor_to = UNIT_DEFINITIONS[u_to]

    if kind_from != kind_to:
        raise UnitMismatch(
            from_unit,
            to_unit,
            f"Cannot convert between incompatible dimensional kinds: '{from_unit}' ({kind_from}) and '{to_unit}' ({kind_to}).",
        )

    base_quantity = q * factor_from
    converted_quantity = base_quantity / factor_to
    return qty(converted_quantity)
