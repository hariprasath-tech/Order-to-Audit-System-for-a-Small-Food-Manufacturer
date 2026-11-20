"""
Django Admin Configuration for Sales Orders.
"""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from apps.sales.models import Order, OrderLine


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0
    fields = [
        "product",
        "quantity",
        "unit_price",
        "gst_rate",
        "taxable_amount",
        "cgst_amount",
        "sgst_amount",
        "igst_amount",
        "line_total",
    ]
    readonly_fields = [
        "taxable_amount",
        "cgst_amount",
        "sgst_amount",
        "igst_amount",
        "line_total",
    ]


@admin.register(Order)
class OrderAdmin(SimpleHistoryAdmin):
    list_display = [
        "order_number",
        "customer",
        "salesman",
        "status",
        "order_date",
        "subtotal",
        "total_tax",
        "total_amount",
        "created_at",
    ]
    list_filter = ["status", "order_date", "customer__customer_type"]
    search_fields = ["order_number", "customer__name", "customer__code", "salesman__username"]
    inlines = [OrderLineInline]
    readonly_fields = [
        "order_number",
        "subtotal",
        "cgst_amount",
        "sgst_amount",
        "igst_amount",
        "total_tax",
        "total_amount",
        "created_at",
        "updated_at",
    ]
