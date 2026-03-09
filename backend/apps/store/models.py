"""
Store model — the tenant root for joat_stores.

Each Store is an independent tenant.  All domain models (Product, Order, etc.)
have a store FK via TenantModel.

Key design decisions:
  - UUID primary key (not integer) — used in X-Store-ID header and JWT claims
  - django-safedelete with SOFT_DELETE_CASCADE — DPA-compliant deletion
  - tenant_type is immutable once orders exist (FR4 guard in save())
  - ArrayField for payment_methods requires django.contrib.postgres in INSTALLED_APPS

Story 1.2 adds: Store, StoreSettings stub, StoreTheme stub
Story 1.4 adds: Store provisioning API, StoreSubscription FK
Story 1.7 adds: StoreSettings + StoreTheme full implementation (branding)
"""

import uuid

from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from safedelete.models import SOFT_DELETE_CASCADE, SafeDeleteModel
from safedelete.queryset import SafeDeleteQueryset

from core.models import TenantModel


class TenantType(models.TextChoices):
    RETAIL = "retail", _("Retail")
    RESTAURANT = "restaurant", _("Restaurant")
    BAR = "bar", _("Bar")
    CONTRACTING = "contracting", _("Contracting")


class StoreStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    ACTIVE = "active", _("Active")
    SUSPENDED = "suspended", _("Suspended")
    CANCELLED = "cancelled", _("Cancelled")


class StoreQuerySet(SafeDeleteQueryset):
    """Custom queryset for Store model."""

    def active(self):
        """Return only active stores."""
        return self.filter(status=StoreStatus.ACTIVE)


class Store(SafeDeleteModel):
    """
    Tenant root model.

    Represents a merchant store (retail shop, restaurant, bar, or contractor).
    All other domain models reference this via TenantModel.store FK.
    """

    _safedelete_policy = SOFT_DELETE_CASCADE

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    # FQDN used for Nginx domain routing + TenantMiddleware resolution
    domain = models.CharField(max_length=253, unique=True, db_index=True)
    tenant_type = models.CharField(
        max_length=20,
        choices=TenantType.choices,
        default=TenantType.RETAIL,
    )
    status = models.CharField(
        max_length=20,
        choices=StoreStatus.choices,
        default=StoreStatus.PENDING,
    )
    # ISO 4217 3-letter currency code (e.g. "KES")
    currency = models.CharField(max_length=3, default="KES")
    # Enabled payment methods (e.g. ["mpesa", "card"])
    payment_methods = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
    )
    # ISO 3166-1 alpha-2 country code (e.g. "KE")
    country = models.CharField(max_length=2, default="KE")
    # IANA timezone string (e.g. "Africa/Nairobi")
    timezone = models.CharField(max_length=63, default="Africa/Nairobi")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = StoreQuerySet.as_manager()

    class Meta:
        db_table = "store_store"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.domain})"

    def save(self, *args, **kwargs):
        """
        FR4: tenant_type is immutable once orders exist.

        On update, if tenant_type is being changed and the store already has
        orders, raise ValidationError.  The guard is application-level only —
        no DB constraint is added.  The lazy import ensures this works even
        before the Order model migration has run.
        """
        if self.pk:
            original = Store.objects.filter(pk=self.pk).first()
            if original and original.tenant_type != self.tenant_type:
                from apps.order.models import Order  # lazy — avoids circular import

                if Order.objects.filter(store=self).exists():
                    raise ValidationError(
                        "tenant_type cannot be changed after orders exist"
                    )
        super().save(*args, **kwargs)


class StoreSettings(TenantModel):
    """
    Per-store configuration settings.

    Stub — full implementation in Story 1.7 (branding + storefront config).
    """

    class Meta:
        db_table = "store_storesettings"

    def __str__(self):
        return f"Settings for {self.store}"


class StoreTheme(TenantModel):
    """
    Per-store branding theme (colours, fonts, logo).

    Stub — full implementation in Story 1.7 (storefront shell + tenant branding).
    """

    class Meta:
        db_table = "store_storetheme"

    def __str__(self):
        return f"Theme for {self.store}"
