"""
Restaurant views.

Story 3.1: MenuSectionViewSet, MenuItemViewSet, ModifierGroupViewSet, ModifierViewSet
Story 3.2: PublicMenuView (no auth, SSR-friendly JSON for current service window)

All management viewsets extend TenantViewSet for automatic tenant scoping.
"""

from django.db.models import Q, Prefetch
from django.utils import timezone

import structlog
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import StoreCursorPagination
from core.views import TenantViewSet

from apps.restaurant.models import MenuItem, MenuSection, Modifier, ModifierGroup
from apps.restaurant.serializers import (
    MenuItemSerializer,
    MenuSectionSerializer,
    ModifierGroupSerializer,
    ModifierSerializer,
)

log = structlog.get_logger(__name__)


def _filter_available_items(qs):
    """Return qs filtered to items within their time window (if any)."""
    now_time = timezone.localtime().time()
    return qs.filter(
        Q(available_from__isnull=True, available_until__isnull=True)
        | Q(
            available_from__isnull=False,
            available_until__isnull=False,
            available_from__lte=now_time,
            available_until__gte=now_time,
        )
        | Q(
            available_from__isnull=False,
            available_until__isnull=True,
            available_from__lte=now_time,
        )
        | Q(
            available_from__isnull=True,
            available_until__isnull=False,
            available_until__gte=now_time,
        )
    )


class MenuSectionViewSet(TenantViewSet):
    """CRUD for menu sections. Ordered by position then name."""

    serializer_class = MenuSectionSerializer
    queryset = MenuSection.objects.all()

    class _Pagination(StoreCursorPagination):
        ordering = "position"

    pagination_class = _Pagination


class MenuItemViewSet(TenantViewSet):
    """
    CRUD for menu items.

    List endpoint filters out items that are outside their scheduled availability
    window. Detail/create/update endpoints return/accept all items regardless of
    time window (admin needs to manage all items).
    """

    serializer_class = MenuItemSerializer
    queryset = MenuItem.objects.all()

    class _Pagination(StoreCursorPagination):
        ordering = "position"

    pagination_class = _Pagination

    def get_queryset(self):
        qs = super().get_queryset()

        # Time-based filtering on list action only
        if self.action == "list":
            qs = _filter_available_items(qs)

        return qs


class ModifierGroupViewSet(TenantViewSet):
    """CRUD for modifier groups."""

    serializer_class = ModifierGroupSerializer
    queryset = ModifierGroup.objects.all()

    class _Pagination(StoreCursorPagination):
        ordering = "name"

    pagination_class = _Pagination


class ModifierViewSet(TenantViewSet):
    """CRUD for modifiers."""

    serializer_class = ModifierSerializer
    queryset = Modifier.objects.all()

    class _Pagination(StoreCursorPagination):
        ordering = "name"

    pagination_class = _Pagination


class PublicMenuView(APIView):
    """
    Story 3.2 — Public menu endpoint.

    Returns all menu sections with their currently-available items for the
    resolved store. No authentication required (AllowAny).

    GET /api/v1/restaurant/public-menu/
    """

    permission_classes = [AllowAny]

    def get(self, request):
        store = getattr(request, "store", None)
        if store is None:
            return Response({"errors": [{"code": "STORE_NOT_FOUND"}]}, status=404)

        # Prefetch available items for performance (avoids N+1)
        available_items_qs = _filter_available_items(
            MenuItem.objects.filter(store=store, is_available=True)
        ).prefetch_related("modifier_groups__modifiers")

        sections = (
            MenuSection.objects.filter(store=store)
            .prefetch_related(
                Prefetch("items", queryset=available_items_qs)
            )
            .order_by("position", "name")
        )

        data = MenuSectionSerializer(sections, many=True).data
        log.info("public_menu_served", store_id=str(store.id))
        return Response({"data": data})
