"""
TenantModel + SoftDeleteModel base classes.

TenantModel:
  - Adds store FK (ForeignKey to apps.store.Store)
  - All querysets filtered by request.store automatically via TenantQuerySet
  - Never query without store scope — enforced at queryset level

SoftDeleteModel:
  - Adds is_deleted + deleted_at fields
  - Uses django-safedelete; objects.all() excludes soft-deleted by default
  - Hard delete only via admin with explicit confirmation

Implementation: Story 1.2
"""
# TODO: Story 1.2 — implement TenantModel and SoftDeleteModel
