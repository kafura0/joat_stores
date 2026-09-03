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

import re
import uuid
from decimal import Decimal

from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

_CSS_COLOR_RE = re.compile(
    r"^(#([0-9a-fA-F]{3}){1,2}|rgb\(\d{1,3},\s*\d{1,3},\s*\d{1,3}\)|[a-zA-Z]+)$"
)
validate_css_color = RegexValidator(
    regex=_CSS_COLOR_RE,
    message="Enter a valid CSS colour value (hex, rgb(), or named colour).",
)

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
        no DB constraint is added.  Lazy imports avoid circular dependency
        issues; missing models are silently skipped (pre-migration safety).
        """
        if self.pk:
            original = Store.objects.filter(pk=self.pk).first()
            if original and original.tenant_type != self.tenant_type:
                if self._has_existing_orders():
                    raise ValidationError(
                        "tenant_type cannot be changed after orders exist"
                    )
        super().save(*args, **kwargs)

    def _has_existing_orders(self) -> bool:
        """Return True if this store has any orders across all commerce verticals."""
        from django.apps import apps

        # Restaurant vertical — DineInOrder (Epic 3)
        if apps.is_installed("apps.restaurant"):
            DineInOrder = apps.get_model("restaurant", "DineInOrder")
            if DineInOrder and DineInOrder.objects.filter(store=self).exists():
                return True

        # Retail vertical — Order (Epic 4)
        if apps.is_installed("apps.order"):
            Order = apps.get_model("order", "Order")
            if Order and Order.objects.filter(store=self).exists():
                return True

        return False


class StoreSettings(TenantModel):
    """
    Per-store configuration settings.

    Story 1.7 adds: tagline, logo_url.
    Story 4.1 adds: low_stock_threshold.
    Story 6.1 adds: tax_rate, tax_inclusive, currency_symbol, receipt_header, receipt_footer.
    """

    tagline = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Short store tagline shown on the storefront.",
    )
    logo_url = models.URLField(
        blank=True,
        default="",
        help_text="Absolute URL to the store's WebP logo.",
    )
    low_stock_threshold = models.IntegerField(
        default=5,
        help_text="Variant inventory_count at or below which a low-stock alert fires.",
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0.1600,
        help_text="Tax rate as decimal (e.g., 0.1600 for 16% VAT).",
    )
    tax_inclusive = models.BooleanField(
        default=True,
        help_text="If True, prices include tax. If False, tax is added on top.",
    )
    currency_symbol = models.CharField(
        max_length=10,
        default="KES",
        help_text="Currency symbol displayed in the admin and storefront.",
    )
    receipt_header = models.TextField(
        blank=True,
        default="",
        help_text="Text shown at the top of receipts.",
    )
    receipt_footer = models.TextField(
        blank=True,
        default="",
        help_text="Text shown at the bottom of receipts.",
    )

    class Meta:
        db_table = "store_storesettings"

    def __str__(self):
        return f"Settings for {self.store}"


class StoreTheme(TenantModel):
    """
    Per-store branding theme — Phase 1-3 design token system.

    Every field has a sensible default so stores work out of the box.
    Presets (Modern, Classic, Minimal, Bold, Vibrant) batch-set all tokens.
    """

    # ── Preset tracking ──────────────────────────────────────────────
    preset_slug = models.CharField(
        max_length=30, default="modern",
        help_text="Slug of the last-applied preset (modern|classic|minimal|bold|vibrant).",
    )
    template_style = models.CharField(
        max_length=30, default="modern",
        help_text="Layout variant key (modern|classic|minimal|bold).",
    )

    # ── Colour palette ───────────────────────────────────────────────
    primary_color = models.CharField(max_length=20, default="#1a1a1a",
        validators=[validate_css_color],
        help_text="Brand primary — nav bg, buttons, links.")
    secondary_color = models.CharField(max_length=20, default="#6b7280",
        validators=[validate_css_color],
        help_text="Brand secondary — muted accents, borders.")
    accent_color = models.CharField(max_length=20, default="#e63946",
        validators=[validate_css_color],
        help_text="Highlights, CTAs, sale badges.")
    background_color = models.CharField(max_length=20, default="#ffffff",
        validators=[validate_css_color],
        help_text="Page background.")
    surface_color = models.CharField(max_length=20, default="#f9fafb",
        validators=[validate_css_color],
        help_text="Card / section background.")
    text_primary_color = models.CharField(max_length=20, default="#111827",
        validators=[validate_css_color],
        help_text="Primary text colour.")
    text_secondary_color = models.CharField(max_length=20, default="#6b7280",
        validators=[validate_css_color],
        help_text="Secondary / muted text colour.")
    success_color = models.CharField(max_length=20, default="#16a34a",
        validators=[validate_css_color],
        help_text="Success / in-stock indicator.")
    error_color = models.CharField(max_length=20, default="#dc2626",
        validators=[validate_css_color],
        help_text="Error / out-of-stock indicator.")
    warning_color = models.CharField(max_length=20, default="#f59e0b",
        validators=[validate_css_color],
        help_text="Warning / low-stock indicator.")
    header_background = models.CharField(max_length=20, default="#1a1a1a",
        validators=[validate_css_color],
        help_text="Header bar background.")
    header_text_color = models.CharField(max_length=20, default="#ffffff",
        validators=[validate_css_color],
        help_text="Header text / link colour.")
    footer_background = models.CharField(max_length=20, default="#1f2937",
        validators=[validate_css_color])
    footer_text_color = models.CharField(max_length=20, default="#f3f4f6",
        validators=[validate_css_color])

    # ── Typography ───────────────────────────────────────────────────
    font_family_heading = models.CharField(max_length=100, default="Inter",
        help_text="Heading font family.")
    font_family_body = models.CharField(max_length=100, default="Inter",
        help_text="Body font family.")
    font_size_base = models.CharField(max_length=10, default="1rem",
        help_text="Base font size (e.g. 1rem, 16px).")
    font_size_scale = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal("1.250"),
        help_text="Heading scale factor (1.250 = Major Third).",
    )

    # ── Spacing ──────────────────────────────────────────────────────
    section_padding_y = models.CharField(max_length=10, default="4rem",
        help_text="Vertical section padding (e.g. 4rem, 64px).")
    card_padding = models.CharField(max_length=10, default="1.5rem",
        help_text="Inner card padding.")
    container_max_width = models.CharField(max_length=10, default="1280px",
        help_text="Max page width.")

    # ── Border radius ────────────────────────────────────────────────
    radius_sm = models.CharField(max_length=10, default="0.25rem")
    radius_md = models.CharField(max_length=10, default="0.5rem")
    radius_lg = models.CharField(max_length=10, default="0.75rem")
    radius_full = models.CharField(max_length=10, default="9999px")

    # ── Shadows ──────────────────────────────────────────────────────
    shadow_sm = models.CharField(max_length=50, default="0 1px 2px 0 rgb(0 0 0 / 0.05)")
    shadow_md = models.CharField(max_length=50, default="0 4px 6px -1px rgb(0 0 0 / 0.1)")
    shadow_lg = models.CharField(max_length=50, default="0 10px 15px -3px rgb(0 0 0 / 0.1)")

    # ── Announcement bar (Phase 3) ───────────────────────────────────
    announcement_enabled = models.BooleanField(default=False)
    announcement_text = models.CharField(max_length=500, blank=True, default="")

    # ── Custom CSS (Phase 3) ─────────────────────────────────────────
    custom_css = models.TextField(blank=True, default="",
        help_text="Raw CSS injected via <style> tag. Overrides any token above.")

    class Meta:
        db_table = "store_storetheme"

    def __str__(self):
        return f"Theme for {self.store}"
