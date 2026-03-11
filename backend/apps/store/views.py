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

from apps.store.models import Store
from apps.store.serializers import (
    BrandingSerializer,
    StoreDetailSerializer,
    StoreProvisionSerializer,
    StoreStatusSerializer,
)
from core.permissions import IsPlatformAdmin

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

    permission_classes = [AllowAny]

    def get(self, request):
        store = getattr(request, "store", None)
        if store is None:
            return Response(
                {
                    "errors": [
                        {
                            "field": None,
                            "message": "Store not found.",
                            "code": "STORE_NOT_FOUND",
                        }
                    ]
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = BrandingSerializer(store)
        data = serializer.data

        if store.status == "suspended":
            return Response({"data": data}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({"data": data})
