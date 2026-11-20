"""
Django Admin configurations for Master Data models with SimpleHistoryAdmin audit trails.
"""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from apps.masters.models import (
    BOM,
    BOMLine,
    Customer,
    CustomerPrice,
    Item,
    PriceList,
    PriceListLine,
    Product,
    Supplier,
    Unit,
)


class BOMLineInline(admin.TabularInline):
    model = BOMLine
    extra = 1
    autocomplete_fields = ["item", "display_unit"]


@admin.register(BOM)
class BOMAdmin(SimpleHistoryAdmin):
    list_display = [
        "product",
        "version",
        "batch_output_packets",
        "recipe_group",
        "yield_basis",
        "is_active",
    ]
    list_filter = ["is_active", "recipe_group"]
    search_fields = ["product__item__name", "recipe_group"]
    inlines = [BOMLineInline]


@admin.register(BOMLine)
class BOMLineAdmin(SimpleHistoryAdmin):
    list_display = ["bom", "item", "qty_base", "display_unit"]
    list_filter = ["bom__product"]
    search_fields = ["item__name", "bom__product__item__name"]


class PriceListLineInline(admin.TabularInline):
    model = PriceListLine
    extra = 1
    autocomplete_fields = ["product"]


@admin.register(PriceList)
class PriceListAdmin(SimpleHistoryAdmin):
    list_display = ["name", "customer_type", "is_default", "is_active"]
    list_filter = ["customer_type", "is_default", "is_active"]
    search_fields = ["name"]
    inlines = [PriceListLineInline]


@admin.register(PriceListLine)
class PriceListLineAdmin(SimpleHistoryAdmin):
    list_display = ["price_list", "product", "unit_price"]
    list_filter = ["price_list"]
    search_fields = ["product__item__name", "price_list__name"]


@admin.register(CustomerPrice)
class CustomerPriceAdmin(SimpleHistoryAdmin):
    list_display = ["customer", "product", "custom_price", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["customer__name", "product__item__name"]


@admin.register(Unit)
class UnitAdmin(SimpleHistoryAdmin):
    list_display = ["code", "name", "kind", "factor_to_base", "is_base"]
    list_filter = ["kind", "is_base"]
    search_fields = ["code", "name"]


@admin.register(Item)
class ItemAdmin(SimpleHistoryAdmin):
    list_display = [
        "code",
        "name",
        "item_type",
        "base_unit",
        "valuation_rate",
        "gst_rate",
        "is_active",
    ]
    list_filter = ["item_type", "is_active", "base_unit"]
    search_fields = ["code", "name"]


@admin.register(Product)
class ProductAdmin(SimpleHistoryAdmin):
    list_display = ["item", "pack_size_g", "packets_per_carton", "list_price"]
    search_fields = ["item__name", "item__code"]


class CustomerPriceInline(admin.TabularInline):
    model = CustomerPrice
    extra = 0
    autocomplete_fields = ["product"]


@admin.register(Customer)
class CustomerAdmin(SimpleHistoryAdmin):
    list_display = [
        "code",
        "name",
        "customer_type",
        "state_code",
        "gstin",
        "assigned_salesman",
        "is_active",
    ]
    list_filter = ["customer_type", "state_code", "is_active"]
    search_fields = ["code", "name", "gstin"]
    inlines = [CustomerPriceInline]


@admin.register(Supplier)
class SupplierAdmin(SimpleHistoryAdmin):
    list_display = ["code", "name", "state_code", "gstin", "is_active"]
    list_filter = ["state_code", "is_active"]
    search_fields = ["code", "name", "gstin"]
