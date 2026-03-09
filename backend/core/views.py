"""
TenantViewSet base class.

Extends ModelViewSet with:
  - get_queryset() scoped to request.store automatically (via TenantQuerySet.for_store)
  - perform_create() injects store from request
  - Permission class: IsStoreScoped by default (stub in Story 1.3, full check in 1.5)
  - Pagination: StoreCursorPagination by default

All domain viewsets MUST extend TenantViewSet — never ModelViewSet directly.

Usage:
  class ProductViewSet(TenantViewSet):
      serializer_class = ProductSerializer
      queryset = Product.objects.all()

Implementation: Story 1.3
"""

from rest_framework import viewsets

from core.pagination import StoreCursorPagination
from core.permissions import IsStoreScoped


class TenantViewSet(viewsets.ModelViewSet):
    """
    Base viewset for all tenant-scoped API endpoints.

    Automatically scopes queries and object creation to request.store.
    """

    pagination_class = StoreCursorPagination
    permission_classes = [IsStoreScoped]

    def get_queryset(self):
        qs = super().get_queryset()
        store = getattr(self.request, "store", None)
        if store and hasattr(qs, "for_store"):
            return qs.for_store(store)
        return qs

    def perform_create(self, serializer):
        serializer.save(store=self.request.store)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context
