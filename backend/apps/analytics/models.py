"""
Analytics models.

Story 1.6: AdminPIIAccessLog — append-only PII audit log
Story 8.1: DailyRevenueSummary, HourlyOrderSummary (pre-aggregated, never live queries)
Story 8.2: AIEvent (append-only event stream for AI/recommendation engine)
Story 8.6: TenantHealthSnapshot (platform-level per-tenant daily health)
Story 8.7: StoreFirstOrderEvent (first-order milestone for investor demo)
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Story 1.6 — AdminPIIAccessLog (unchanged)
# ---------------------------------------------------------------------------


class AdminPIIAccessLog(models.Model):
    """
    Append-only audit log for admin access to customer PII.

    Kenya DPA 2019 requires a full audit trail of all PII access.
    The DB role should have INSERT-only privileges on this table
    (enforced in Story 12.3).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    store = models.ForeignKey(
        "store.Store",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    record_type = models.CharField(max_length=100)
    record_id = models.CharField(max_length=255)
    accessed_at = models.DateTimeField(default=timezone.now, db_index=True)
    path = models.CharField(max_length=500, blank=True, default="")
    method = models.CharField(max_length=10, blank=True, default="")

    class Meta:
        db_table = "analytics_adminpiiaccesslog"
        ordering = ["-accessed_at"]
        indexes = [
            models.Index(fields=["user", "accessed_at"]),
            models.Index(fields=["store", "accessed_at"]),
        ]

    def __str__(self):
        return f"PII access: {self.user} -> {self.record_type}#{self.record_id} at {self.accessed_at}"


# ---------------------------------------------------------------------------
# Story 8.1 — Pre-aggregated summary models
# ---------------------------------------------------------------------------


class DailyRevenueSummary(models.Model):
    """
    Pre-aggregated daily revenue per store.

    Populated by generate_daily_summary Celery task at 00:05.
    Analytics endpoints MUST read from this model — never from live Order tables.

    amount_usd: USD-normalized for cross-tenant GMV aggregation.
    aov: average order value = total_revenue / order_count (null if order_count=0).
    top_products: JSON list of {product_id, name, revenue} — top 5 by revenue.
    """

    store = models.ForeignKey("store.Store", on_delete=models.CASCADE, related_name="+")
    date = models.DateField(db_index=True)
    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    order_count = models.PositiveIntegerField(default=0)
    aov = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text="Average order value. Null when order_count=0.",
    )
    amount_usd = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0"),
        help_text="USD-normalized revenue for cross-tenant GMV. 1 KES ≈ 0.0078 USD.",
    )
    top_products = models.JSONField(
        default=list,
        help_text="Top 5 products by revenue: [{product_id, name, revenue}]",
    )

    class Meta:
        unique_together = [("store", "date")]
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["store", "date"], name="idx_analytics_drs_store_date"),
        ]

    def __str__(self):
        return f"DailyRevenue(store={self.store_id}, date={self.date}, revenue={self.total_revenue})"


class HourlyOrderSummary(models.Model):
    """
    Pre-aggregated hourly order counts per store per day.

    Populated alongside DailyRevenueSummary. Used for peak-hour analysis (Story 8.4).
    hour: 0–23 (local time).
    """

    store = models.ForeignKey("store.Store", on_delete=models.CASCADE, related_name="+")
    date = models.DateField(db_index=True)
    hour = models.PositiveSmallIntegerField(help_text="Hour of day (0–23) in store's local time.")
    order_count = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))

    class Meta:
        unique_together = [("store", "date", "hour")]
        ordering = ["date", "hour"]
        indexes = [
            models.Index(
                fields=["store", "date"], name="idx_analytics_hos_store_date"
            ),
        ]

    def __str__(self):
        return f"HourlyOrder(store={self.store_id}, date={self.date}, hour={self.hour:02d}:00)"


# ---------------------------------------------------------------------------
# Story 8.2 — AIEvent (append-only)
# ---------------------------------------------------------------------------


class AIEvent(models.Model):
    """
    Append-only event log for the AI recommendation engine.

    Captures: product_view, cart_add, cart_remove, search, order_complete.
    Never updated or deleted — enforced via save() override.

    Dispatch pattern: post_save signal + transaction.on_commit + Celery task
    so event capture never runs inside the primary business transaction.
    """

    EVENT_PRODUCT_VIEW = "product_view"
    EVENT_CART_ADD = "cart_add"
    EVENT_CART_REMOVE = "cart_remove"
    EVENT_SEARCH = "search"
    EVENT_ORDER_COMPLETE = "order_complete"

    EVENT_TYPE_CHOICES = [
        (EVENT_PRODUCT_VIEW, "Product View"),
        (EVENT_CART_ADD, "Cart Add"),
        (EVENT_CART_REMOVE, "Cart Remove"),
        (EVENT_SEARCH, "Search"),
        (EVENT_ORDER_COMPLETE, "Order Complete"),
    ]

    store = models.ForeignKey("store.Store", on_delete=models.CASCADE, related_name="+")
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES, db_index=True)
    entity_id = models.CharField(
        max_length=255, blank=True, default="",
        help_text="ID of the product, search query, or order.",
    )
    metadata = models.JSONField(default=dict)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["store", "event_type", "occurred_at"], name="idx_analytics_aievent_store_type"),
        ]

    def save(self, *args, **kwargs):
        """Enforce append-only — reject updates to existing records."""
        if self.pk:
            raise ValueError("AIEvent is append-only. Updates are not permitted.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"AIEvent({self.event_type}, store={self.store_id}, entity={self.entity_id})"


# ---------------------------------------------------------------------------
# Story 8.6 — TenantHealthSnapshot
# ---------------------------------------------------------------------------


class TenantHealthSnapshot(models.Model):
    """
    Daily per-tenant health snapshot for platform admin dashboard.

    Populated by generate_daily_summary at 00:05. Provides the
    cross-tenant view for investor demos and platform monitoring.
    """

    store = models.ForeignKey("store.Store", on_delete=models.CASCADE, related_name="+")
    date = models.DateField(db_index=True)
    gmv = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    gmv_usd = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    order_count = models.PositiveIntegerField(default=0)
    subscription_status = models.CharField(max_length=30, blank=True, default="")
    is_healthy = models.BooleanField(
        default=True,
        help_text="False if subscription is past_due or suspended.",
    )

    class Meta:
        unique_together = [("store", "date")]
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["date", "is_healthy"], name="idx_analytics_ths_date_health"),
        ]

    def __str__(self):
        return f"TenantHealth(store={self.store_id}, date={self.date}, healthy={self.is_healthy})"


# ---------------------------------------------------------------------------
# Story 8.7 — StoreFirstOrderEvent (investor demo milestone)
# ---------------------------------------------------------------------------


class StoreFirstOrderEvent(models.Model):
    """
    Records the moment a store receives its very first confirmed order.

    Created exactly once per store via transaction.on_commit + Celery task.
    Never duplicated even on retry (idempotent: get_or_create).
    Permanent — never deleted.

    Surfaced in platform admin dashboard as a celebration milestone.
    """

    store = models.OneToOneField(
        "store.Store",
        on_delete=models.CASCADE,
        related_name="first_order_event",
    )
    order = models.ForeignKey(
        "order.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    first_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["occurred_at"]
        indexes = [
            models.Index(fields=["occurred_at"], name="idx_analytics_firstorder_at"),
        ]

    def __str__(self):
        return f"FirstOrder(store={self.store_id}, at={self.occurred_at})"
