"""
Bar domain models.

Story 5.1: Tab, InvalidTabTransition
Story 5.2: TabRound, TabItem (item removal audit trail)
Story 5.3: AgeRestrictionLog (MenuItem.is_age_restricted added via migration)
Story 5.4: HappyHour (price snapshot at add-time)
Story 5.5: TabShare (split-bill settlement via M-Pesa)

All models inherit TenantModel (UUID PK, store FK, soft-delete, TenantQuerySet).
Bar requires apps.restaurant to be installed (MenuItem FK dependency).
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from core.models import TenantModel


# ---------------------------------------------------------------------------
# Story 5.1 — Tab state machine
# ---------------------------------------------------------------------------


class InvalidTabTransition(Exception):
    """Raised when a Tab state transition is not allowed."""

    def __init__(self, current: str, attempted: str) -> None:
        self.current = current
        self.attempted = attempted
        super().__init__(
            f"Cannot transition Tab from {current!r} to {attempted!r}."
        )


class Tab(TenantModel):
    """
    Customer bar tab — created when a customer or staff opens a tab.

    State machine (enforced via .transition() — never direct field assignment):
        OPEN → BILL_REQUESTED → SETTLED

    Lifecycle:
      OPEN          — tab is active; rounds can be added
      BILL_REQUESTED — customer has asked for the bill; split payment initiated
      SETTLED        — all payments confirmed; tab is closed
    """

    STATUS_OPEN = "OPEN"
    STATUS_BILL_REQUESTED = "BILL_REQUESTED"
    STATUS_SETTLED = "SETTLED"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_BILL_REQUESTED, "Bill Requested"),
        (STATUS_SETTLED, "Settled"),
    ]

    VALID_TRANSITIONS: dict[str, list[str]] = {
        STATUS_OPEN: [STATUS_BILL_REQUESTED],
        STATUS_BILL_REQUESTED: [STATUS_SETTLED],
        STATUS_SETTLED: [],
    }

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="bar_tabs",
        help_text="Authenticated customer who opened the tab. Null for walk-in tabs.",
    )
    customer_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Display name for walk-in customers.",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
        db_index=True,
    )
    opened_at = models.DateTimeField(auto_now_add=True)
    settled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-opened_at"]
        indexes = [
            models.Index(
                fields=["store", "status"],
                name="idx_bar_tab_store_status",
            ),
        ]

    def __str__(self) -> str:
        name = self.customer_name or (self.customer and str(self.customer)) or "Walk-in"
        return f"Tab({self.id}, {name}, status={self.status})"

    def transition(self, new_status: str) -> None:
        """
        Enforce the state machine. Never assign self.status directly.

        Raises InvalidTabTransition if the transition is not allowed.
        """
        allowed = self.VALID_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise InvalidTabTransition(self.status, new_status)

        self.status = new_status
        update_fields = ["status"]

        if new_status == self.STATUS_SETTLED:
            self.settled_at = timezone.now()
            update_fields.append("settled_at")

        self.save(update_fields=update_fields)

    @property
    def total_amount(self) -> Decimal:
        """Sum of all active (non-removed) TabItem unit_price × quantity."""
        return sum(
            item.unit_price * item.quantity
            for item in self.items.filter(removed_at__isnull=True)
        )


# ---------------------------------------------------------------------------
# Story 5.2 — TabRound + TabItem (with removal audit)
# ---------------------------------------------------------------------------


class TabRound(TenantModel):
    """
    Groups a set of items ordered together in a single round.
    Rounds allow customers to see their order history grouped by when they ordered.
    """

    tab = models.ForeignKey(
        Tab,
        on_delete=models.CASCADE,
        related_name="rounds",
    )
    round_number = models.PositiveSmallIntegerField(
        help_text="Sequential round number within the tab (1-indexed).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["round_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["tab", "round_number"],
                name="uq_bar_tabround_number",
            )
        ]

    def __str__(self) -> str:
        return f"Round {self.round_number} on Tab {self.tab_id}"


class TabItem(TenantModel):
    """
    Single item line on a bar tab.

    unit_price is snapshotted at add-time (including happy hour discount).
    Removal creates an audit trail: removed_at, removed_by_id, removed_by_name.
    """

    tab = models.ForeignKey(
        Tab,
        on_delete=models.CASCADE,
        related_name="items",
    )
    round = models.ForeignKey(
        TabRound,
        on_delete=models.CASCADE,
        related_name="items",
    )
    menu_item = models.ForeignKey(
        "restaurant.MenuItem",
        on_delete=models.PROTECT,
        related_name="tab_items",
    )
    # Denormalized at creation time — immune to menu edits
    name = models.CharField(max_length=150)
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Price snapshotted at add-time (may include happy hour discount).",
    )
    quantity = models.PositiveSmallIntegerField(default=1)
    is_happy_hour = models.BooleanField(
        default=False,
        help_text="True if the happy hour discount was applied to unit_price.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Removal audit trail (Story 5.2)
    removed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Timestamp of removal by staff. Null = item is still on tab.",
    )
    removed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Staff member who removed this item.",
    )
    removed_by_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Denormalized staff name at time of removal.",
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["tab", "removed_at"],
                name="idx_bar_tabitem_tab_removed",
            ),
        ]

    def __str__(self) -> str:
        removed = " [REMOVED]" if self.removed_at else ""
        return f"TabItem({self.name} × {self.quantity} @ {self.unit_price}){removed}"


# ---------------------------------------------------------------------------
# Story 5.3 — AgeRestrictionLog
# (MenuItem.is_age_restricted added via bar migration on restaurant.MenuItem)
# ---------------------------------------------------------------------------


class AgeRestrictionLog(TenantModel):
    """
    Records that a customer acknowledged the age restriction prompt for their tab.

    One log per (customer / tab) is sufficient — second age-restricted item
    on the same tab skips the prompt (existing log covers the session).

    For anonymous walk-ins, customer_phone is used instead of a User FK.
    """

    tab = models.ForeignKey(
        Tab,
        on_delete=models.CASCADE,
        related_name="age_restriction_logs",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    customer_phone = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Used when customer is not authenticated.",
    )
    acknowledged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-acknowledged_at"]
        indexes = [
            models.Index(
                fields=["tab", "customer"],
                name="bar_agelog_tab_customer",
            ),
        ]

    def __str__(self) -> str:
        who = str(self.customer_id or self.customer_phone)
        return f"AgeRestrictionLog(tab={self.tab_id}, who={who})"


# ---------------------------------------------------------------------------
# Story 5.4 — HappyHour
# ---------------------------------------------------------------------------


class HappyHour(TenantModel):
    """
    A time window during which a discount applies to all bar items.

    Configured by store manager. When active, TabItem.unit_price is snapshotted
    with the discounted price — never recalculated at settlement.

    days_of_week: JSON list of ISO weekday ints (0=Monday … 6=Sunday).
    discount_percent: 0–100 (e.g. 20 = 20% off).
    """

    name = models.CharField(max_length=100, help_text="E.g. 'Evening Happy Hour'")
    start_time = models.TimeField(help_text="Start of happy hour window.")
    end_time = models.TimeField(help_text="End of happy hour window.")
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0")),
            MaxValueValidator(Decimal("100")),
        ],
        help_text="Discount percentage applied to all items during this window.",
    )
    days_of_week = models.JSONField(
        default=list,
        help_text="ISO weekday list: 0=Monday … 6=Sunday. Empty = every day.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["start_time"]
        indexes = [
            models.Index(
                fields=["store", "is_active"],
                name="idx_bar_happyhour_store_active",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.start_time}–{self.end_time}, {self.discount_percent}% off)"

    def is_active_now(self, current_dt=None) -> bool:
        """Return True if this happy hour window is currently active."""
        if not self.is_active:
            return False
        if current_dt is None:
            current_dt = timezone.localtime()
        current_time = current_dt.time()
        current_weekday = current_dt.weekday()  # 0=Monday

        if self.days_of_week and current_weekday not in self.days_of_week:
            return False
        return self.start_time <= current_time <= self.end_time

    def apply_discount(self, price: Decimal) -> Decimal:
        """Return price with the happy hour discount applied, rounded to 2dp."""
        factor = 1 - (self.discount_percent / Decimal("100"))
        return (price * factor).quantize(Decimal("0.01"))


def get_active_happy_hour(store) -> "HappyHour | None":
    """Return the first active HappyHour for the store right now, or None."""
    now = timezone.localtime()
    for hh in HappyHour.objects.filter(store=store, is_active=True):
        if hh.is_active_now(now):
            return hh
    return None


# ---------------------------------------------------------------------------
# Story 5.5 — TabShare (split-bill settlement via M-Pesa)
# ---------------------------------------------------------------------------


class TabShare(TenantModel):
    """
    One payer's share of a split bar tab bill.

    payment_reference: f"tab-share-{share.id}" — correlates M-Pesa webhook.

    When all TabShares for a tab reach PAID status, the tab auto-transitions
    to SETTLED via the payment_confirmed signal handler in bar/apps.py.

    For single-payer tabs, one TabShare covers the full amount.
    """

    STATUS_PENDING = "PENDING"
    STATUS_PAID = "PAID"
    STATUS_FAILED = "FAILED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_FAILED, "Failed / timed out"),
    ]

    tab = models.ForeignKey(
        Tab,
        on_delete=models.CASCADE,
        related_name="shares",
    )
    payer_phone = models.CharField(max_length=20)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    # Item IDs this payer is responsible for (subset of tab items)
    item_ids = models.JSONField(
        default=list,
        help_text="TabItem UUIDs covered by this share. Empty = percentage-based share.",
    )
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Percentage of total bill (used when item_ids is empty).",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    payment_transaction = models.ForeignKey(
        "payment.MpesaTransaction",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tab_shares",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["store", "tab", "status"],
                name="idx_bar_tabshare_tab_status",
            ),
        ]

    def __str__(self) -> str:
        return f"TabShare({self.id}, tab={self.tab_id}, phone={self.payer_phone}, amount={self.amount}, status={self.status})"
