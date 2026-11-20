"""
Test suite for Phase 2: Masters, Units, Bills of Materials (BOM), Pricing Resolution, and GSTIN.
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

        # 5. Global convert() accepting Unit model instances
        assert convert(Decimal("1.5"), u_kg, u_g) == Decimal("1500.0000")
        assert convert(Decimal("500"), u_ml, u_l) == Decimal("0.5000")


@pytest.mark.django_db
class TestBOMAndRecipe:
    """Verifies BOM consumption scaling, active-BOM partial constraints, and shared recipes."""

    @pytest.fixture(autouse=True)
    def setup_master_data(self):
        call_command("seed_benchmark")

    def test_bom_consumption_scaling(self):
        """Verifies BOM planned component scaling across production batches."""
        product = Product.objects.get(item__code="FG-MURUKKU-200G")
        bom = BOM.objects.get(product=product, is_active=True)

        # 1 batch scaling
        plan_1 = {c["item"].code: c["qty_base"] for c in bom.scale_consumption(Decimal("1.0000"))}
        assert plan_1["RAW-FLOUR"] == Decimal("40000.0000")  # 40 kg
        assert plan_1["RAW-OIL"] == Decimal("10000.0000")  # 10 L
        assert plan_1["RAW-SPICE"] == Decimal("1200.0000")  # 1.2 kg
        assert plan_1["PKG-POUCH-200G"] == Decimal("200.0000")  # 200 pouches
        assert plan_1["PKG-CARTON"] == Decimal("10.0000")  # 10 cartons

        # 2.5 batches scaling
        plan_2_5 = {c["item"].code: c["qty_base"] for c in bom.scale_consumption(Decimal("2.5000"))}
        assert plan_2_5["RAW-FLOUR"] == Decimal("100000.0000")  # 100 kg
        assert plan_2_5["RAW-OIL"] == Decimal("25000.0000")  # 25 L
        assert plan_2_5["RAW-SPICE"] == Decimal("3000.0000")  # 3.0 kg
        assert plan_2_5["PKG-POUCH-200G"] == Decimal("500.0000")  # 500 pouches
        assert plan_2_5["PKG-CARTON"] == Decimal("25.0000")  # 25 cartons

    def test_active_bom_partial_unique_constraint(self):
        """Ensures database enforces only one active BOM per product."""
        product = Product.objects.get(item__code="FG-MURUKKU-200G")

        # BOM v1 is already active from seed_benchmark.
        # Creating a second active BOM v2 must violate unique_active_bom_per_product.
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                BOM.objects.create(
                    product=product,
                    version=2,
                    batch_output_packets=200,
                    recipe_group="MURUKKU_CLASSIC",
                    yield_basis=Decimal("40.00"),
                    is_active=True,
                )

        # Creating an inactive BOM v2 is permitted
        bom_v2 = BOM.objects.create(
            product=product,
            version=2,
            batch_output_packets=200,
            recipe_group="MURUKKU_CLASSIC",
            yield_basis=Decimal("40.00"),
            is_active=False,
        )
        assert bom_v2.pk is not None

        # Deactivating v1 allows v2 to become active
        bom_v1 = BOM.objects.get(product=product, version=1)
        bom_v1.is_active = False
        bom_v1.save()

        bom_v2.is_active = True
        bom_v2.save()
        assert BOM.objects.filter(product=product, is_active=True).count() == 1

    def test_shared_recipe_formulation_500g_product(self):
        """
        Demonstrates adding a 500g Murukku product sharing the classic recipe formulation.
        Core dough batch yields 40.00 kg.
        - 200g Murukku yields 200 pkts / batch (40,000 / 200).
        - 500g Murukku yields 80 pkts / batch (40,000 / 500).
        Raw materials are identical per batch; packaging items scale to the 80 pkt yield.
        """
        u_g = Unit.objects.get(code="g")
        u_kg = Unit.objects.get(code="kg")
        u_l = Unit.objects.get(code="l")
        u_pc = Unit.objects.get(code="pc")

        flour = Item.objects.get(code="RAW-FLOUR")
        oil = Item.objects.get(code="RAW-OIL")
        spice = Item.objects.get(code="RAW-SPICE")
        carton = Item.objects.get(code="PKG-CARTON")

        # Create packaging item for 500g pouch
        pouch_500g = Item.objects.create(
            code="PKG-POUCH-500G",
            name="500g Printed Pouch",
            item_type="PACKAGING",
            base_unit=u_pc,
            valuation_rate=Decimal("4.5000"),
        )

        # Create Finished Good Item & Product Profile for 500g Murukku
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
            pack_size_g=Decimal("500.00"),
            packets_per_carton=20,
            list_price=Decimal("120.00"),
        )

        # 40kg dough yield / 0.5kg per packet = 80 packets per batch
        batch_packets_500g = int(Decimal("40000.00") / product_500g.pack_size_g)
        assert batch_packets_500g == 80

        # Create BOM sharing the 'MURUKKU_CLASSIC' recipe group
        bom_500g = BOM.objects.create(
            product=product_500g,
            version=1,
            batch_output_packets=batch_packets_500g,
            recipe_group="MURUKKU_CLASSIC",
            yield_basis=Decimal("40.00"),
            is_active=True,
        )

        # Dough raw materials match standard 40kg formulation
        BOMLine.objects.create(
            bom=bom_500g, item=flour, qty_base=Decimal("40000.0000"), display_unit=u_kg
        )
        BOMLine.objects.create(
            bom=bom_500g, item=oil, qty_base=Decimal("10000.0000"), display_unit=u_l
        )
        BOMLine.objects.create(
            bom=bom_500g, item=spice, qty_base=Decimal("1200.0000"), display_unit=u_g
        )

        # Packaging lines match 80 packet yield
        cartons_required = Decimal(
            str(batch_packets_500g / product_500g.packets_per_carton)
        )  # 80 / 20 = 4
        BOMLine.objects.create(
            bom=bom_500g, item=pouch_500g, qty_base=Decimal("80.0000"), display_unit=u_pc
        )
        BOMLine.objects.create(
            bom=bom_500g, item=carton, qty_base=cartons_required, display_unit=u_pc
        )

        # Scale consumption for 2 batches of 500g Murukku
        plan = {
            c["item"].code: c["qty_base"] for c in bom_500g.scale_consumption(Decimal("2.0000"))
        }
        assert plan["RAW-FLOUR"] == Decimal("80000.0000")  # 80 kg
        assert plan["RAW-OIL"] == Decimal("20000.0000")  # 20 L
        assert plan["RAW-SPICE"] == Decimal("2400.0000")  # 2.4 kg
        assert plan["PKG-POUCH-500G"] == Decimal("160.0000")  # 160 pouches
        assert plan["PKG-CARTON"] == Decimal("8.0000")  # 8 outer cartons


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
        # Valid 15-char statutory format
        validate_gstin("33AAAAA1111A1Z1", state_code="33")
        validate_gstin("29BBBBB2222B1Z2", state_code="29")

        # Invalid length
        with pytest.raises(ValidationError, match="GSTIN must be exactly 15 characters long"):
            validate_gstin("33AAAAA1111A1Z")

        # Invalid pattern
        with pytest.raises(ValidationError, match="Invalid GSTIN structure"):
            validate_gstin("33AAAAA1111A1-1")

        # State code prefix mismatch (e.g. Karnataka prefix 29 on Tamil Nadu entity 33)
        with pytest.raises(
            ValidationError, match="GSTIN state prefix '29' does not match entity state code '33'"
        ):
            validate_gstin("29BBBBB2222B1Z2", state_code="33")

    def test_customer_model_clean_validation(self):
        """Ensures Customer model validates state code and GSTIN on save."""
        customer = Customer(
            code="CUST-INVALID",
            name="Invalid GSTIN Customer",
            customer_type="RETAILER",
            state_code="33",
            gstin="29AAAAA1111A1Z1",  # Starts with 29, but state_code is 33
        )
        with pytest.raises(
            ValidationError, match="GSTIN state prefix '29' does not match entity state code '33'"
        ):
            customer.save()


@pytest.mark.django_db
class TestPriceResolution:
    """Verifies price resolution hierarchy: CustomerPrice -> Type PriceList -> Default PriceList -> list_price."""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        call_command("seed_benchmark")

    def test_price_resolution_hierarchy(self):
        product_200g = Product.objects.get(item__code="FG-MURUKKU-200G")
        retailer_a = Customer.objects.get(code="CUST-RETAILER-A")
        distributor_b = Customer.objects.get(code="CUST-DIST-B")

        # 1. Retailer A has direct CustomerPrice override (₹48.00)
        price_a = resolve_product_price(retailer_a, product_200g)
        assert price_a == Decimal("48.00")

        # 2. Distributor B has no direct override, matches DISTRIBUTOR PriceList (₹45.00)
        price_b = resolve_product_price(distributor_b, product_200g)
        assert price_b == Decimal("45.00")

        # 3. New Retailer C has no custom price and no RETAILER-specific list; falls back to default list (₹50.00)
        retailer_c = Customer.objects.create(
            code="CUST-RETAILER-C",
            name="Retailer C",
            customer_type="RETAILER",
            state_code="33",
        )
        price_c = resolve_product_price(retailer_c, product_200g)
        assert price_c == Decimal("50.00")

        # 4. If removed from all price lists, falls back to product.list_price
        PriceListLine.objects.filter(product=product_200g).delete()
        CustomerPrice.objects.filter(product=product_200g).delete()

        price_fallback = resolve_product_price(retailer_c, product_200g)
        assert price_fallback == Decimal("50.00")

        # 5. Anonymous / None customer falls back to product.list_price
        price_anon = resolve_product_price(None, product_200g)
        assert price_anon == Decimal("50.00")


@pytest.mark.django_db
class TestSeedBenchmarkIdempotency:
    """Verifies seed_benchmark command can be run repeatedly without errors or duplicating data."""

    def test_seed_benchmark_is_idempotent(self):
        # First execution
        call_command("seed_benchmark")

        units_count = Unit.objects.count()
        items_count = Item.objects.count()
        products_count = Product.objects.count()
        boms_count = BOM.objects.count()
        bom_lines_count = BOMLine.objects.count()
        customers_count = Customer.objects.count()
        suppliers_count = Supplier.objects.count()
        pricelists_count = PriceList.objects.count()

        # Second execution
        call_command("seed_benchmark")

        # Counts must match exactly
        assert Unit.objects.count() == units_count
        assert Item.objects.count() == items_count
        assert Product.objects.count() == products_count
        assert BOM.objects.count() == boms_count
        assert BOMLine.objects.count() == bom_lines_count
        assert Customer.objects.count() == customers_count
        assert Supplier.objects.count() == suppliers_count
        assert PriceList.objects.count() == pricelists_count
