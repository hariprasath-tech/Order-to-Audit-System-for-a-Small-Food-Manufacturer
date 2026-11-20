"""
Comprehensive Test Suite for Sales Orders and Salesman Workspace (/salesman/).
Verifies:
1. Workspace RBAC access control (salesman, admin_desk allowed; others 403; anon 302).
2. Live customer selection & catalog rendering.
3. Accurate Indian GST tax calculations:
   - Intrastate (Tamil Nadu -> Tamil Nadu): 2.5% CGST + 2.5% SGST.
   - Interstate (Tamil Nadu -> Karnataka): 5.0% IGST.
4. Benchmark Scenario 4: Salesman A orders 150 pkts for Retailer A (₹7,875.00 total).
5. Benchmark Scenario 6: Salesman B orders 120 pkts for Distributor B (₹6,300.00 total).
6. Order lifecycle: Draft creation and subsequent submission for Admin Desk verification.
7. Salesman order isolation (salesman only sees own orders; admin sees all).
8. Input validations (zero quantity, inactive customer, missing lines).
9. Pricing API endpoint (/salesman/api/pricing/).
10. Simple history audit trail tracking on Order mutations.
Strictly zero floating-point math.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase

from apps.masters.models import Customer, Item, Product, Unit
from apps.sales.models import Order
from apps.sales.services import create_sales_order, submit_sales_order

User = get_user_model()


@pytest.mark.django_db
class TestSalesmanWorkspaceAndOrders(TestCase):
    """Integration and Unit tests for Sales Orders and Salesman Workspace."""

    def setUp(self):
        self.client = Client()

        # Roles
        self.sales_group = Group.objects.get_or_create(name="salesman")[0]
        self.admin_group = Group.objects.get_or_create(name="admin_desk")[0]
        self.prod_group = Group.objects.get_or_create(name="production")[0]

        # Users
        self.salesman_a = User.objects.create_user(username="salesman_a", password="Password123")
        self.salesman_a.groups.add(self.sales_group)

        self.salesman_b = User.objects.create_user(username="salesman_b", password="Password123")
        self.salesman_b.groups.add(self.sales_group)

        self.admin_user = User.objects.create_user(username="admin_user", password="Password123")
        self.admin_user.groups.add(self.admin_group)

        self.prod_user = User.objects.create_user(username="prod_user", password="Password123")
        self.prod_user.groups.add(self.prod_group)

        # Base Units
        self.u_pc = Unit.objects.get_or_create(
            code="pc", defaults={"name": "Piece", "kind": "count", "is_base": True}
        )[0]

        # Finished Good Item (Murukku 200g, 5% GST)
        self.fg_item = Item.objects.create(
            code="FG-MURUKKU-200G",
            name="Murukku 200g",
            item_type="FINISHED",
            base_unit=self.u_pc,
            hsn_code="2106",
            gst_rate=Decimal("5.00"),
            standard_rate=Decimal("0.00000000"),
            is_active=True,
        )

        # Product Profile (List price ₹50.00 before tax)
        self.product_200g = Product.objects.create(
            item=self.fg_item,
            pack_size_g=Decimal("200.00"),
            packets_per_carton=20,
            list_price=Decimal("50.00"),
        )

        # Customers
        # Retailer A (Intrastate - Tamil Nadu, state 33)
        self.retailer_a = Customer.objects.create(
            code="CUST-RETAILER-A",
            name="Retailer A (Chennai Supermart)",
            customer_type="RETAILER",
            state_code="33",
            gstin="33AAAAA1111A1Z1",
            assigned_salesman=self.salesman_a,
            phone="9876543210",
            address="Chennai, Tamil Nadu",
            is_active=True,
        )

        # Distributor B (Interstate - Karnataka, state 29)
        self.distributor_b = Customer.objects.create(
            code="CUST-DIST-B",
            name="Distributor B (Bengaluru Wholesale)",
            customer_type="DISTRIBUTOR",
            state_code="29",
            gstin="29BBBBB2222B1Z2",
            assigned_salesman=self.salesman_b,
            phone="9876543211",
            address="Bengaluru, Karnataka",
            is_active=True,
        )

    def test_salesman_workspace_rbac_permissions(self):
        """
        Salesman and Admin Desk get 200 OK on /salesman/.
        Production supervisor gets 403 Forbidden.
        Anonymous visitor is redirected to login.
        """
        # Anonymous
        anon_resp = self.client.get("/salesman/")
        assert anon_resp.status_code == 302
        assert "/accounts/login/" in anon_resp.url

        # Salesman A -> 200 OK
        self.client.login(username="salesman_a", password="Password123")
        sales_resp = self.client.get("/salesman/")
        assert sales_resp.status_code == 200
        content = sales_resp.content.decode()
        assert "Salesman Order Entry" in content
        assert "New Sales Order" in content
        assert "Retailer A (Chennai Supermart)" in content
        assert "Murukku 200g" in content
        assert "data-logout" in content

        # Admin User -> 200 OK
        self.client.login(username="admin_user", password="Password123")
        admin_resp = self.client.get("/salesman/")
        assert admin_resp.status_code == 200

        # Production User -> 403 Forbidden
        self.client.login(username="prod_user", password="Password123")
        prod_resp = self.client.get("/salesman/")
        assert prod_resp.status_code == 403

    def test_benchmark_order_retailer_a_intrastate_calculation(self):
        """
        Benchmark Step 4: Salesman A orders 150 packets for Retailer A (TN).
        Expected totals:
          - Taxable: 150 * ₹50.00 = ₹7,500.00
          - CGST (2.5%): ₹187.50
          - SGST (2.5%): ₹187.50
          - IGST: ₹0.00
          - Total Tax: ₹375.00
          - Grand Total: ₹7,875.00
        """
        self.client.login(username="salesman_a", password="Password123")

        payload = {
            "customer": str(self.retailer_a.id),
            "order_date": "2026-04-10",
            "notes": "Urgent store restock",
            "action": "submit",
            "product_id": [str(self.product_200g.id)],
            "quantity": ["150"],
            "unit_price": ["50.00"],
        }

        response = self.client.post("/salesman/", data=payload)
        assert response.status_code == 302
        assert response.url == "/salesman/"

        order = Order.objects.get(customer=self.retailer_a)
        assert order.salesman == self.salesman_a
        assert order.status == Order.Status.SUBMITTED
        assert order.subtotal == Decimal("7500.00")
        assert order.cgst_amount == Decimal("187.50")
        assert order.sgst_amount == Decimal("187.50")
        assert order.igst_amount == Decimal("0.00")
        assert order.total_tax == Decimal("375.00")
        assert order.total_amount == Decimal("7875.00")
        assert order.order_number.startswith("SO-2026-27-")

        # Line item assertions
        line = order.lines.first()
        assert line is not None
        assert line.product == self.product_200g
        assert line.quantity == Decimal("150.0000")
        assert line.unit_price == Decimal("50.00")
        assert line.taxable_amount == Decimal("7500.00")
        assert line.cgst_amount == Decimal("187.50")
        assert line.sgst_amount == Decimal("187.50")
        assert line.igst_amount == Decimal("0.00")
        assert line.line_total == Decimal("7875.00")

    def test_benchmark_order_distributor_b_interstate_calculation(self):
        """
        Benchmark Step 6: Salesman B orders 120 packets for Distributor B (KA, state 29).
        Expected totals:
          - Taxable: 120 * ₹50.00 = ₹6,000.00
          - CGST: ₹0.00
          - SGST: ₹0.00
          - IGST (5.0%): ₹300.00
          - Total Tax: ₹300.00
          - Grand Total: ₹6,300.00
        """
        self.client.login(username="salesman_b", password="Password123")

        payload = {
            "customer": str(self.distributor_b.id),
            "order_date": "2026-04-12",
            "notes": "Interstate shipment to Bengaluru hub",
            "action": "submit",
            "product_id": [str(self.product_200g.id)],
            "quantity": ["120"],
            "unit_price": ["50.00"],
        }

        response = self.client.post("/salesman/", data=payload)
        assert response.status_code == 302

        order = Order.objects.get(customer=self.distributor_b)
        assert order.salesman == self.salesman_b
        assert order.status == Order.Status.SUBMITTED
        assert order.subtotal == Decimal("6000.00")
        assert order.cgst_amount == Decimal("0.00")
        assert order.sgst_amount == Decimal("0.00")
        assert order.igst_amount == Decimal("300.00")
        assert order.total_tax == Decimal("300.00")
        assert order.total_amount == Decimal("6300.00")

    def test_save_order_as_draft_and_subsequent_submit(self):
        """
        Salesman saves an order as DRAFT, verifies it in the order table,
        and subsequently submits it for Admin Desk verification via action button.
        """
        self.client.login(username="salesman_a", password="Password123")

        # 1. Save as Draft
        draft_payload = {
            "customer": str(self.retailer_a.id),
            "order_date": "2026-04-15",
            "action": "draft",
            "product_id": [str(self.product_200g.id)],
            "quantity": ["50"],
            "unit_price": ["50.00"],
        }
        resp = self.client.post("/salesman/", data=draft_payload)
        assert resp.status_code == 302

        order = Order.objects.get(customer=self.retailer_a, status=Order.Status.DRAFT)
        assert order.total_amount == Decimal("2625.00")

        # Check rendered in workspace as Draft with Submit button
        get_resp = self.client.get("/salesman/")
        assert get_resp.status_code == 200
        content = get_resp.content.decode()
        assert order.order_number in content
        assert "Draft" in content
        assert f"/salesman/orders/{order.id}/submit/" in content

        # 2. Submit the Draft via POST
        submit_resp = self.client.post(f"/salesman/orders/{order.id}/submit/")
        assert submit_resp.status_code == 302

        order.refresh_from_db()
        assert order.status == Order.Status.SUBMITTED

    def test_salesman_order_isolation(self):
        """
        Salesman A only sees their own orders in recent orders list.
        Salesman B only sees Salesman B's orders.
        Admin Desk sees all orders.
        """
        order_a = create_sales_order(
            salesman=self.salesman_a,
            customer=self.retailer_a,
            lines_data=[{"product": self.product_200g, "quantity": Decimal("10.0000")}],
            status=Order.Status.SUBMITTED,
        )

        order_b = create_sales_order(
            salesman=self.salesman_b,
            customer=self.distributor_b,
            lines_data=[{"product": self.product_200g, "quantity": Decimal("20.0000")}],
            status=Order.Status.SUBMITTED,
        )

        # Salesman A
        self.client.login(username="salesman_a", password="Password123")
        resp_a = self.client.get("/salesman/")
        content_a = resp_a.content.decode()
        assert order_a.order_number in content_a
        assert order_b.order_number not in content_a

        # Salesman B
        self.client.login(username="salesman_b", password="Password123")
        resp_b = self.client.get("/salesman/")
        content_b = resp_b.content.decode()
        assert order_b.order_number in content_b
        assert order_a.order_number not in content_b

        # Admin Desk
        self.client.login(username="admin_user", password="Password123")
        resp_admin = self.client.get("/salesman/")
        content_admin = resp_admin.content.decode()
        assert order_a.order_number in content_admin
        assert order_b.order_number in content_admin

    def test_invalid_order_inputs_display_errors(self):
        """Invalid customer or missing products must display proper validation errors."""
        self.client.login(username="salesman_a", password="Password123")

        # Missing products
        resp1 = self.client.post(
            "/salesman/",
            data={
                "customer": str(self.retailer_a.id),
                "action": "submit",
                "product_id": [],
            },
            follow=True,
        )
        assert resp1.status_code == 200
        assert "Please add at least one product" in resp1.content.decode()

        # Zero quantity
        resp2 = self.client.post(
            "/salesman/",
            data={
                "customer": str(self.retailer_a.id),
                "action": "submit",
                "product_id": [str(self.product_200g.id)],
                "quantity": ["0"],
            },
            follow=True,
        )
        assert resp2.status_code == 200
        assert "must be greater than zero" in resp2.content.decode()

    def test_customer_pricing_api_endpoint(self):
        """GET /salesman/api/pricing/ returns JSON with resolved prices and customer metadata."""
        self.client.login(username="salesman_a", password="Password123")

        resp = self.client.get(f"/salesman/api/pricing/?customer_id={self.retailer_a.id}")
        assert resp.status_code == 200
        data = resp.json()

        assert data["customer"]["code"] == "CUST-RETAILER-A"
        assert data["customer"]["state_code"] == "33"
        assert data["customer"]["is_intrastate"] is True
        assert str(self.product_200g.id) in data["prices"]
        assert data["prices"][str(self.product_200g.id)]["unit_price"] == "50.00"

    def test_simple_history_audit_trail_recorded(self):
        """Every change on Order creates a historical audit record."""
        order = create_sales_order(
            salesman=self.salesman_a,
            customer=self.retailer_a,
            lines_data=[{"product": self.product_200g, "quantity": Decimal("10.0000")}],
            status=Order.Status.DRAFT,
        )
        assert order.history.count() >= 1

        submit_sales_order(order, self.salesman_a)
        assert order.history.count() >= 2
