"""
TenantQuerySet

Base queryset that scopes every query to a single store.
Prevents cross-tenant data leakage at the ORM layer.

Usage:
  class ProductQuerySet(TenantQuerySet):
      pass

  class Product(TenantModel):
      objects = ProductQuerySet.as_manager()

  # In a view:
  Product.objects.for_store(request.store).get(pk=pk)

Implementation: Story 1.3
"""

from safedelete.queryset import SafeDeleteQueryset


class TenantQuerySet(SafeDeleteQueryset):
    """
    Base queryset for all tenant-scoped models.

    Call .for_store(store) to scope the queryset to a single tenant.
    TenantViewSet.get_queryset() does this automatically on every request.
    """

    def for_store(self, store):
        """Return only records belonging to the given store."""
        return self.filter(store_id=store.pk)
