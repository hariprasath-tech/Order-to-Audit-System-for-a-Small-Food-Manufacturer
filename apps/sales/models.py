"""
Sales Order and Line Models for Order-to-Audit Food Manufacturing System.
Tracks on-field salesman orders from Draft through Submission to Admin Verification,
Invoicing, and Dispatch.
Strictly zero floating-point model fields.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.core.fiscal_year import fy_label
from apps.core.money import money, qty
from apps.masters.models import Customer, Product


class Order(models.Model):
    """
    Sales order placed by on-field sales representatives for wholesale customers.
    Lifecycle:
      DRAFT -> SUBMITTED -> VERIFIED -> INVOICED -> DISPATCHED (or REJECTED)
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"
        INVOICED = "INVOICED", "Invoiced"
        DISPATCHED = "DISPATCHED", "Dispatched"

    order_number = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        help_text="Unique sequence number formatted per Indian FY (e.g. SO-2026-27-0001).",
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="orders",
        help_text="Wholesale customer placing the order.",
    )
    salesman = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sales_orders",
        help_text="Sales representative who captured this order.",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Current state in the Order-to-Audit lifecycle.",
    )
    order_date = models.DateField(
        default=timezone.now,
        help_text="Date when the order was entered.",
    )
    subtotal = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Sum of taxable line amounts before GST.",
    )
    cgst_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Total Central GST (for intrastate supply within Tamil Nadu).",
    )
    sgst_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Total State GST (for intrastate supply within Tamil Nadu).",
    )
    igst_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Total Integrated GST (for interstate supply).",
    )
    total_tax = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Total tax liability (CGST + SGST or IGST).",
    )
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Grand total invoiceable order amount including all taxes.",
    )
    notes = models.TextField(
        blank=True,
        default="",
        help_text="Optional remarks, delivery preferences, or customer notes.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-order_date", "-id"]
        verbose_name = "Sales Order"
        verbose_name_plural = "Sales Orders"

    def __str__(self):
        return f"{self.order_number} - {self.customer.name} [₹{self.total_amount}] ({self.status})"

    @classmethod
    def generate_order_number(cls, order_date=None) -> str:
        """
        Generates an Indian FY-based order number: SO-YYYY-YY-NNNN.
        Uses sequential suffix per financial year.
        """
        d = order_date or timezone.now().date()
        fy = fy_label(d)
        prefix = f"SO-{fy}-"

        last_order = (
            cls.objects.filter(order_number__startswith=prefix).order_by("-order_number").first()
        )
        if last_order:
            try:
                seq = int(last_order.order_number.replace(prefix, "")) + 1
            except ValueError:
                seq = cls.objects.filter(order_number__startswith=prefix).count() + 1
        else:
            seq = 1

        return f"{prefix}{seq:04d}"

    def recalculate_totals(self, save: bool = True):
        """
        Recomputes taxable subtotal, CGST, SGST, IGST, and total_amount from order lines.
        Place of supply logic:
          - If customer.state_code == settings.SELLER_STATE_CODE ("33"):
              Intrastate supply: CGST (gst_rate / 2) + SGST (gst_rate / 2)
          - Else:
              Interstate supply: IGST (gst_rate)
        """
        seller_state = getattr(settings, "SELLER_STATE_CODE", "33")
        is_intrastate = self.customer.state_code == seller_state

        subtotal = Decimal("0.00")
        cgst_sum = Decimal("0.00")
        sgst_sum = Decimal("0.00")
        igst_sum = Decimal("0.00")

        for line in self.lines.all():
            line_qty = qty(line.quantity)
            line_price = money(line.unit_price)
            line_taxable = money(line_qty * line_price)
            gst_rate = line.gst_rate

            if is_intrastate:
                # 50% CGST + 50% SGST
                half_rate = gst_rate / Decimal("2.00")
                line_cgst = money(line_taxable * (half_rate / Decimal("100.00")))
                line_sgst = money(line_taxable * (half_rate / Decimal("100.00")))
                line_igst = Decimal("0.00")
            else:
                line_cgst = Decimal("0.00")
                line_sgst = Decimal("0.00")
                line_igst = money(line_taxable * (gst_rate / Decimal("100.00")))

            line_total = line_taxable + line_cgst + line_sgst + line_igst

            line.taxable_amount = line_taxable
            line.cgst_amount = line_cgst
            line.sgst_amount = line_sgst
            line.igst_amount = line_igst
            line.line_total = line_total
            line.save(
                update_fields=[
                    "taxable_amount",
                    "cgst_amount",
                    "sgst_amount",
                    "igst_amount",
                    "line_total",
                ]
            )

            subtotal += line_taxable
            cgst_sum += line_cgst
            sgst_sum += line_sgst
            igst_sum += line_igst

        self.subtotal = money(subtotal)
        self.cgst_amount = money(cgst_sum)
        self.sgst_amount = money(sgst_sum)
        self.igst_amount = money(igst_sum)
        self.total_tax = money(cgst_sum + sgst_sum + igst_sum)
        self.total_amount = money(self.subtotal + self.total_tax)

        if save:
            self.save(
                update_fields=[
                    "subtotal",
                    "cgst_amount",
                    "sgst_amount",
                    "igst_amount",
                    "total_tax",
                    "total_amount",
                ]
            )


class OrderLine(models.Model):
    """
    Individual catalog line item in a sales order.
    Enforces pure Decimal monetary and quantity integrity.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_lines",
        help_text="Finished good product pack.",
    )
    quantity = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        default=Decimal("1.0000"),
        help_text="Ordered quantity in packets / consumer units.",
    )
    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Agreed selling price per packet excluding GST.",
    )
    gst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("5.00"),
        help_text="Statutory GST percentage at the time of order.",
    )
    taxable_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Taxable line subtotal (quantity * unit_price).",
    )
    cgst_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    sgst_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    igst_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    line_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Total line amount including taxes.",
    )

    history = HistoricalRecords()

    class Meta:
        ordering = ["id"]
        verbose_name = "Sales Order Line"
        verbose_name_plural = "Sales Order Lines"

    def __str__(self):
        return f"{self.order.order_number}: {self.product.item.name} ({self.quantity} pkts @ ₹{self.unit_price})"
