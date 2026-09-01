"""
Order app URL configuration — Stories 4.2, 4.3, 4.4, 4.8.
Mounted at /api/v1/store/ in config/urls.py.
"""

from django.urls import path

from apps.order.merchant_views import (
    CustomerDetailView,
    CustomerListView,
    InventoryListView,
    OrderListView,
    StaffListView,
)
from apps.order.views import (
    CartMergeView,
    CartView,
    CheckoutView,
    MerchantDashboardView,
    OrderConfirmView,
    OrderDetailView,
    OrderStatusView,
)

urlpatterns = [
    # Cart — Story 4.2
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/merge/", CartMergeView.as_view(), name="cart-merge"),
    # Checkout — Story 4.4
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    # Order management — Story 4.3
    path("orders/", OrderListView.as_view(), name="order-list"),
    path("orders/<uuid:order_id>/", OrderDetailView.as_view(), name="order-detail"),
    path("orders/<uuid:order_id>/status/", OrderStatusView.as_view(), name="order-status"),
    path("orders/<uuid:order_id>/confirm/", OrderConfirmView.as_view(), name="order-confirm"),
    # Merchant dashboard — Story 4.3b
    path("dashboard/", MerchantDashboardView.as_view(), name="merchant-dashboard"),
    # Customers
    path("customers/", CustomerListView.as_view(), name="customer-list"),
    path("customers/<int:customer_id>/", CustomerDetailView.as_view(), name="customer-detail"),
    # Inventory
    path("inventory/", InventoryListView.as_view(), name="inventory-list"),
    # Staff
    path("users/", StaffListView.as_view(), name="staff-list"),
]
