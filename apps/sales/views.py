"""
Views and API Endpoints for Sales Order Entry Workspace.
Mobile-first order entry, pricing resolution, draft saving, and admin verification submission.
Strictly zero floating-point math.
"""

import json
import logging
from datetime import date
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.decorators import role_required
from apps.core.money import money, qty
from apps.masters.models import Customer, Product
from apps.masters.services import resolve_product_price
from apps.sales.models import Order
from apps.sales.services import create_sales_order, submit_sales_order

logger = logging.getLogger(__name__)


@role_required("salesman", "admin_desk")
def salesman_workspace_view(request):
    """
    Main Salesman Workspace (/salesman/).
    Renders mobile-friendly order entry form, live customer pricing,
    and salesman's saved order history with status tracking.
    Handles POST submissions for both 'Save Draft' and 'Submit Order'.
    """
    user = request.user
    seller_state = getattr(settings, "SELLER_STATE_CODE", "33")

    # Scope orders: Salesmen see their own orders; Admin Desk sees all orders
    is_admin = user.groups.filter(name="admin_desk").exists() or user.is_superuser
    if is_admin:
        orders_qs = (
            Order.objects.all()
            .select_related("customer", "salesman")
            .prefetch_related("lines__product__item")
        )
    else:
        orders_qs = (
            Order.objects.filter(salesman=user)
            .select_related("customer", "salesman")
            .prefetch_related("lines__product__item")
        )

    # Handle New Order Submission
    if request.method == "POST":
        action = request.POST.get("action", "draft")
        target_status = Order.Status.SUBMITTED if action == "submit" else Order.Status.DRAFT

        customer_id = request.POST.get("customer")
        order_date_raw = request.POST.get("order_date")
        notes = request.POST.get("notes", "")

        order_date_val = None
        if order_date_raw and order_date_raw.strip():
            try:
                order_date_val = date.fromisoformat(order_date_raw.strip())
            except ValueError:
                order_date_val = None

        # Extract multi-line payload
        product_ids = request.POST.getlist("product_id")
        quantities = request.POST.getlist("quantity")
        unit_prices = request.POST.getlist("unit_price")

        try:
            if not customer_id:
                raise ValidationError("Please select a customer for this order.")

            customer = Customer.objects.get(pk=customer_id, is_active=True)

            lines_data = []
            for idx, p_id in enumerate(product_ids):
                if not p_id:
                    continue
                product = Product.objects.select_related("item").get(pk=p_id)
                q_str = quantities[idx] if idx < len(quantities) else "1"
                try:
                    q = qty(Decimal(q_str.strip()))
                except (InvalidOperation, ValueError, AttributeError) as exc:
                    raise ValidationError(
                        f"Invalid quantity '{q_str}' for product {product.item.name}."
                    ) from exc

                p_str = unit_prices[idx] if idx < len(unit_prices) else ""
                if p_str and p_str.strip():
                    try:
                        p = money(Decimal(p_str.strip()))
                    except (InvalidOperation, ValueError, AttributeError) as exc:
                        raise ValidationError(
                            f"Invalid price '{p_str}' for product {product.item.name}."
                        ) from exc
                else:
                    p = resolve_product_price(customer, product)

                lines_data.append(
                    {
                        "product": product,
                        "quantity": q,
                        "unit_price": p,
                    }
                )

            if not lines_data:
                raise ValidationError("Please add at least one product with a valid quantity.")

            order = create_sales_order(
                salesman=user,
                customer=customer,
                lines_data=lines_data,
                status=target_status,
                notes=notes,
                order_date=order_date_val,
            )

            if target_status == Order.Status.SUBMITTED:
                messages.success(
                    request,
                    f"Order {order.order_number} submitted to Factory Admin for verification! (Total: ₹{order.total_amount})",
                )
            else:
                messages.success(
                    request,
                    f"Order {order.order_number} saved as Draft. (Total: ₹{order.total_amount})",
                )

            return redirect("salesman:workspace")

        except Customer.DoesNotExist:
            messages.error(request, "Selected customer is not found or inactive.")
        except Product.DoesNotExist:
            messages.error(request, "One of the selected products is invalid.")
        except ValidationError as e:
            messages.error(request, e.message if hasattr(e, "message") else str(e))
        except Exception as e:
            logger.exception("Unexpected error creating sales order.")
            messages.error(request, f"Unable to process order: {e}")

    # Fetch Catalog & Customers
    active_customers = Customer.objects.filter(is_active=True).order_by("name")
    assigned_customers = active_customers.filter(assigned_salesman=user)
    other_customers = active_customers.exclude(assigned_salesman=user)

    active_products = (
        Product.objects.filter(item__is_active=True)
        .select_related("item", "item__base_unit")
        .order_by("item__name")
    )

    # Build customer metadata & price matrix for reactive Alpine.js frontend
    customer_meta = {}
    for c in active_customers:
        customer_meta[str(c.id)] = {
            "id": c.id,
            "name": c.name,
            "code": c.code,
            "type": c.get_customer_type_display(),
            "state_code": c.state_code,
            "is_intrastate": (c.state_code == seller_state),
            "gstin": c.gstin or "Unregistered",
            "phone": c.phone or "",
        }

    # Pre-resolve prices for every (customer, product) combination for instant UI response
    price_matrix = {}
    for c in active_customers:
        price_matrix[str(c.id)] = {}
        for p in active_products:
            resolved_p = resolve_product_price(c, p)
            price_matrix[str(c.id)][str(p.id)] = str(resolved_p)

    # Product catalog metadata
    product_meta = {}
    for p in active_products:
        product_meta[str(p.id)] = {
            "id": p.id,
            "name": p.item.name,
            "code": p.item.code,
            "pack_size_g": str(p.pack_size_g),
            "packets_per_carton": p.packets_per_carton,
            "gst_rate": str(p.item.gst_rate),
            "list_price": str(p.list_price),
            "hsn_code": p.item.hsn_code,
        }

    # Order statistics
    draft_count = orders_qs.filter(status=Order.Status.DRAFT).count()
    submitted_count = orders_qs.filter(status=Order.Status.SUBMITTED).count()
    verified_count = orders_qs.filter(
        status__in=[Order.Status.VERIFIED, Order.Status.INVOICED, Order.Status.DISPATCHED]
    ).count()

    context = {
        "page_title": "Salesman Order Entry | Kaveri Foods",
        "role_code": "salesman",
        "role_display": "Salesman Order Entry",
        "role_description": "Mobile order entry portal for on-field sales representatives. Quick catalog lookup, draft orders, and offline queueing.",
        "assigned_customers": assigned_customers,
        "other_customers": other_customers,
        "active_products": active_products,
        "orders": orders_qs[:30],
        "draft_count": draft_count,
        "submitted_count": submitted_count,
        "verified_count": verified_count,
        "seller_state": seller_state,
        "customer_meta_json": json.dumps(customer_meta),
        "price_matrix_json": json.dumps(price_matrix),
        "product_meta_json": json.dumps(product_meta),
    }

    return render(request, "roles/salesman_workspace.html", context)


@require_POST
@role_required("salesman", "admin_desk")
def submit_draft_order_view(request, order_id: int):
    """
    Submits an existing DRAFT order for Admin Desk verification.
    """
    user = request.user
    is_admin = user.groups.filter(name="admin_desk").exists() or user.is_superuser

    if is_admin:
        order = get_object_or_404(Order, pk=order_id)
    else:
        order = get_object_or_404(Order, pk=order_id, salesman=user)

    try:
        submit_sales_order(order, user)
        messages.success(
            request,
            f"Order {order.order_number} submitted to Factory Admin for verification! (Total: ₹{order.total_amount})",
        )
    except ValidationError as e:
        messages.error(request, e.message if hasattr(e, "message") else str(e))
    except Exception as e:
        logger.exception("Failed to submit draft order.")
        messages.error(request, f"Error submitting order: {e}")

    return redirect("salesman:workspace")


@require_GET
@role_required("salesman", "admin_desk")
def customer_pricing_api(request):
    """
    JSON API returning customer details and resolved catalog prices.
    GET /salesman/api/pricing/?customer_id=123
    """
    customer_id = request.GET.get("customer_id")
    if not customer_id:
        return HttpResponseBadRequest("customer_id query parameter is required.")

    customer = get_object_or_404(Customer, pk=customer_id, is_active=True)
    seller_state = getattr(settings, "SELLER_STATE_CODE", "33")
    is_intrastate = customer.state_code == seller_state

    products = (
        Product.objects.filter(item__is_active=True).select_related("item").order_by("item__name")
    )

    prices = {}
    for product in products:
        resolved_price = resolve_product_price(customer, product)
        prices[product.id] = {
            "product_id": product.id,
            "product_name": product.item.name,
            "unit_price": str(resolved_price),
            "gst_rate": str(product.item.gst_rate),
            "pack_size_g": str(product.pack_size_g),
            "packets_per_carton": product.packets_per_carton,
        }

    return JsonResponse(
        {
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "code": customer.code,
                "type": customer.get_customer_type_display(),
                "state_code": customer.state_code,
                "is_intrastate": is_intrastate,
                "gstin": customer.gstin or "",
            },
            "prices": prices,
        }
    )
