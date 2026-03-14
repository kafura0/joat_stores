"""
Public (AllowAny) product URL routes — Story 4.1.
Mounted at /p/ in config/urls.py.
"""

from django.urls import path

from apps.product.views import PublicProductQRScanView

urlpatterns = [
    path("scan/", PublicProductQRScanView.as_view(), name="product-qr-scan"),
]
