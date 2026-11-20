"""
Master Data Models for Order-to-Audit Food Manufacturing System.
Covers Units, Items, Products, Customers, Suppliers, Price Lists, and Bills of Materials (BOM).
All monetary values use DecimalField(14, 2), unit rates use DecimalField(18, 8), quantities (16, 4).
Strictly zero floating-point model fields allowed.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from apps.core.money import qty
from apps.masters.validators import validate_gstin, validate_state_code

# Standard Quantizers for Validation
MONEY_ZERO = Decimal("0.00")
RATE_ZERO = Decimal("0.0000")
UNIT_RATE_ZERO = Decimal("0.00000000")
QTY_ZERO = Decimal("0.0000")


class Unit(models.Model):
    """
    Physical unit of measurement for inventory and recipes.
    Base units: 'g' for mass, 'ml' for volume, 'pc' for count.
    """

    KIND_CHOICES = [
        ("mass", "Mass"),
        ("volume", "Volume"),
        ("count", "Count"),
    ]

    code = models.CharField(max_length=16, unique=True, db_index=True)
    name = models.CharField(max_length=64)
    kind = models.CharField(max_length=16, choices=KIND_CHOICES)
    factor_to_base = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        default=Decimal("1.0000"),
        help_text="Multiplier to convert this unit into the dimension's canonical base unit.",
    )
    is_base = models.BooleanField(
        default=False,
        help_text="True if this is the canonical base unit (g, ml, pc) stored in the ledger.",
    )

    history = HistoricalRecords()

    class Meta:
        ordering = ["kind", "code"]
        verbose_name = "Unit of Measure"
        verbose_name_plural = "Units of Measure"

    def __str__(self):
        return f"{self.name} ({self.code})"

    def convert_to(self, target_unit: "Unit", quantity) -> Decimal:
        """
        Converts quantity from this unit to target_unit using the table's factor_to_base.
        NOTE: This helper method is intended for UI display and reference presentation only.
        All ledger stock movements and core balance calculations MUST use
        apps.core.units.convert() with item.base_unit directly.
        """
        from apps.core.errors import UnitMismatch

        if self.kind != target_unit.kind:
            raise UnitMismatch(
                self.code,
                target_unit.code,
                f"Cannot convert between incompatible dimensional kinds: '{self.code}' ({self.kind}) and '{target_unit.code}' ({target_unit.kind}).",
            )
        q = qty(quantity)
        base_qty = q * self.factor_to_base
        converted = base_qty / target_unit.factor_to_base
        return qty(converted)


class Item(models.Model):
    """
    Single catalogue table for Raw Materials, Packaging Materials, and Finished Goods.
    All stock movements write to Item base unit quantities.
    """

    TYPE_CHOICES = [
        ("RAW", "Raw Material"),
        ("PACKAGING", "Packaging Material"),
        ("FINISHED", "Finished Good"),
    ]

    code = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=128)
    item_type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    base_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="items")
    hsn_code = models.CharField(max_length=16, default="2106")
    gst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("5.00"),
        help_text="Statutory GST rate percentage (e.g. 5.00, 12.00, 18.00).",
    )
    tolerance_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Specific production run variance tolerance override (default system 3.00%).",
    )
    reorder_level = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Minimum stock threshold in base unit for low-stock warnings.",
    )
    standard_rate = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        default=Decimal("0.00000000"),
        help_text="Opening/standard cost rate per base unit (8 decimal places). The running moving average is maintained on the stock balance in Phase 3.",
    )
    is_active = models.BooleanField(default=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["item_type", "code"]
        verbose_name = "Item"
        verbose_name_plural = "Items"

    def __str__(self):
        return f"[{self.item_type}] {self.name} ({self.code})"


class BOM(models.Model):
    """
    Bill of Materials (recipe) specifying raw material and packaging consumption per batch.

    SHARED RECIPE ARCHITECTURE:
    One master BOM record (e.g. 'Murukku Classic', 40,000 g bulk dough batch) serves multiple
    finished package sizes (e.g. 200g Murukku, 500g Murukku).
    - Raw dough material lines have `product=None` (shared across all products using this BOM).
    - Packaging component lines (consumer pouches, outer cartons) have `product` set to the specific pack size.
    - Expected output in saleable packets per batch = batch_output_g / product.pack_size_g
      (e.g. 40,000g / 200g = 200 packets; 40,000g / 500g = 80 packets).
    - Updating a shared raw material line (e.g. flour) once automatically updates raw material
      consumption for all products sharing this BOM.
    """

    name = models.CharField(max_length=64, default="Murukku Classic")
    version = models.PositiveIntegerField(default=1)
    batch_output_g = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("40000.00"),
        help_text="Expected bulk finished dough yield in grams per standard batch (e.g. 40,000.00 g = 40 kg).",
    )
    is_active = models.BooleanField(default=True)

    history = HistoricalRecords()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                condition=models.Q(is_active=True),
                name="unique_active_bom_per_name",
            ),
            models.UniqueConstraint(
                fields=["name", "version"],
                name="unique_bom_version_per_name",
            ),
        ]
        ordering = ["name", "-version"]
        verbose_name = "Bill of Materials (BOM)"
        verbose_name_plural = "Bills of Materials (BOMs)"

    def __str__(self):
        status = "Active" if self.is_active else "Archived"
        return f"{self.name} BOM v{self.version} ({int(self.batch_output_g)}g batch) [{status}]"

    def expected_packets(self, product: "Product") -> int:
        """Calculates expected finished packets per batch: batch_output_g / pack_size_g."""
        return int(self.batch_output_g / product.pack_size_g)

    def planned_consumption(
        self, product: "Product", batches: Decimal = Decimal("1.0000")
    ) -> list[dict]:
        """
        Returns planned component consumption for a given Product and batch count.
        Combines shared core dough ingredients (product is None) with product-specific packaging items.
        Scales: planned_qty = qty_base * batches.
        """
        b = qty(batches)
        lines = (
            self.lines.filter(models.Q(product__isnull=True) | models.Q(product=product))
            .select_related("item", "item__base_unit", "display_unit")
            .order_by("item__item_type", "item__name")
        )

        results = []
        for line in lines:
            results.append(
                {
                    "item": line.item,
                    "qty_base": qty(line.qty_base * b),
                    "display_unit": line.display_unit,
                    "is_shared": line.product is None,
                }
            )
        return results


class Product(models.Model):
    """
    Sales and commercial packaging profile for a FINISHED Item.
    Defines finished pack weight, outer carton packing, and list selling price.
    """

    item = models.OneToOneField(
        Item,
        on_delete=models.CASCADE,
        related_name="product_profile",
        limit_choices_to={"item_type": "FINISHED"},
    )
    bom = models.ForeignKey(
        BOM,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="products",
        help_text="Associated recipe Bill of Materials.",
    )
    pack_size_g = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Net mass per packet in grams (e.g. 200.00 for 200g Murukku).",
    )
    packets_per_carton = models.PositiveIntegerField(
        default=20,
        help_text="Number of consumer packets packed into an outer shipper carton.",
    )
    list_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Default list selling price per packet excluding GST (selling price before tax).",
    )

    history = HistoricalRecords()

    class Meta:
        ordering = ["item__name"]
        verbose_name = "Product Profile"
        verbose_name_plural = "Product Profiles"

    def __str__(self):
        return f"{self.item.name} ({int(self.pack_size_g)}g) - ₹{self.list_price}"

    def planned_consumption(self, batches: Decimal = Decimal("1.0000")) -> list[dict]:
        """Convenience delegation to associated BOM planned_consumption."""
        if not self.bom:
            raise ValueError(f"Product {self} has no BOM assigned.")
        return self.bom.planned_consumption(self, batches)


class BOMLine(models.Model):
    """Component line inside a Bill of Materials."""

    bom = models.ForeignKey(BOM, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="bom_packaging_lines",
        help_text="Null for shared bulk ingredients (dough); set for product-specific packaging items (pouches, cartons).",
    )
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="bom_usages")
    qty_base = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        help_text="Required quantity per batch stored in the Item's base unit (g, ml, pc).",
    )
    display_unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bom_display_lines",
        help_text="Optional human-friendly display unit (e.g. kg instead of g).",
    )

    history = HistoricalRecords()

    class Meta:
        ordering = ["item__item_type", "item__name"]
        verbose_name = "BOM Component Line"
        verbose_name_plural = "BOM Component Lines"

    def __str__(self):
        scope = f"[{self.product.item.name}]" if self.product else "[Shared]"
        return f"{self.bom.name} {scope}: {self.item.name} ({self.qty_base} {self.item.base_unit.code})"


class Customer(models.Model):
    """
    Wholesale customer account (Retailer or Distributor).
    Tracks GSTIN, destination state for IGST vs CGST/SGST, and assigned salesperson.
    """

    TYPE_CHOICES = [
        ("RETAILER", "Retailer"),
        ("DISTRIBUTOR", "Distributor"),
    ]

    code = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=128)
    customer_type = models.CharField(max_length=16, choices=TYPE_CHOICES, default="RETAILER")
    gstin = models.CharField(max_length=15, blank=True, null=True)
    state_code = models.CharField(
        max_length=2,
        default="33",
        help_text="Two-digit Indian state code (e.g. 33 for Tamil Nadu, 29 for Karnataka).",
    )
    assigned_salesman = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_customers",
    )
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["name"]
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def clean(self):
        super().clean()
        validate_state_code(self.state_code)
        if self.gstin:
            validate_gstin(self.gstin, self.state_code)

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code}) - {self.get_customer_type_display()} [State {self.state_code}]"


class Supplier(models.Model):
    """
    Vendor supplying raw materials (flour, oil, spices) or packaging (pouches, cartons).
    """

    code = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=128)
    gstin = models.CharField(max_length=15, blank=True, null=True)
    state_code = models.CharField(max_length=2, default="33")
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["name"]
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"

    def clean(self):
        super().clean()
        validate_state_code(self.state_code)
        if self.gstin:
            validate_gstin(self.gstin, self.state_code)

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"


class PriceList(models.Model):
    """
    Tiered pricing structure by customer segment (e.g. Retailer List vs Distributor List).
    """

    CUSTOMER_TYPE_CHOICES = [
        ("ALL", "All Customers"),
        ("RETAILER", "Retailers"),
        ("DISTRIBUTOR", "Distributors"),
    ]

    name = models.CharField(max_length=64)
    customer_type = models.CharField(max_length=16, choices=CUSTOMER_TYPE_CHOICES, default="ALL")
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["name"]
        verbose_name = "Price List"
        verbose_name_plural = "Price Lists"

    def __str__(self):
        return f"{self.name} ({self.customer_type})"


class PriceListLine(models.Model):
    """Itemized rate for a Product inside a PriceList."""

    price_list = models.ForeignKey(PriceList, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="price_lines")
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)

    history = HistoricalRecords()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["price_list", "product"],
                name="unique_product_per_price_list",
            )
        ]
        verbose_name = "Price List Line"
        verbose_name_plural = "Price List Lines"

    def __str__(self):
        return f"{self.price_list.name}: {self.product} @ ₹{self.unit_price}"


class CustomerPrice(models.Model):
    """Direct negotiated contract price override for a specific Customer and Product."""

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="custom_prices")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="customer_prices")
    custom_price = models.DecimalField(max_digits=14, decimal_places=2)
    is_active = models.BooleanField(default=True)

    history = HistoricalRecords()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "product"],
                name="unique_customer_product_price_override",
            )
        ]
        verbose_name = "Customer Price Override"
        verbose_name_plural = "Customer Price Overrides"

    def __str__(self):
        return f"{self.customer.name} override: {self.product} @ ₹{self.custom_price}"
