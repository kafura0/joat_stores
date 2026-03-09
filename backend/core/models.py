"""
TenantModel + SoftDeleteModel base classes.

TenantModel:
  - Adds store FK (ForeignKey to apps.store.Store)
  - Uses "store.Store" lazy string ref to avoid circular import
  - All querysets filtered by request.store automatically via TenantQuerySet (Story 1.3)
  - Never query without store scope — enforced at queryset level

SoftDeleteModel:
  - For models that need soft-delete but are NOT tenant-scoped (e.g. Store itself)
  - Uses django-safedelete SOFT_DELETE_CASCADE policy

Implementation: Story 1.2
"""

from django.db import models

from safedelete.models import SOFT_DELETE_CASCADE, SafeDeleteModel


class SoftDeleteModel(SafeDeleteModel):
    """
    Base for models needing soft-delete without a tenant FK.

    Examples: Store itself (it IS the tenant root).
    """

    _safedelete_policy = SOFT_DELETE_CASCADE

    class Meta:
        abstract = True


class TenantModel(SafeDeleteModel):
    """
    Base class for ALL tenant-scoped domain models.

    Adds store FK.  TenantQuerySet auto-filter wired in Story 1.3.

    RULE: Every domain model MUST inherit from TenantModel — never models.Model.
    RULE: Use "store.Store" string ref — avoids circular import.
    """

    _safedelete_policy = SOFT_DELETE_CASCADE

    store = models.ForeignKey(
        "store.Store",  # lazy string — app_label.ModelName
        on_delete=models.CASCADE,
        related_name="+",
        db_index=True,
    )

    class Meta:
        abstract = True
