"""
Product catalog URL configuration — Story 4.1.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.product.views import (
    CategoryViewSet,
    ProductImageViewSet,
    ProductViewSet,
    PublicProductQRScanView,
    VariantViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("products", ProductViewSet, basename="product")
router.register("variants", VariantViewSet, basename="variant")
router.register("product-images", ProductImageViewSet, basename="product-image")

urlpatterns = [
    path("", include(router.urls)),
    path("products/<uuid:pk>/qr/", ProductViewSet.as_view({"get": "qr"}), name="product-qr"),
]
