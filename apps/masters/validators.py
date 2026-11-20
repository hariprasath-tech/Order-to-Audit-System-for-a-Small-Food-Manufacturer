"""
Validators for statutory Indian tax identification and state codes.
"""

import re

from django.core.exceptions import ValidationError

GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
STATE_CODE_REGEX = re.compile(r"^[0-9]{2}$")


def validate_state_code(val: str):
    """
    Validates that state code is exactly 2 numeric digits.
    Example: '33' for Tamil Nadu, '29' for Karnataka.
    """
    if not val or not STATE_CODE_REGEX.match(str(val).strip()):
        raise ValidationError(
            f"State code must be exactly 2 numeric digits (e.g. '33' for Tamil Nadu), got '{val}'."
        )


def validate_gstin(gstin: str, state_code: str = None):
    """
    Validates statutory Indian GSTIN format (15 characters alphanumeric).
    If state_code is provided, strictly enforces that the first two digits match.
    """
    if not gstin:
        return
    gstin_clean = str(gstin).strip().upper()
    if len(gstin_clean) != 15:
        raise ValidationError(
            f"GSTIN must be exactly 15 characters long, got {len(gstin_clean)} ('{gstin_clean}')."
        )
    if not GSTIN_REGEX.match(gstin_clean):
        raise ValidationError(
            f"Invalid GSTIN structure: '{gstin_clean}'. Expected statutory format (e.g. 33AAAAA0000A1Z5)."
        )
    if state_code:
        st = str(state_code).strip()
        if gstin_clean[:2] != st:
            raise ValidationError(
                f"GSTIN state prefix '{gstin_clean[:2]}' does not match entity state code '{st}'."
            )
