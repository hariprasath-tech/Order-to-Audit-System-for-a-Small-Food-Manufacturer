"""
Domain services for master data and pricing resolution.
"""

from decimal import Decimal
from typing import Optional

from apps.core.money import money
from apps.masters.models import Customer, CustomerPrice, PriceListLine, Product


def resolve_product_price(customer: Optional[Customer], product: Product) -> Decimal:
    """
    Resolves the applicable selling price per packet for a given customer and product.

    Resolution hierarchy:
    1. Direct active CustomerPrice override for (customer, product).
    2. Active PriceListLine for customer's specific customer_type (RETAILER or DISTRIBUTOR).
    3. Active PriceListLine in default price list (is_default=True).
    4. Active PriceListLine for customer_type='ALL'.
    5. Fallback to Product default list_price.

    Returns:
        Decimal(14, 2) quantized monetary amount.
    """
    if customer is not None:
        # 1. Direct active CustomerPrice override
        custom_price_record = (
            CustomerPrice.objects.filter(
                customer=customer,
                product=product,
                is_active=True,
            )
            .order_by("-id")
            .first()
        )
        if custom_price_record is not None:
            return money(custom_price_record.custom_price)

        # 2. Specific PriceList matching customer_type (RETAILER / DISTRIBUTOR)
        customer_type_line = (
            PriceListLine.objects.filter(
                price_list__customer_type=customer.customer_type,
                price_list__is_active=True,
                product=product,
            )
            .order_by("-id")
            .first()
        )
        if customer_type_line is not None:
            return money(customer_type_line.unit_price)

    # 3. Default PriceList
    default_price_line = (
        PriceListLine.objects.filter(
            price_list__is_default=True,
            price_list__is_active=True,
            product=product,
        )
        .order_by("-id")
        .first()
    )
    if default_price_line is not None:
        return money(default_price_line.unit_price)

    # 4. Fallback to customer_type='ALL' active list
    all_type_line = (
        PriceListLine.objects.filter(
            price_list__customer_type="ALL",
            price_list__is_active=True,
            product=product,
        )
        .order_by("-id")
        .first()
    )
    if all_type_line is not None:
        return money(all_type_line.unit_price)

    # 5. Product default list price
    return money(product.list_price)
