"""
Domain Services for Sales Orders.
Handles order creation, automatic line calculations (CGST/SGST vs IGST),
and lifecycle status transitions under atomic database transactions.
Strictly zero floating-point math.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.money import money, qty
from apps.masters.models import Customer, Product
from apps.masters.services import resolve_product_price
from apps.sales.models import Order, OrderLine

User = get_user_model()


def calculate_line_taxes(
    customer: Customer,
    taxable_amount: Decimal,
    gst_rate: Decimal,
) -> Dict[str, Decimal]:
    """
    Computes CGST, SGST, IGST, and total tax based on customer state.
    Seller state defaults to settings.SELLER_STATE_CODE ("33" - Tamil Nadu).
    """
    seller_state = getattr(settings, "SELLER_STATE_CODE", "33")
    is_intrastate = customer.state_code == seller_state

    taxable = money(taxable_amount)
    gst = money(gst_rate)

    if is_intrastate:
        half_rate = gst / Decimal("2.00")
        cgst = money(taxable * (half_rate / Decimal("100.00")))
        sgst = money(taxable * (half_rate / Decimal("100.00")))
        igst = Decimal("0.00")
    else:
        cgst = Decimal("0.00")
        sgst = Decimal("0.00")
        igst = money(taxable * (gst / Decimal("100.00")))

    total_tax = cgst + sgst + igst
    line_total = taxable + total_tax

    return {
        "is_intrastate": is_intrastate,
        "taxable_amount": taxable,
        "cgst_amount": cgst,
        "sgst_amount": sgst,
        "igst_amount": igst,
        "total_tax": total_tax,
        "line_total": line_total,
    }


def create_sales_order(
    salesman: Any,
    customer: Customer,
    lines_data: List[Dict[str, Any]],
    status: str = Order.Status.DRAFT,
    notes: str = "",
    order_date: Optional[Any] = None,
) -> Order:
    """
    Atomically creates a Sales Order and its OrderLines.

    Args:
        salesman: User object representing the salesperson.
        customer: Active Customer object.
        lines_data: List of dicts containing 'product', 'quantity', and optional 'unit_price'.
        status: Order.Status (DRAFT or SUBMITTED).
        notes: Optional order remarks.
        order_date: Optional date object (defaults to today).

    Returns:
        Persisted and totaled Order instance.
    """
    if not customer.is_active:
        raise ValidationError(f"Customer '{customer.name}' is inactive and cannot place orders.")

    if not lines_data:
        raise ValidationError("At least one product line is required to place an order.")

    order_date = order_date or timezone.now().date()

    with transaction.atomic():
        order_num = Order.generate_order_number(order_date=order_date)
        order = Order.objects.create(
            order_number=order_num,
            customer=customer,
            salesman=salesman,
            status=status,
            order_date=order_date,
            notes=notes.strip() if notes else "",
        )

        for line_item in lines_data:
            product = line_item["product"]
            if isinstance(product, (int, str)):
                product = Product.objects.select_related("item").get(pk=product)

            q = qty(line_item.get("quantity", Decimal("1.0000")))
            if q <= Decimal("0.0000"):
                raise ValidationError(
                    f"Quantity for '{product.item.name}' must be greater than zero."
                )

            # Resolve price if not explicitly supplied
            if "unit_price" in line_item and line_item["unit_price"] is not None:
                p = money(line_item["unit_price"])
            else:
                p = resolve_product_price(customer, product)

            if p < Decimal("0.00"):
                raise ValidationError(f"Price for '{product.item.name}' cannot be negative.")

            gst_rate = money(product.item.gst_rate)

            OrderLine.objects.create(
                order=order,
                product=product,
                quantity=q,
                unit_price=p,
                gst_rate=gst_rate,
            )

        order.recalculate_totals(save=True)

    return order


def submit_sales_order(order: Order, user: Any) -> Order:
    """
    Submits an existing DRAFT sales order for Admin Desk verification.
    """
    if order.status != Order.Status.DRAFT:
        raise ValidationError(
            f"Only DRAFT orders can be submitted for verification. Order '{order.order_number}' is already '{order.status}'."
        )

    with transaction.atomic():
        order.status = Order.Status.SUBMITTED
        order.save(update_fields=["status", "updated_at"])

    return order
