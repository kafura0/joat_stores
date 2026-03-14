"""
Restaurant URL configuration — Story 3.1 + 3.2.
"""

from django.urls import path

from rest_framework.routers import DefaultRouter

from apps.restaurant.views import (
    MenuItemViewSet,
    MenuSectionViewSet,
    ModifierGroupViewSet,
    ModifierViewSet,
    PublicMenuView,
)

router = DefaultRouter()
router.register(r"menu-sections", MenuSectionViewSet, basename="menu-sections")
router.register(r"menu-items", MenuItemViewSet, basename="menu-items")
router.register(r"modifier-groups", ModifierGroupViewSet, basename="modifier-groups")
router.register(r"modifiers", ModifierViewSet, basename="modifiers")

urlpatterns = router.urls + [
    path("public-menu/", PublicMenuView.as_view(), name="public-menu"),
]
