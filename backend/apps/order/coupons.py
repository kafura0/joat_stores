"""
Coupon / discount code model.

Story 4.5 — Percentage or fixed-amount coupons with per-store scoping,
usage limits, date windows, and optional product/category restrictions.
"""

import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from core.models import TenantModel


class Coupon(TenantModel):
    """
    A coupon code that can be applied at checkout for a percentage or
    fixed-amount discount.
    """

    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage off"
        FIXED = "fixed", "Fixed amount off (KES)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=50,
        help_text="Customer-facing code (case-insensitive).",
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Internal note — not shown to customers.",
    )
    discount_type = models.CharField(
        max_length=10,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE,
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Percentage (0–100) or fixed amount in KES.",
    )
    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Minimum cart subtotal to qualify. 0 = no minimum.",
    )
    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Cap for percentage discounts. Null = uncapped.",
    )
    max_uses = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total redemption limit. Null = unlimited.",
    )
    times_used = models.PositiveIntegerField(default=0)
    max_uses_per_customer = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Per-customer redemption limit. Null = unlimited.",
    )
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Null = no expiry.",
    )
    is_active = models.BooleanField(default=True)
    applicable_products = models.ManyToManyField(
        "product.Product",
        blank=True,
        related_name="coupons",
        help_text="Restrict to specific products. Empty = all products.",
    )
    applicable_categories = models.ManyToManyField(
        "product.Category",
        blank=True,
        related_name="coupons",
        help_text="Restrict to specific categories. Empty = all categories.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["store", "code"],
                name="uq_coupon_store_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} ({self.get_discount_type_display()})"

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    @property
    def is_valid(self) -> bool:
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_from > now:
            return False
        if self.valid_to is not None and self.valid_to < now:
            return False
        if self.max_uses is not None and self.times_used >= self.max_uses:
            return False
        return True

    def calculate_discount(self, subtotal):
        """Return the discount amount for a given cart subtotal (Decimal)."""
        from decimal import Decimal

        if not self.is_valid:
            return Decimal("0")
        if subtotal < self.min_order_amount:
            return Decimal("0")

        if self.discount_type == self.DiscountType.FIXED:
            discount = min(self.discount_value, subtotal)
        else:
            # Percentage
            discount = (subtotal * self.discount_value / Decimal("100")).quantize(
                Decimal("0.01")
            )
            if self.max_discount_amount is not None:
                discount = min(discount, self.max_discount_amount)

        return discount

    def record_use(self):
        """Increment times_used atomically."""
        Coupon.objects.filter(pk=self.pk).update(
            times_used=models.F("times_used") + 1
        )
