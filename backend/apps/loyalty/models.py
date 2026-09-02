"""
Loyalty models — Epic 10.

Story 10.1: LoyaltyAccount + PointsTransaction (earn/redeem/expire)
Story 10.2: StampCard + CustomerStampCard + CustomerStamp (auto-reward)
Story 10.4: CustomerProfile — unified guest/auth customer record
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import TenantModel


# ---------------------------------------------------------------------------
# 10.1 — Loyalty points
# ---------------------------------------------------------------------------


class LoyaltyAccount(TenantModel):
    """
    Per-customer loyalty account scoped to a store.

    Points are earned on confirmed orders (1 point per configurable KES amount).
    Redeemed via POST /api/v1/loyalty/redeem/ (deducted at checkout).
    """

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="loyalty_accounts",
        null=True,
        blank=True,
        help_text="Null for guest accounts — linked by customer_phone.",
    )
    customer_phone = models.CharField(max_length=30, db_index=True)
    points_balance = models.IntegerField(default=0)
    lifetime_earned = models.IntegerField(default=0)

    class Meta:
        unique_together = [("store", "customer_phone")]
        ordering = ["-lifetime_earned"]

    def __str__(self):
        return f"{self.customer_phone} @ {self.store.name}: {self.points_balance} pts"

    def earn(self, points: int, source: str, reference: str = "") -> "PointsTransaction":
        """Add points and record a PointsTransaction."""
        self.points_balance += points
        self.lifetime_earned += points
        self.save(update_fields=["points_balance", "lifetime_earned"])
        return PointsTransaction.objects.create(
            store=self.store,
            account=self,
            delta=points,
            balance_after=self.points_balance,
            source=source,
            reference=reference,
        )

    def redeem(self, points: int, reference: str = "") -> "PointsTransaction":
        """Deduct points and record a PointsTransaction. Raises ValueError if insufficient."""
        if self.points_balance < points:
            raise ValueError(
                f"Insufficient points: balance={self.points_balance}, requested={points}"
            )
        self.points_balance -= points
        self.save(update_fields=["points_balance"])
        return PointsTransaction.objects.create(
            store=self.store,
            account=self,
            delta=-points,
            balance_after=self.points_balance,
            source=PointsTransaction.SOURCE_REDEMPTION,
            reference=reference,
        )


class PointsTransaction(TenantModel):
    """Append-only ledger of all points movements."""

    SOURCE_ORDER = "order"
    SOURCE_REDEMPTION = "redemption"
    SOURCE_MANUAL = "manual"
    SOURCE_EXPIRY = "expiry"

    SOURCE_CHOICES = [
        (SOURCE_ORDER, _("Order")),
        (SOURCE_REDEMPTION, _("Redemption")),
        (SOURCE_MANUAL, _("Manual Adjustment")),
        (SOURCE_EXPIRY, _("Expiry")),
    ]

    account = models.ForeignKey(
        LoyaltyAccount,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    delta = models.IntegerField(help_text="Positive = earned, negative = redeemed/expired.")
    balance_after = models.IntegerField()
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, db_index=True)
    reference = models.CharField(max_length=255, blank=True, default="")
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-occurred_at"]

    def save(self, *args, **kwargs):
        if self.pk and self.__class__.objects.filter(pk=self.pk).exists():
            raise ValueError("PointsTransaction is append-only.")
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# 10.2 — Stamp cards
# ---------------------------------------------------------------------------


class StampCard(TenantModel):
    """
    A stamp-card loyalty programme for a store.

    Customers earn one stamp per qualifying order. When stamps_count reaches
    stamps_required, a reward is automatically issued.
    """

    name = models.CharField(max_length=100)
    stamps_required = models.PositiveIntegerField(default=10)
    reward_description = models.CharField(max_length=255)
    points_per_stamp = models.IntegerField(
        default=0,
        help_text="Bonus loyalty points awarded when the card is completed.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.stamps_required} stamps)"


class CustomerStampCard(TenantModel):
    """
    A customer's progress on a specific StampCard.

    stamps_count is incremented on each qualifying order.
    redeemed_count tracks how many times the threshold has been hit and reset.
    """

    stamp_card = models.ForeignKey(
        StampCard,
        on_delete=models.CASCADE,
        related_name="customer_cards",
    )
    customer_phone = models.CharField(max_length=30, db_index=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    stamps_count = models.PositiveIntegerField(default=0)
    redeemed_count = models.PositiveIntegerField(default=0)
    last_stamp_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("store", "stamp_card", "customer_phone")]
        ordering = ["-last_stamp_at"]

    def add_stamp(self, order_id: str) -> bool:
        """
        Add one stamp and create a CustomerStamp record.
        Returns True if the card threshold was just reached (reward triggered).
        """
        self.stamps_count += 1
        self.last_stamp_at = timezone.now()
        self.save(update_fields=["stamps_count", "last_stamp_at"])

        CustomerStamp.objects.create(
            store=self.store,
            customer_card=self,
            order_reference=order_id,
        )

        if self.stamps_count >= self.stamp_card.stamps_required:
            self.stamps_count = 0
            self.redeemed_count += 1
            self.save(update_fields=["stamps_count", "redeemed_count"])
            return True
        return False


class CustomerStamp(TenantModel):
    """One stamp earned on a CustomerStampCard."""

    customer_card = models.ForeignKey(
        CustomerStampCard,
        on_delete=models.CASCADE,
        related_name="stamps",
    )
    order_reference = models.CharField(max_length=255, blank=True, default="")
    earned_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-earned_at"]


# ---------------------------------------------------------------------------
# 10.4 — Unified customer profile
# ---------------------------------------------------------------------------


class CustomerProfile(TenantModel):
    """
    Unified customer profile — links guest phone → auth user → order history.

    Created on first order (guest) or first login (auth customer).
    Accumulates order_count + total_spent for RFM analysis.
    """

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_profiles",
    )
    customer_phone = models.CharField(max_length=30, db_index=True)
    customer_email = models.EmailField(blank=True, default="")
    customer_name = models.CharField(max_length=255, blank=True, default="")
    order_count = models.PositiveIntegerField(default=0)
    total_spent = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    first_order_at = models.DateTimeField(null=True, blank=True)
    last_order_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("store", "customer_phone")]
        ordering = ["-last_order_at"]

    def __str__(self):
        return f"{self.customer_phone} @ {self.store.name}"

    def record_order(self, amount: Decimal, ordered_at=None) -> None:
        """Update RFM metrics after a confirmed order."""
        now = ordered_at or timezone.now()
        self.order_count += 1
        self.total_spent += amount
        self.last_order_at = now
        if self.first_order_at is None:
            self.first_order_at = now
        self.save(update_fields=[
            "order_count", "total_spent", "last_order_at", "first_order_at"
        ])
