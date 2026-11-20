"""
Management command to seed idempotent benchmark master data for Murukku food factory.
Seeds the 5 core Items with standard_rate (8 dp), Murukku 200g Product, 40kg shared BOM,
Customers (Retailer A, Distributor B), Suppliers, and default Price List (₹50.00 for all).
Also invokes create_demo_users.
Units are seeded by data migration 0002_seed_units (single source of truth).
DOES NOT seed opening inventory balances (opening stock belongs to Phase 3 ledger).
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

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

User = get_user_model()


class Command(BaseCommand):
    help = "Idempotently seeds benchmark master data (items, shared BOM, customers, suppliers, price lists)."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("==> Seeding Demo Users first..."))
        call_command("create_demo_users")

        salesman_a = User.objects.filter(username="salesman_a").first()
        salesman_b = User.objects.filter(username="salesman_b").first()

        self.stdout.write(
            self.style.NOTICE("==> Retrieving Units of Measure (seeded via migration)...")
        )
        u_g = Unit.objects.get(code="g")
        u_kg = Unit.objects.get(code="kg")
        u_ml = Unit.objects.get(code="ml")
        u_l = Unit.objects.get(code="l")
        u_pc = Unit.objects.get(code="pc")

        self.stdout.write(
            self.style.NOTICE("==> Seeding 5 Core Items & Standard Rates (8 decimal places)...")
        )
        # 1. Flour Blend (Raw Material: ₹42.00 / kg -> 0.04200000 / g)
        flour, _ = Item.objects.update_or_create(
            code="RAW-FLOUR",
            defaults={
                "name": "Rice & Besan Flour Blend",
                "item_type": "RAW",
                "base_unit": u_g,
                "hsn_code": "2106",
                "gst_rate": Decimal("5.00"),
                "tolerance_pct": Decimal("3.00"),
                "reorder_level": Decimal("50000.0000"),  # 50 kg
                "standard_rate": Decimal("0.04200000"),  # ₹0.04200000 / g
                "is_active": True,
            },
        )

        # 2. Refined Cooking Oil (Raw Material: ₹140.00 / L -> 0.14000000 / ml)
        oil, _ = Item.objects.update_or_create(
            code="RAW-OIL",
            defaults={
                "name": "Refined Cooking Oil",
                "item_type": "RAW",
                "base_unit": u_ml,
                "hsn_code": "1507",
                "gst_rate": Decimal("5.00"),
                "tolerance_pct": Decimal("3.00"),
                "reorder_level": Decimal("20000.0000"),  # 20 L
                "standard_rate": Decimal("0.14000000"),  # ₹0.14000000 / ml
                "is_active": True,
            },
        )

        # 3. Spice Mix (Raw Material: ₹200.00 / kg -> 0.20000000 / g)
        spice, _ = Item.objects.update_or_create(
            code="RAW-SPICE",
            defaults={
                "name": "Murukku Spice Mix",
                "item_type": "RAW",
                "base_unit": u_g,
                "hsn_code": "0910",
                "gst_rate": Decimal("5.00"),
                "tolerance_pct": Decimal("3.00"),
                "reorder_level": Decimal("5000.0000"),  # 5 kg
                "standard_rate": Decimal("0.20000000"),  # ₹0.20000000 / g
                "is_active": True,
            },
        )

        # 4. 200g Printed Pouch (Packaging Material: ₹2.50000000 / pc)
        pouch, _ = Item.objects.update_or_create(
            code="PKG-POUCH-200G",
            defaults={
                "name": "200g Printed Pouch",
                "item_type": "PACKAGING",
                "base_unit": u_pc,
                "hsn_code": "3923",
                "gst_rate": Decimal("18.00"),
                "tolerance_pct": Decimal("3.00"),
                "reorder_level": Decimal("1000.0000"),  # 1,000 pouches
                "standard_rate": Decimal("2.50000000"),  # ₹2.50000000 / pc
                "is_active": True,
            },
        )

        # 5. Shipper Carton (Packaging Material: ₹15.00000000 / pc)
        carton, _ = Item.objects.update_or_create(
            code="PKG-CARTON",
            defaults={
                "name": "Shipper Carton (20 pkts)",
                "item_type": "PACKAGING",
                "base_unit": u_pc,
                "hsn_code": "4819",
                "gst_rate": Decimal("18.00"),
                "tolerance_pct": Decimal("3.00"),
                "reorder_level": Decimal("100.0000"),  # 100 cartons
                "standard_rate": Decimal("15.00000000"),  # ₹15.00000000 / pc
                "is_active": True,
            },
        )

        self.stdout.write(
            self.style.NOTICE("==> Seeding Master BOM ('Murukku Classic', 40kg dough yield)...")
        )
        bom, _ = BOM.objects.update_or_create(
            name="Murukku Classic",
            version=1,
            defaults={
                "batch_output_g": Decimal("40000.00"),
                "is_active": True,
            },
        )

        # Shared dough raw material lines (product is None: identical for all products using this BOM)
        shared_components = [
            (flour, Decimal("40000.0000"), u_kg),  # 40,000 g (40 kg)
            (oil, Decimal("10000.0000"), u_l),  # 10,000 ml (10 L)
            (spice, Decimal("1200.0000"), u_g),  # 1,200 g (1.2 kg)
        ]
        for item, qty_base, display_unit in shared_components:
            BOMLine.objects.update_or_create(
                bom=bom,
                product=None,
                item=item,
                defaults={
                    "qty_base": qty_base,
                    "display_unit": display_unit,
                },
            )

        self.stdout.write(self.style.NOTICE("==> Seeding Finished Product (Murukku 200g)..."))
        fg_item, _ = Item.objects.update_or_create(
            code="FG-MURUKKU-200G",
            defaults={
                "name": "Murukku 200g Pack",
                "item_type": "FINISHED",
                "base_unit": u_pc,
                "hsn_code": "2106",
                "gst_rate": Decimal("5.00"),
                "tolerance_pct": Decimal("3.00"),
                "standard_rate": Decimal("0.00000000"),
                "is_active": True,
            },
        )

        product_200g, _ = Product.objects.update_or_create(
            item=fg_item,
            defaults={
                "bom": bom,
                "pack_size_g": Decimal("200.00"),
                "packets_per_carton": 20,
                "list_price": Decimal("50.00"),  # Benchmark list price: ₹50.00 before tax
            },
        )

        # Product-specific packaging lines for 200g product (200 pkts / batch)
        product_packaging_components = [
            (pouch, Decimal("200.0000"), u_pc),  # 200 pouches for 200 pkts
            (carton, Decimal("10.0000"), u_pc),  # 10 cartons (20 pkts/carton)
        ]
        for item, qty_base, display_unit in product_packaging_components:
            BOMLine.objects.update_or_create(
                bom=bom,
                product=product_200g,
                item=item,
                defaults={
                    "qty_base": qty_base,
                    "display_unit": display_unit,
                },
            )

        self.stdout.write(
            self.style.NOTICE("==> Seeding Customers (Retailer A & Distributor B)...")
        )
        # Retailer A (Intrastate - Tamil Nadu, state 33)
        retailer_a, _ = Customer.objects.update_or_create(
            code="CUST-RETAILER-A",
            defaults={
                "name": "Retailer A (Chennai Supermart)",
                "customer_type": "RETAILER",
                "state_code": "33",
                "gstin": "33AAAAA1111A1Z1",
                "assigned_salesman": salesman_a,
                "phone": "9876543210",
                "address": "12 Gandhi Road, Anna Nagar, Chennai, Tamil Nadu 600040",
                "is_active": True,
            },
        )

        # Distributor B (Interstate - Karnataka, state 29)
        distributor_b, _ = Customer.objects.update_or_create(
            code="CUST-DIST-B",
            defaults={
                "name": "Distributor B (Bengaluru Wholesale)",
                "customer_type": "DISTRIBUTOR",
                "state_code": "29",
                "gstin": "29BBBBB2222B1Z2",
                "assigned_salesman": salesman_b,
                "phone": "9876543211",
                "address": "45 Industrial Suburb, Yeshwanthpur, Bengaluru, Karnataka 560022",
                "is_active": True,
            },
        )

        self.stdout.write(self.style.NOTICE("==> Seeding Suppliers..."))
        Supplier.objects.update_or_create(
            code="SUPP-FLOUR-MILL",
            defaults={
                "name": "Tamil Nadu Agro Flour Mills",
                "state_code": "33",
                "gstin": "33SUPPL1111A1Z1",
                "phone": "9841001122",
                "address": "Madurai Main Road, Dindigul, Tamil Nadu",
                "is_active": True,
            },
        )
        Supplier.objects.update_or_create(
            code="SUPP-OIL-REFINERY",
            defaults={
                "name": "Kaveri Edible Oils Refinery",
                "state_code": "33",
                "gstin": "33SUPPL2222B1Z2",
                "phone": "9841003344",
                "address": "SIDCO Industrial Estate, Trichy, Tamil Nadu",
                "is_active": True,
            },
        )
        Supplier.objects.update_or_create(
            code="SUPP-PACK-PVT",
            defaults={
                "name": "Apex Flexible Packaging Ltd",
                "state_code": "33",
                "gstin": "33SUPPL3333C1Z3",
                "phone": "9841005566",
                "address": "Ambattur Industrial Estate, Chennai, Tamil Nadu",
                "is_active": True,
            },
        )

        self.stdout.write(
            self.style.NOTICE("==> Seeding Standard Price List (₹50.00 for EVERY customer)...")
        )
        # Standard Price List (Applicable to ALL customers, default)
        std_list, _ = PriceList.objects.update_or_create(
            name="Standard Wholesale Price List",
            defaults={
                "customer_type": "ALL",
                "is_default": True,
                "is_active": True,
            },
        )
        PriceListLine.objects.update_or_create(
            price_list=std_list,
            product=product_200g,
            defaults={"unit_price": Decimal("50.00")},
        )

        # Benchmark pricing rule: Murukku 200g is ₹50.00 for EVERY customer.
        # Clean up any custom overrides or distributor price lists if present from previous runs
        CustomerPrice.objects.filter(product=product_200g).delete()
        PriceList.objects.filter(name="Distributor Tier Price List").delete()

        self.stdout.write(
            self.style.SUCCESS("[seed_benchmark] Successfully seeded all benchmark master data.")
        )
