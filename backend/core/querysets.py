"""
TenantQuerySet

Base queryset that auto-filters by store_id on every query.
Prevents cross-tenant data leakage at the ORM layer.

Usage:
  class ProductQuerySet(TenantQuerySet):
      pass

  class Product(TenantModel):
      objects = ProductQuerySet.as_manager()

Implementation: Story 1.3
"""
# TODO: Story 1.3 — implement TenantQuerySet
