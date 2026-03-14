"""
Product catalog models — Story 4.1.

Category → Product → Variant (per-combination inventory) + ProductImage.

Design notes:
- Variants store attribute_values as JSON ({"Size": "M", "Colour": "Red"}) — no
  separate AttributeValue table; simpler and sufficient for MVP read patterns.
- ProductAttribute holds the attribute *names* per product (derived from the
  union of variant keys, but stored on Product for O(1) read on product detail).
- Low-stock alert fires via transaction.on_commit when inventory_count is saved
  at or below the store's configured threshold.
- Images are stored as WebP after Pillow compression in the upload view.
"""

import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from core.models import TenantModel

# Default low-stock threshold when StoreSettings doesn't override
DEFAULT_LOW_STOCK_THRESHOLD = 5


class Category(TenantModel):
    """
    Product category — hierarchical (self-referential parent FK).
    Retail stores may have: Electronics > Phones > Android.
    """

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    position = models.IntegerField(default=0)

    class Meta:
        ordering = ["position", "name"]
        indexes = [
            models.Index(fields=["store", "parent"], name="idx_product_category_parent"),
        ]

    def __str__(self):
        return self.name


class Product(TenantModel):
    """
    A sellable product.  Price lives on Variant — Product has no base price.
    attribute_names is a JSON list of attribute dimension names that apply to
    this product (e.g. ["Size", "Colour"]), derived from variant keys.
    """

    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="products",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    # Attribute dimension names, e.g. ["Size", "Colour"]
    attribute_names = models.JSONField(default=list)
    is_available = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["store", "is_available"], name="idx_product_store_available"),
            models.Index(fields=["store", "category"], name="idx_product_store_category"),
        ]

    def __str__(self):
        return self.name


class Variant(TenantModel):
    """
    A specific combination of attribute values for a product.

    attribute_values: {"Size": "M", "Colour": "Red"}
    inventory_count: tracked per variant independently.

    On save: if inventory_count <= threshold, dispatch low-stock alert task
    via transaction.on_commit (never blocks the request).
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    attribute_values = models.JSONField(default=dict)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    inventory_count = models.IntegerField(default=0)
    is_available = models.BooleanField(default=True)
    sku = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["store", "product"], name="idx_variant_store_product"),
            models.Index(fields=["store", "is_available"], name="idx_variant_available"),
        ]

    def __str__(self):
        return f"{self.product.name} {self.attribute_values}"

    def save(self, *args, **kwargs):
        """Dispatch low-stock alert when inventory drops to/below threshold."""
        super().save(*args, **kwargs)
        from django.db import transaction as db_tx

        variant_id = str(self.id)
        threshold = self._get_low_stock_threshold()
        if self.inventory_count <= threshold:
            db_tx.on_commit(
                lambda: _dispatch_low_stock_alert(variant_id)
            )

    def _get_low_stock_threshold(self) -> int:
        """
        Return the low-stock threshold from StoreSettings if configured,
        otherwise fall back to the module default.
        """
        try:
            from apps.store.models import StoreSettings

            settings = StoreSettings.objects.get(store_id=self.store_id)
            return getattr(settings, "low_stock_threshold", DEFAULT_LOW_STOCK_THRESHOLD)
        except Exception:
            return DEFAULT_LOW_STOCK_THRESHOLD


def _dispatch_low_stock_alert(variant_id: str) -> None:
    """Called via on_commit — import lazily to avoid startup circular imports."""
    try:
        from apps.product.tasks import send_low_stock_alert

        send_low_stock_alert.apply_async(args=[variant_id], queue="inventory.alerts")
    except Exception:
        pass  # Never let a task dispatch failure break the save path


class ProductImage(TenantModel):
    """
    A WebP image associated with a product (or a specific variant).

    When variant is set, the image belongs to that variant's gallery.
    When variant is None, it is a product-level default image.
    After upload, the view compresses to WebP ≤ 800KB and removes the original.
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    variant = models.ForeignKey(
        Variant,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="images",
    )
    image = models.ImageField(upload_to="products/images/")
    alt_text = models.CharField(max_length=255, blank=True, default="")
    position = models.IntegerField(default=0)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["position", "id"]
        indexes = [
            models.Index(fields=["store", "product"], name="idx_productimage_product"),
        ]

    def __str__(self):
        return f"Image for {self.product.name} (variant={self.variant_id})"
