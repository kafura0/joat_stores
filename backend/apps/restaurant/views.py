"""
Restaurant views — Story 3.1 (Menu Management API).

All viewsets extend TenantViewSet for automatic tenant scoping.
MenuItemViewSet applies time-based availability filtering on list queries.
"""

from django.utils import timezone

import structlog

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
            now_time = timezone.localtime().time()
            # Items with no time window are always included
            # Items with a window: must be within available_from..available_until
            # Django ORM: Q objects to express the filter
            from django.db.models import Q

            qs = qs.filter(
                Q(available_from__isnull=True, available_until__isnull=True)
                | Q(
                    available_from__isnull=False,
                    available_until__isnull=False,
                    available_from__lte=now_time,
                    available_until__gte=now_time,
                )
                | Q(available_from__isnull=False, available_until__isnull=True,
                    available_from__lte=now_time)
                | Q(available_from__isnull=True, available_until__isnull=False,
                    available_until__gte=now_time)
            )

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
