"""
URL Configuration for Sales and Order Entry.
"""

from django.urls import path

from apps.sales import views

app_name = "salesman"

urlpatterns = [
    path("", views.salesman_workspace_view, name="workspace"),
    path("orders/<int:order_id>/submit/", views.submit_draft_order_view, name="order_submit"),
    path("api/pricing/", views.customer_pricing_api, name="customer_pricing"),
]
