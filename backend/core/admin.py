"""
StoreAdmin base class.

Scopes Django admin list/detail views to request.store.
Story 1.3: STUB — filters by store when request.store is set.
Story 1.5: adds full RBAC checks (platform_admin sees all stores).

Usage:
  @admin.register(Product)
  class ProductAdmin(StoreAdmin):
      list_display = ["name", "price"]

Implementation: Story 1.3
"""

from django.contrib import admin


class StoreAdmin(admin.ModelAdmin):
    """
    Base admin class that scopes querysets to the current store.

    When request.store is set (store staff), only that store's records
    are visible.  When request.store is None (platform admin path), the
    full queryset is returned — Story 1.5 will add role gating.
    """

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        store = getattr(request, "store", None)
        if store is not None:
            return qs.filter(store=store)
        return qs
