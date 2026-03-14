"""
Restaurant URL configuration — Stories 3.1, 3.2, 3.3.
"""

from django.urls import path

from rest_framework.routers import DefaultRouter

from apps.restaurant.views import (
    MenuItemViewSet,
    MenuSectionViewSet,
    ModifierGroupViewSet,
    ModifierViewSet,
    PublicMenuView,
    QRTokenGenerateView,
    QRTokenValidateView,
    TableViewSet,
)

router = DefaultRouter()
router.register(r"menu-sections", MenuSectionViewSet, basename="menu-sections")
router.register(r"menu-items", MenuItemViewSet, basename="menu-items")
router.register(r"modifier-groups", ModifierGroupViewSet, basename="modifier-groups")
router.register(r"modifiers", ModifierViewSet, basename="modifiers")
router.register(r"tables", TableViewSet, basename="tables")

urlpatterns = router.urls + [
    path("public-menu/", PublicMenuView.as_view(), name="public-menu"),
    path(
        "tables/<uuid:table_id>/qr-token/",
        QRTokenGenerateView.as_view(),
        name="table-qr-token",
    ),
    path("qr/validate/", QRTokenValidateView.as_view(), name="qr-validate"),
]
