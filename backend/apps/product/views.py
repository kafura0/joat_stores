"""
Product catalog views — Story 4.1.

CategoryViewSet, ProductViewSet, VariantViewSet, ProductImageViewSet.
Product QR code generation (same HMAC scheme as restaurant table QR).
WebP image compression via Pillow on upload.
"""

import hashlib
import hmac
import io
import os
import uuid

import structlog
from django.conf import settings
from django.core.files.base import ContentFile
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import StoreCursorPagination
from core.permissions import HasPermission, IsStoreManager
from core.views import TenantViewSet

from apps.product.models import Category, Product, ProductImage, Variant
from apps.product.serializers import (
    CategorySerializer,
    ProductDetailSerializer,
    ProductImageSerializer,
    ProductImageUploadSerializer,
    ProductSerializer,
    VariantSerializer,
)

log = structlog.get_logger(__name__)

# Max WebP file size (800KB per Story 4.1 AC)
_MAX_WEBP_BYTES = 800 * 1024


def _compress_to_webp(image_file) -> bytes:
    """
    Compress an uploaded image to WebP format at ≤ 800KB.
    Iterates quality down from 85 until size target is met.
    """
    from PIL import Image

    img = Image.open(image_file)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")

    for quality in (85, 75, 65, 50, 35):
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=quality)
        if buf.tell() <= _MAX_WEBP_BYTES:
            return buf.getvalue()

    # Last resort: lowest quality
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=20)
    return buf.getvalue()


def _generate_product_qr_token(store_id: str, product_id: str, secret: str) -> str:
    """
    HMAC-SHA256 signed token for product QR code.
    Same signing scheme as restaurant table QR (FR22).
    Format: {store_id}.{product_id}.{hmac_hex}
    """
    payload = f"{store_id}.{product_id}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def _verify_product_qr_token(token: str, secret: str) -> dict | None:
    """Return {'store_id': ..., 'product_id': ...} or None if invalid."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        store_id, product_id, sig = parts
        expected = hmac.new(
            secret.encode(),
            f"{store_id}.{product_id}".encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        return {"store_id": store_id, "product_id": product_id}
    except Exception:
        return None


class CategoryViewSet(TenantViewSet):
    """CRUD for product categories — Story 4.1."""

    serializer_class = CategorySerializer
    queryset = Category.objects.all()

    class _Pagination(StoreCursorPagination):
        ordering = "position"

    pagination_class = _Pagination


class ProductViewSet(TenantViewSet):
    """
    CRUD for products — Story 4.1.

    List: paginated, available only.
    Detail: includes nested variants + images (ProductDetailSerializer).
    QR: GET /products/{id}/qr/ → PNG download.
    """

    queryset = Product.objects.prefetch_related(
        "variants__images",
        "images",
    )

    class _Pagination(StoreCursorPagination):
        ordering = "name"

    pagination_class = _Pagination

    def get_permissions(self):
        if self.action in ("list", "retrieve", "qr"):
            return [HasStore()]
        # create, update, partial_update, destroy → store_manager+
        return [IsStoreManager()]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            qs = qs.filter(is_available=True)
        return qs

    def perform_create(self, serializer):
        from apps.saas.models import PlanLimitExceeded, check_product_limit

        try:
            check_product_limit(self.request.store)
        except PlanLimitExceeded as exc:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                detail={
                    "code": "PLAN_LIMIT_EXCEEDED",
                    "limit_type": exc.limit_type,
                    "max": exc.max_value,
                    "message": f"Your plan allows a maximum of {exc.max_value} {exc.limit_type}. Upgrade to add more.",
                }
            )
        serializer.save(store=self.request.store)

    @action(detail=True, methods=["get"], url_path="qr")
    def qr(self, request, pk=None):
        """
        Story 4.1 — Generate product QR code.
        GET /api/v1/store/products/{id}/qr/
        Returns a PNG image encoding store_id + product_id + HMAC.
        """
        import qrcode
        import qrcode.image.pil

        product = self.get_object()
        secret = getattr(settings, "HMAC_QR_SECRET", "dev-qr-secret")
        token = _generate_product_qr_token(
            store_id=str(product.store_id),
            product_id=str(product.id),
            secret=secret,
        )

        # Encode the token as the QR URL — storefront resolves /p/scan/?token=...
        qr_url = f"/p/scan/?token={token}"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        log.info("product_qr_generated", product_id=str(product.id))
        return HttpResponse(buf.read(), content_type="image/png")


class VariantViewSet(TenantViewSet):
    """CRUD for product variants — Story 4.1."""

    serializer_class = VariantSerializer
    queryset = Variant.objects.prefetch_related("images")

    class _Pagination(StoreCursorPagination):
        ordering = "name"

    pagination_class = _Pagination


class ProductImportView(APIView):
    """
    POST /api/v1/store/products/import/

    Bulk import products from CSV.
    Expected CSV columns: name, price, category, stock, sku, description
    """

    permission_classes = [IsStoreManager]

    def post(self, request):
        import csv
        import io

        csv_file = request.FILES.get("file")
        if not csv_file:
            return Response(
                {"errors": [{"code": "NO_FILE", "message": "No file provided"}]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            decoded = csv_file.read().decode("utf-8")
            reader = csv.DictReader(io.StringIO(decoded))
        except Exception:
            return Response(
                {"errors": [{"code": "INVALID_CSV", "message": "Invalid CSV format"}]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = 0
        errors = []

        # Subscription limit check
        from apps.saas.models import PlanLimitExceeded, check_product_limit

        try:
            check_product_limit(request.store)
        except PlanLimitExceeded as exc:
            return Response(
                {
                    "errors": [{
                        "code": "PLAN_LIMIT_EXCEEDED",
                        "limit_type": exc.limit_type,
                        "max": exc.max_value,
                        "message": f"Your plan allows a maximum of {exc.max_value} {exc.limit_type}. Upgrade to import more products.",
                    }]
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Pre-compute category position (single query, not per-row)
        category_position = Category.objects.filter(store=request.store).count()

        for i, row in enumerate(reader, start=2):
            name = row.get("name", "").strip()
            if not name:
                errors.append({"row": i, "error": "Name is required"})
                continue

            try:
                price = float(row.get("price", 0))
            except (ValueError, TypeError):
                errors.append({"row": i, "error": "Invalid price"})
                continue

            # Find or create category
            category = None
            category_name = row.get("category", "").strip()
            if category_name:
                category, created_cat = Category.objects.get_or_create(
                    store=request.store,
                    name=category_name,
                    defaults={"position": category_position},
                )
                if created_cat:
                    category_position += 1

            # Create product
            product = Product.objects.create(
                store=request.store,
                name=name,
                description=row.get("description", "").strip(),
                category=category,
                is_available=True,
            )

            # Create default variant with price
            Variant.objects.create(
                store=request.store,
                product=product,
                attribute_values={"size": "default"},
                price=price,
                inventory_count=int(row.get("stock", 0)),
                sku=row.get("sku", "").strip(),
                is_available=True,
            )

            created += 1

        return Response({
            "data": {
                "created": created,
                "errors": errors,
                "total_rows": created + len(errors),
            }
        })

    def get_queryset(self):
        qs = super().get_queryset()
        product_id = self.request.query_params.get("product")
        if product_id:
            qs = qs.filter(product_id=product_id)
        return qs


class ProductImageViewSet(TenantViewSet):
    """
    Manage product images — Story 4.1.

    POST /api/v1/store/product-images/ with multipart/form-data.
    Uploaded image is compressed to WebP ≤ 800KB via Pillow.
    Original upload is deleted after compression.
    """

    serializer_class = ProductImageSerializer
    queryset = ProductImage.objects.all()

    class _Pagination(StoreCursorPagination):
        ordering = "position"

    pagination_class = _Pagination

    def create(self, request, *args, **kwargs):
        """Override create to compress image to WebP before saving."""
        serializer = ProductImageUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"errors": serializer.errors}, status=400)

        uploaded_file = request.FILES.get("image")
        if uploaded_file is None:
            return Response({"errors": [{"code": "IMAGE_REQUIRED"}]}, status=400)

        # Compress to WebP
        try:
            webp_bytes = _compress_to_webp(uploaded_file)
        except Exception as exc:
            log.error("image_compression_failed", error=str(exc))
            return Response({"errors": [{"code": "IMAGE_PROCESSING_FAILED"}]}, status=422)

        webp_filename = f"{uuid.uuid4().hex}.webp"
        webp_file = ContentFile(webp_bytes, name=webp_filename)

        instance = ProductImage(
            store=request.store,
            product=serializer.validated_data["product"],
            variant=serializer.validated_data.get("variant"),
            alt_text=serializer.validated_data.get("alt_text", ""),
            position=serializer.validated_data.get("position", 0),
            is_default=serializer.validated_data.get("is_default", False),
        )
        instance.image.save(webp_filename, webp_file, save=True)

        log.info(
            "product_image_uploaded",
            image_id=str(instance.id),
            product_id=str(instance.product_id),
            size_bytes=len(webp_bytes),
        )
        return Response(
            ProductImageSerializer(instance, context={"request": request}).data,
            status=201,
        )


class PublicProductQRScanView(APIView):
    """
    Story 4.1 — Resolve a scanned product QR token.

    GET /p/scan/?token=<token>
    Verifies HMAC; returns store_id + product_id for storefront redirect.
    Returns 403 if token is invalid (unsigned QR codes).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get("token", "")
        if not token:
            return Response({"errors": [{"code": "TOKEN_REQUIRED"}]}, status=400)

        secret = getattr(settings, "HMAC_QR_SECRET", "dev-qr-secret")
        payload = _verify_product_qr_token(token, secret)
        if payload is None:
            return Response({"errors": [{"code": "INVALID_QR_TOKEN"}]}, status=403)

        try:
            product = Product.objects.select_related("store").get(
                id=payload["product_id"],
                store_id=payload["store_id"],
            )
        except Product.DoesNotExist:
            return Response({"errors": [{"code": "PRODUCT_NOT_FOUND"}]}, status=404)

        return Response({
            "store_id": str(product.store_id),
            "product_id": str(product.id),
            "product_name": product.name,
            "redirect_url": f"/products/{product.id}/",
        })
