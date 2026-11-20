"""
Test suite for Phase 2: Masters, Units, Shared Bills of Materials (BOM), Pricing Resolution, and GSTIN.
"""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction

from apps.core.errors import UnitMismatch
from apps.core.units import convert
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
from apps.masters.services import resolve_product_price
from apps.masters.validators import validate_gstin, validate_state_code


@pytest.mark.django_db
class TestUnitConversions:
    """Verifies unit conversions via database table records and UNIT_DEFINITIONS."""

    def test_unit_conversion_through_table(self):
        """Conversions using Unit table instances factor_to_base."""
        u_g, _ = Unit.objects.get_or_create(
            code="g",
            defaults={
                "name": "Gram",
                "kind": "mass",
                "factor_to_base": Decimal("1.0000"),
                "is_base": True,
            },
        )
        u_kg, _ = Unit.objects.get_or_create(
            code="kg",
            defaults={
                "name": "Kilogram",
                "kind": "mass",
                "factor_to_base": Decimal("1000.0000"),
                "is_base": False,
            },
        )
        u_ml, _ = Unit.objects.get_or_create(
            code="ml",
            defaults={
                "name": "Millilitre",
                "kind": "volume",
                "factor_to_base": Decimal("1.0000"),
                "is_base": True,
            },
        )
        u_l, _ = Unit.objects.get_or_create(
            code="l",
            defaults={
                "name": "Litre",
                "kind": "volume",
                "factor_to_base": Decimal("1000.0000"),
                "is_base": False,
            },
        )
        u_pc, _ = Unit.objects.get_or_create(
            code="pc",
            defaults={
                "name": "Piece",
                "kind": "count",
                "factor_to_base": Decimal("1.0000"),
                "is_base": True,
            },
        )
        u_pkt, _ = Unit.objects.get_or_create(
            code="packet",
            defaults={
                "name": "Packet",
                "kind": "count",
                "factor_to_base": Decimal("1.0000"),
                "is_base": False,
            },
        )

        # 1. Mass: kg -> g
        assert u_kg.convert_to(u_g, Decimal("2.5")) == Decimal("2500.0000")
        assert u_g.convert_to(u_kg, Decimal("40000")) == Decimal("40.0000")

        # 2. Volume: l -> ml
        assert u_l.convert_to(u_ml, Decimal("10.0")) == Decimal("10000.0000")
        assert u_ml.convert_to(u_l, Decimal("750.0")) == Decimal("0.7500")

        # 3. Count: pc <-> packet
        assert u_pkt.convert_to(u_pc, Decimal("200")) == Decimal("200.0000")

        # 4. Incompatible kinds rejection
        with pytest.raises(UnitMismatch, match="Cannot convert between incompatible"):
            u_kg.convert_to(u_l, Decimal("5"))

        with pytest.raises(UnitMismatch, match="Cannot convert between incompatible"):
            u_pc.convert_to(u_g, Decimal("10"))

        # 5. Global convert() accepting Unit model instances or string codes
        assert convert(Decimal("1.5"), u_kg, u_g) == Decimal("1500.0000")
        assert convert(Decimal("500"), u_ml, u_l) == Decimal("0.5000")
        assert convert(Decimal("2.5"), "kg", "g") == Decimal("2500.0000")


@pytest.mark.django_db
class TestBOMAndSharedRecipe:
    """Verifies single shared BOM architecture across pack sizes and scaling."""

    @pytest.fixture(autouse=True)
    def setup_master_data(self):
        call_command("seed_benchmark")

    def test_benchmark_bom_planned_consumption(self):
        """After seed, planned_consumption for Murukku 200g matches benchmark specification."""
        product_200g = Product.objects.get(item__code="FG-MURUKKU-200G")
        bom = product_200g.bom
        assert bom is not None
        assert bom.batch_output_g == Decimal("40000.00")
        assert bom.expected_packets(product_200g) == 200

        # 1 batch scaling: 40kg dough + 200 pouches + 10 cartons
        plan_1 = {
            c["item"].code: c["qty_base"]
            for c in bom.planned_consumption(product_200g, Decimal("1.0000"))
        }
        assert plan_1["RAW-FLOUR"] == Decimal("40000.0000")  # 40 kg
        assert plan_1["RAW-OIL"] == Decimal("10000.0000")  # 10 L
        assert plan_1["RAW-SPICE"] == Decimal("1200.0000")  # 1.2 kg
        assert plan_1["PKG-POUCH-200G"] == Decimal("200.0000")  # 200 pouches
        assert plan_1["PKG-CARTON"] == Decimal("10.0000")  # 10 cartons

        # 2.5 batches scaling
        plan_2_5 = {
            c["item"].code: c["qty_base"]
            for c in bom.planned_consumption(product_200g, Decimal("2.5000"))
        }
        assert plan_2_5["RAW-FLOUR"] == Decimal("100000.0000")  # 100 kg
        assert plan_2_5["RAW-OIL"] == Decimal("25000.0000")  # 25 L
        assert plan_2_5["RAW-SPICE"] == Decimal("3000.0000")  # 3.0 kg
        assert plan_2_5["PKG-POUCH-200G"] == Decimal("500.0000")  # 500 pouches
        assert plan_2_5["PKG-CARTON"] == Decimal("25.0000")  # 25 cartons

    def test_shared_recipe_formulation_500g_product(self):
        """
        Adding a 500g Product to the same BOM takes one Product record plus its pouch and carton lines,
        creating NO raw dough material lines.
        Raw consumption for both products is identical.
        Changing the flour line once in the BOM updates raw consumption for both products.
        """
        u_pc = Unit.objects.get(code="pc")
        carton = Item.objects.get(code="PKG-CARTON")
        product_200g = Product.objects.get(item__code="FG-MURUKKU-200G")
        bom = product_200g.bom

        # Count existing raw material lines before adding 500g pack
        raw_lines_before = BOMLine.objects.filter(bom=bom, item__item_type="RAW").count()
        assert raw_lines_before == 3  # Flour, Oil, Spice

        # Create 500g packaging item
        pouch_500g = Item.objects.create(
            code="PKG-POUCH-500G",
            name="500g Printed Pouch",
            item_type="PACKAGING",
            base_unit=u_pc,
            standard_rate=Decimal("4.50000000"),
        )

        # Create Finished Good Item & Product Profile for 500g Murukku sharing the same BOM
        fg_500g_item = Item.objects.create(
            code="FG-MURUKKU-500G",
            name="Murukku 500g Pack",
            item_type="FINISHED",
            base_unit=u_pc,
            hsn_code="2106",
            gst_rate=Decimal("5.00"),
        )
        product_500g = Product.objects.create(
            item=fg_500g_item,
            bom=bom,  # Same master recipe
            pack_size_g=Decimal("500.00"),
            packets_per_carton=20,
            list_price=Decimal("120.00"),
        )

        # 40,000 g dough / 500 g per packet = 80 packets per batch
        assert bom.expected_packets(product_500g) == 80

        # Add ONLY packaging lines for the 500g product (NO raw lines created!)
        BOMLine.objects.create(
            bom=bom,
            product=product_500g,
            item=pouch_500g,
            qty_base=Decimal("80.0000"),
            display_unit=u_pc,
        )
        BOMLine.objects.create(
            bom=bom,
            product=product_500g,
            item=carton,
            qty_base=Decimal("4.0000"),  # 80 packets / 20 pkts per carton = 4 cartons
            display_unit=u_pc,
        )

        # Ensure NO new raw material lines were created
        raw_lines_after = BOMLine.objects.filter(bom=bom, item__item_type="RAW").count()
        assert raw_lines_after == raw_lines_before

        # Raw consumption for both products is identical
        raw_200 = [x for x in bom.planned_consumption(product_200g) if x["is_shared"]]
        raw_500 = [x for x in bom.planned_consumption(product_500g) if x["is_shared"]]
        assert raw_200 == raw_500

        # Changing the flour line once in the BOM updates raw consumption for BOTH products
        flour_line = BOMLine.objects.get(bom=bom, item__code="RAW-FLOUR")
        flour_line.qty_base = Decimal("42000.0000")  # Change from 40kg to 42kg
        flour_line.save()

        plan_200_updated = {
            c["item"].code: c["qty_base"] for c in bom.planned_consumption(product_200g)
        }
        plan_500_updated = {
            c["item"].code: c["qty_base"] for c in bom.planned_consumption(product_500g)
        }
        assert plan_200_updated["RAW-FLOUR"] == Decimal("42000.0000")
        assert plan_500_updated["RAW-FLOUR"] == Decimal("42000.0000")

    def test_one_active_bom_per_name_constraint(self):
        """Ensures database enforces only one active BOM per recipe name."""
        bom_v1 = BOM.objects.get(name="Murukku Classic", version=1)
        assert bom_v1.is_active is True

        # Creating a second active BOM with the same name must violate unique_active_bom_per_name
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                BOM.objects.create(
                    name="Murukku Classic",
                    version=2,
                    batch_output_g=Decimal("40000.00"),
                    is_active=True,
                )

        # Inactive BOM v2 is permitted
        bom_v2 = BOM.objects.create(
            name="Murukku Classic",
            version=2,
            batch_output_g=Decimal("40000.00"),
            is_active=False,
        )
        assert bom_v2.pk is not None

        # Deactivating v1 allows v2 to become active
        bom_v1.is_active = False
        bom_v1.save()

        bom_v2.is_active = True
        bom_v2.save()
        assert BOM.objects.filter(name="Murukku Classic", is_active=True).count() == 1


@pytest.mark.django_db
class TestValidators:
    """Verifies statutory GSTIN and state code validations."""

    def test_state_code_validator(self):
        validate_state_code("33")  # Tamil Nadu
        validate_state_code("29")  # Karnataka

        with pytest.raises(ValidationError, match="State code must be exactly 2 numeric digits"):
            validate_state_code("3")

        with pytest.raises(ValidationError, match="State code must be exactly 2 numeric digits"):
            validate_state_code("TN")

        with pytest.raises(ValidationError, match="State code must be exactly 2 numeric digits"):
            validate_state_code("")

    def test_gstin_validator(self):
        validate_gstin("33AAAAA1111A1Z1", state_code="33")
        validate_gstin("29BBBBB2222B1Z2", state_code="29")

        with pytest.raises(ValidationError, match="GSTIN must be exactly 15 characters long"):
            validate_gstin("33AAAAA1111A1Z")

        with pytest.raises(ValidationError, match="Invalid GSTIN structure"):
            validate_gstin("33AAAAA1111A1-1")

        with pytest.raises(
            ValidationError, match="GSTIN state prefix '29' does not match entity state code '33'"
        ):
            validate_gstin("29BBBBB2222B1Z2", state_code="33")

    def test_customer_model_clean_validation(self):
        customer = Customer(
            code="CUST-INVALID",
            name="Invalid GSTIN Customer",
            customer_type="RETAILER",
            state_code="33",
            gstin="29AAAAA1111A1Z1",
        )
        with pytest.raises(
            ValidationError, match="GSTIN state prefix '29' does not match entity state code '33'"
        ):
            customer.save()


@pytest.mark.django_db
class TestPriceResolution:
    """Verifies benchmark ₹50.00 pricing for all customers and full resolution hierarchy."""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        call_command("seed_benchmark")

    def test_seed_benchmark_prices_at_fifty_for_all_customers(self):
        """Rule 1: Murukku 200g is priced at 50.00 for EVERY customer after seed_benchmark."""
        product_200g = Product.objects.get(item__code="FG-MURUKKU-200G")
        retailer_a = Customer.objects.get(code="CUST-RETAILER-A")
        distributor_b = Customer.objects.get(code="CUST-DIST-B")

        # Both must resolve to ₹50.00
        assert resolve_product_price(retailer_a, product_200g) == Decimal("50.00")
        assert resolve_product_price(distributor_b, product_200g) == Decimal("50.00")

    def test_price_resolution_hierarchy(self):
        """
        Tests resolution order:
        1. CustomerPrice override -> 2. customer_type PriceList -> 3. default PriceList -> 4. list_price.
        Tier/override rows are set up explicitly in this test fixture.
        """
        product_200g = Product.objects.get(item__code="FG-MURUKKU-200G")
        retailer_a = Customer.objects.get(code="CUST-RETAILER-A")
        distributor_b = Customer.objects.get(code="CUST-DIST-B")

        # Baseline: Both resolve to default list price ₹50.00
        assert resolve_product_price(retailer_a, product_200g) == Decimal("50.00")
        assert resolve_product_price(distributor_b, product_200g) == Decimal("50.00")

        # 1. Add Distributor tier price list (₹45.00)
        dist_list = PriceList.objects.create(
            name="Distributor Tier Price List",
            customer_type="DISTRIBUTOR",
            is_default=False,
            is_active=True,
        )
        PriceListLine.objects.create(
            price_list=dist_list,
            product=product_200g,
            unit_price=Decimal("45.00"),
        )
        # Distributor B now gets ₹45.00; Retailer A still gets default ₹50.00
        assert resolve_product_price(distributor_b, product_200g) == Decimal("45.00")
        assert resolve_product_price(retailer_a, product_200g) == Decimal("50.00")

        # 2. Add direct CustomerPrice override for Retailer A (₹48.00)
        custom_override = CustomerPrice.objects.create(
            customer=retailer_a,
            product=product_200g,
            custom_price=Decimal("48.00"),
            is_active=True,
        )
        # Retailer A now gets ₹48.00 override
        assert resolve_product_price(retailer_a, product_200g) == Decimal("48.00")

        # 3. If override is deactivated, falls back to default list
        custom_override.is_active = False
        custom_override.save()
        assert resolve_product_price(retailer_a, product_200g) == Decimal("50.00")

        # 4. If all price lists are deleted, falls back to product.list_price
        PriceListLine.objects.filter(product=product_200g).delete()
        assert resolve_product_price(retailer_a, product_200g) == Decimal("50.00")
        assert resolve_product_price(None, product_200g) == Decimal("50.00")


@pytest.mark.django_db
class TestSeedBenchmarkIdempotency:
    """Verifies seed_benchmark command can be run repeatedly without errors or duplicating data."""

    def test_seed_benchmark_is_idempotent(self):
        call_command("seed_benchmark")

        units_count = Unit.objects.count()
        items_count = Item.objects.count()
        products_count = Product.objects.count()
        boms_count = BOM.objects.count()
        bom_lines_count = BOMLine.objects.count()
        customers_count = Customer.objects.count()
        suppliers_count = Supplier.objects.count()
        pricelists_count = PriceList.objects.count()

        call_command("seed_benchmark")

        assert Unit.objects.count() == units_count
        assert Item.objects.count() == items_count
        assert Product.objects.count() == products_count
        assert BOM.objects.count() == boms_count
        assert BOMLine.objects.count() == bom_lines_count
        assert Customer.objects.count() == customers_count
        assert Supplier.objects.count() == suppliers_count
        assert PriceList.objects.count() == pricelists_count
