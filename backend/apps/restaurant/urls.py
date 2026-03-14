"""
Restaurant URL configuration — Stories 3.1, 3.2, 3.3, 3.4, 3.6, 3.6b, 3.7.
"""

from django.urls import path

from rest_framework.routers import DefaultRouter

from apps.restaurant.views import (
    DineInOrderView,
    KitchenTicketListView,
    KitchenTicketUpdateView,
    MenuItemViewSet,
    MenuSectionViewSet,
    ModifierGroupViewSet,
    ModifierViewSet,
    OrderStatusView,
    PendingOrderConvertView,
    PendingOrderCreateView,
    PendingOrderLookupView,
    PublicMenuView,
    QRTokenGenerateView,
    QRTokenValidateView,
    TableSessionViewSet,
    TableViewSet,
)

router = DefaultRouter()
router.register(r"menu-sections", MenuSectionViewSet, basename="menu-sections")
router.register(r"menu-items", MenuItemViewSet, basename="menu-items")
router.register(r"modifier-groups", ModifierGroupViewSet, basename="modifier-groups")
router.register(r"modifiers", ModifierViewSet, basename="modifiers")
router.register(r"tables", TableViewSet, basename="tables")
router.register(r"sessions", TableSessionViewSet, basename="sessions")

urlpatterns = router.urls + [
    path("public-menu/", PublicMenuView.as_view(), name="public-menu"),
    path(
        "tables/<uuid:table_id>/qr-token/",
        QRTokenGenerateView.as_view(),
        name="table-qr-token",
    ),
    path("qr/validate/", QRTokenValidateView.as_view(), name="qr-validate"),
    # Story 3.6 — dine-in orders + kitchen display
    path("orders/", DineInOrderView.as_view(), name="dinein-orders"),
    path("orders/<uuid:order_id>/status/", OrderStatusView.as_view(), name="order-status"),
    path("kitchen/tickets/", KitchenTicketListView.as_view(), name="kitchen-tickets"),
    path(
        "kitchen/tickets/<uuid:ticket_id>/",
        KitchenTicketUpdateView.as_view(),
        name="kitchen-ticket-update",
    ),
    # Story 3.7 — pending orders (pre-arrival) + waiter convert
    path("pending-orders/", PendingOrderCreateView.as_view(), name="pending-orders"),
    path("pending-orders/lookup/", PendingOrderLookupView.as_view(), name="pending-orders-lookup"),
    path(
        "pending-orders/<uuid:order_id>/convert/",
        PendingOrderConvertView.as_view(),
        name="pending-orders-convert",
    ),
]
