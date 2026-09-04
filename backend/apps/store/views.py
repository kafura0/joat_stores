"""
Platform admin views for store provisioning and management.

These are NOT tenant-scoped (they don't use TenantViewSet) — they operate
at the platform level with IsPlatformAdmin permission.

Implementation: Story 1.4
"""

import logging

from django.db import transaction

from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.store.models import Store, StoreSettings, StoreTheme
from apps.store.serializers import (
    BrandingSerializer,
    StoreDetailSerializer,
    StoreProvisionSerializer,
    StoreSettingsSerializer,
    StoreStatusSerializer,
    ThemeSerializer,
)
from apps.store.presets import PRESETS, apply_preset
from core.permissions import HasStore, IsPlatformAdmin, IsStoreManager

logger = logging.getLogger(__name__)


class StoreProvisionView(generics.CreateAPIView):
    """
    POST /api/v1/platform/stores/

    Atomically provisions a new store with subscription and owner.
    """

    permission_classes = [IsPlatformAdmin]
    serializer_class = StoreProvisionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        store = serializer.save()
        detail = StoreDetailSerializer(store).data

        # Include onboarding details in response
        onboarding = getattr(store, "_onboarding", None)
        if onboarding:
            detail["onboarding"] = onboarding

        return Response(
            {"data": detail},
            status=status.HTTP_201_CREATED,
        )


class StoreListView(generics.ListAPIView):
    """
    GET /api/v1/platform/stores/

    Lists all stores. Platform admin only.
    """

    permission_classes = [IsPlatformAdmin]
    serializer_class = StoreDetailSerializer
    queryset = Store.objects.all().select_related("subscription")


class StoreStatusUpdateView(APIView):
    """
    PATCH /api/v1/platform/stores/{id}/status/

    Updates store status with transition validation.
    Logs StoreStatusChanged event.
    """

    permission_classes = [IsPlatformAdmin]

    def patch(self, request, pk):
        with transaction.atomic():
            try:
                # select_for_update prevents concurrent PATCH requests from
                # both reading the same status and applying duplicate transitions.
                store = Store.objects.select_for_update().get(pk=pk)
            except Store.DoesNotExist:
                return Response(
                    {
                        "errors": [
                            {
                                "field": None,
                                "message": "Store not found.",
                                "code": "NOT_FOUND",
                            }
                        ]
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = StoreStatusSerializer(
                data=request.data,
                context={"store": store},
            )
            serializer.is_valid(raise_exception=True)

            old_status = store.status
            store.status = serializer.validated_data["status"]
            store.save(update_fields=["status", "updated_at"])

        logger.info(
            "StoreStatusChanged",
            extra={
                "store_id": str(store.pk),
                "old_status": old_status,
                "new_status": store.status,
            },
        )

        detail = StoreDetailSerializer(store).data
        return Response({"data": detail})


class OfflineInventorySnapshotView(APIView):
    """
    GET /api/v1/store/offline-snapshot/

    Story 12.5 — PWA offline inventory snapshot.

    Returns a compact JSON payload of all active products + variant inventory
    levels for service worker caching. The PWA can use this to show stock
    levels when the device is offline.

    Designed for periodic background sync — SW fetches this every 30 minutes.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        store = getattr(request, "store", None)
        if store is None:
            return Response(
                {"errors": [{"code": "STORE_NOT_FOUND", "message": "Store not resolved."}]},
                status=404,
            )

        from apps.product.models import Product

        products = (
            Product.objects.filter(store=store, is_available=True)
            .prefetch_related("variants")
        )

        snapshot = []
        for product in products:
            variants = [
                {
                    "id": str(v.id),
                    "sku": v.sku,
                    "name": v.name,
                    "price": str(v.price),
                    "inventory_count": v.inventory_count,
                    "is_in_stock": v.inventory_count > 0,
                }
                for v in product.variants.all()
            ]
            snapshot.append({
                "id": str(product.id),
                "name": product.name,
                "variants": variants,
            })

        from django.utils import timezone
        return Response({
            "store_id": str(store.id),
            "generated_at": timezone.now().isoformat(),
            "product_count": len(snapshot),
            "products": snapshot,
        })


class BrandingView(APIView):
    """
    GET /api/v1/store/branding/

    Public endpoint — no authentication required.
    Returns tenant branding (colours, logo, tagline) for storefront SSR.
    Resolved via TenantMiddleware from X-Store-ID header or Host.

    Returns 503 if store is suspended (with store_name still included
    so the storefront can render a branded error page).

    Implementation: Story 1.7
    """

    permission_classes = [HasStore]

    def get(self, request):
        store = request.store

        serializer = BrandingSerializer(store)
        data = serializer.data

        if store.status == "suspended":
            return Response({"data": data}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({"data": data})


class ThemeDetailView(APIView):
    """
    GET    /api/v1/store/themes/ — current theme (all design tokens)
    PATCH  /api/v1/store/themes/ — partial update of theme tokens
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [HasStore()]
        return [IsStoreManager()]

    def get(self, request):
        theme, _ = StoreTheme.objects.get_or_create(store=request.store)
        return Response({"data": ThemeSerializer(theme).data})

    def patch(self, request):
        theme, _ = StoreTheme.objects.get_or_create(store=request.store)
        serializer = ThemeSerializer(theme, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"data": serializer.data})


class PresetListView(APIView):
    """
    GET /api/v1/store/themes/presets/ — list available presets with metadata.
    """

    permission_classes = [HasStore]

    def get(self, request):
        result = []
        for slug, data in PRESETS.items():
            result.append({
                "slug": slug,
                "label": slug.capitalize(),
                "description": self._describe(slug),
                "thumbnail_url": None,
            })
        return Response({"data": {"presets": result}})

    @staticmethod
    def _describe(slug):
        descriptions = {
            "modern": "Clean, dark header, sharp corners. Best for retail.",
            "classic": "Serif fonts, warm tones, traditional feel. Best for restaurants.",
            "minimal": "Black & white, lots of whitespace, subtle shadows. Best for premium brands.",
            "bold": "Dark mode with purple accents, large headings. Best for nightlife / bars.",
            "vibrant": "Cyan & orange palette, playful. Best for cafes & fast food.",
        }
        return descriptions.get(slug, "")


class ApplyPresetView(APIView):
    """
    POST /api/v1/store/themes/apply-preset/
    Body: {"preset": "modern"}
    """

    permission_classes = [IsStoreManager]

    def post(self, request):
        slug = request.data.get("preset", "").strip()
        if slug not in PRESETS:
            return Response(
                {"errors": [{"code": "INVALID_PRESET", "message": f"Unknown preset: {slug}. Available: {', '.join(PRESETS)}"}]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        theme, _ = StoreTheme.objects.get_or_create(store=request.store)
        apply_preset(theme, slug)
        return Response({"data": ThemeSerializer(theme).data})


class StoreSettingsView(APIView):
    """
    GET    /api/v1/store/settings/ — current store settings
    PATCH  /api/v1/store/settings/ — partial update of store settings
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [HasStore()]
        return [IsStoreManager()]

    def get(self, request):
        settings, _ = StoreSettings.objects.get_or_create(store=request.store)
        return Response({"data": StoreSettingsSerializer(settings).data})

    def patch(self, request):
        settings, _ = StoreSettings.objects.get_or_create(store=request.store)
        serializer = StoreSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"data": serializer.data})


class StoreLogoUploadView(APIView):
    """
    POST /api/v1/store/settings/logo/ — upload store logo

    Accepts multipart/form-data with 'image' file field.
    Compresses to WebP <= 500KB, saves to MEDIA_ROOT/logos/,
    and updates StoreSettings.logo_url with the served URL.
    """

    permission_classes = [IsStoreManager]

    def post(self, request):
        uploaded = request.FILES.get("image")
        if not uploaded:
            return Response(
                {"errors": [{"code": "NO_FILE", "message": "No image file provided."}]},
                status=400,
            )

        # Validate file type
        allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        if uploaded.content_type not in allowed:
            return Response(
                {"errors": [{"code": "INVALID_TYPE", "message": "Upload a JPEG, PNG, WebP, or GIF image."}]},
                status=400,
            )

        # Validate file size (max 5MB)
        if uploaded.size > 5 * 1024 * 1024:
            return Response(
                {"errors": [{"code": "FILE_TOO_LARGE", "message": "Image must be under 5MB."}]},
                status=400,
            )

        try:
            from PIL import Image
            import io

            img = Image.open(uploaded)
            img = img.convert("RGBA") if img.mode == "RGBA" else img.convert("RGB")

            # Resize to max 400x400 for logos
            img.thumbnail((400, 400), Image.Resampling.LANCZOS)

            buf = io.BytesIO()
            img.save(buf, format="WEBP", quality=85)
            buf.seek(0)

            # Save to MEDIA_ROOT/logos/
            import os
            from django.conf import settings

            logo_dir = os.path.join(settings.MEDIA_ROOT, "logos")
            os.makedirs(logo_dir, exist_ok=True)

            filename = f"{request.store.id}_logo.webp"
            filepath = os.path.join(logo_dir, filename)

            with open(filepath, "wb") as f:
                f.write(buf.read())

            # Build URL
            logo_url = f"{settings.MEDIA_URL}logos/{filename}"

            # Update store settings
            store_settings, _ = StoreSettings.objects.get_or_create(store=request.store)
            store_settings.logo_url = logo_url
            store_settings.save(update_fields=["logo_url"])

            return Response({
                "logo_url": logo_url,
                "message": "Logo uploaded successfully.",
            })

        except Exception as e:
            import structlog
            log = structlog.get_logger(__name__)
            log.exception("logo_upload_failed", store_id=str(request.store.id))
            return Response(
                {"errors": [{"code": "UPLOAD_FAILED", "message": "Failed to process image."}]},
                status=500,
            )
