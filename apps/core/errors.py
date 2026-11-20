"""
Domain Exceptions for the Order-to-Audit Food Manufacturing System.
"""


class DomainError(Exception):
    """Base exception for all domain and business rule violations."""

    pass


class InsufficientStock(DomainError):
    """Raised when an order, issue, or dispatch exceeds available stock."""

    def __init__(self, item, requested, available, shortage=None):
        self.item = item
        self.requested = requested
        self.available = available
        if shortage is not None:
            self.shortage = shortage
        elif requested is not None and available is not None:
            self.shortage = requested - available
        else:
            self.shortage = None

        msg = (
            f"Insufficient stock for item '{item}': "
            f"requested {requested}, available {available}, shortage {self.shortage}."
        )
        super().__init__(msg)


class UnitMismatch(DomainError):
    """Raised when attempting unit conversion across incompatible dimensional kinds."""

    def __init__(self, source_unit, target_unit, reason=None):
        self.source_unit = source_unit
        self.target_unit = target_unit
        self.reason = reason or (
            f"Cannot convert between incompatible unit kinds: '{source_unit}' and '{target_unit}'."
        )
        super().__init__(self.reason)


class IllegalTransition(DomainError):
    """Raised when an entity attempts an invalid state machine transition."""

    def __init__(self, entity, current_status, target_status):
        self.entity = entity
        self.current_status = current_status
        self.target_status = target_status
        msg = (
            f"Illegal status transition for {entity}: "
            f"cannot transition from '{current_status}' to '{target_status}'."
        )
        super().__init__(msg)
