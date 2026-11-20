"""
Data migration seeding Unit table from UNIT_DEFINITIONS in apps.core.units.
"""

from django.db import migrations

CANONICAL_NAMES = {
    "g": "Gram",
    "kg": "Kilogram",
    "ml": "Millilitre",
    "l": "Litre",
    "pc": "Piece",
    "packet": "Packet",
    "pouch": "Pouch",
}


def seed_units(apps, schema_editor):
    Unit = apps.get_model("masters", "Unit")
    from apps.core.units import UNIT_DEFINITIONS

    canonical_codes = ["g", "kg", "ml", "l", "pc", "packet", "pouch"]
    base_units = {"g", "ml", "pc"}

    for code in canonical_codes:
        if code in UNIT_DEFINITIONS:
            kind, factor = UNIT_DEFINITIONS[code]
            name = CANONICAL_NAMES.get(code, code.title())
            Unit.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "kind": kind,
                    "factor_to_base": factor,
                    "is_base": code in base_units,
                },
            )


def unseed_units(apps, schema_editor):
    Unit = apps.get_model("masters", "Unit")
    canonical_codes = ["g", "kg", "ml", "l", "pc", "packet", "pouch"]
    Unit.objects.filter(code__in=canonical_codes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("masters", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_units, reverse_code=unseed_units),
    ]
