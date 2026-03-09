"""
TenantModel + SoftDeleteModel base classes.

TenantModel:
  - UUID primary key (never exposes auto-increment integers in API URLs)
  - store FK (ForeignKey to apps.store.Store — lazy string ref avoids circular import)
  - TenantQuerySet as default manager (auto-filter by store_id via .for_store())
  - SOFT_DELETE_CASCADE policy (django-safedelete)

SoftDeleteModel:
  - For models that need soft-delete but are NOT tenant-scoped (e.g. Store itself)

Implementation: Story 1.2 (base), Story 1.3 (UUID PK + TenantQuerySet wired)
"""

import uuid

from django.db import models

from safedelete.models import SOFT_DELETE_CASCADE, SafeDeleteModel

from core.querysets import TenantQuerySet


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

    - UUID primary key — never exposes integer IDs in API or URL paths
    - store FK — all records belong to exactly one Store
    - TenantQuerySet — .for_store(store) scopes all queries to one tenant
    - SOFT_DELETE_CASCADE — DPA-compliant soft deletion

    RULE: Every domain model MUST inherit from TenantModel — never models.Model.
    RULE: Use "store.Store" string ref in FK — avoids circular import.
    """

    _safedelete_policy = SOFT_DELETE_CASCADE

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        "store.Store",  # lazy string — app_label.ModelName
        on_delete=models.CASCADE,
        related_name="+",
        db_index=True,
    )

    objects = TenantQuerySet.as_manager()

    class Meta:
        abstract = True
