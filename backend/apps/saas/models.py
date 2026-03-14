"""
SaaS subscription models — Epic 9.

Story 9.1: Plan model — pricing tiers, feature flags, resource limits
Story 9.2: StoreSubscription lifecycle — state machine, period tracking
Story 9.3: M-Pesa renewal support (current_payment_transaction FK)
Story 9.7: Suspended/cancelled tracking for auto-suspension pipeline
"""

from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# ---------------------------------------------------------------------------
# 9.1 — Plan model
# ---------------------------------------------------------------------------


class BillingCycle(models.TextChoices):
    MONTHLY = "monthly", _("Monthly")
    ANNUAL = "annual", _("Annual")


class Plan(models.Model):
    """
    Subscription plan definition.

    slug          — machine-readable identifier (e.g. "free", "starter", "growth", "pro")
    price_kes     — monthly/annual price in Kenya Shillings
    billing_cycle — MONTHLY or ANNUAL
    trial_days    — how long the free trial lasts (default 14)

    Resource limits (null = unlimited):
    - max_products         — catalogue size cap
    - max_orders_per_month — order volume cap
    - max_staff            — number of staff accounts

    Feature flags:
    - has_analytics   — access to analytics dashboard
    - has_qr_codes    — QR code generation for tables
    - has_ai_features — AI recommendations / NLP search
    - has_whatsapp    — WhatsApp notification dispatch

    api_rate_limit — requests per minute per store (default 100)
    """

    slug = models.SlugField(unique=True, max_length=50)
    name = models.CharField(max_length=100)
    price_kes = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Plan price in Kenya Shillings (0 = free).",
    )
    billing_cycle = models.CharField(
        max_length=10,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY,
    )
    trial_days = models.PositiveIntegerField(default=14)

    # Resource limits (null = unlimited)
    max_products = models.PositiveIntegerField(
        null=True, blank=True, help_text="Max catalogue products (null = unlimited)."
    )
    max_orders_per_month = models.PositiveIntegerField(
        null=True, blank=True, help_text="Max orders per calendar month (null = unlimited)."
    )
    max_staff = models.PositiveIntegerField(
        null=True, blank=True, help_text="Max staff accounts (null = unlimited)."
    )

    # Feature flags
    has_analytics = models.BooleanField(default=False)
    has_qr_codes = models.BooleanField(default=True)
    has_ai_features = models.BooleanField(default=False)
    has_whatsapp = models.BooleanField(default=False)

    api_rate_limit = models.IntegerField(
        default=100,
        help_text="Max API requests per minute per store.",
    )
    is_public = models.BooleanField(
        default=True,
        help_text="Visible on the public pricing page.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "saas_plan"
        ordering = ["price_kes"]

    def __str__(self):
        return f"{self.name} ({self.get_billing_cycle_display()}, KES {self.price_kes})"


# ---------------------------------------------------------------------------
# 9.2 — StoreSubscription lifecycle
# ---------------------------------------------------------------------------


class SubscriptionStatus(models.TextChoices):
    TRIAL = "trial", _("Trial")
    ACTIVE = "active", _("Active")
    PAST_DUE = "past_due", _("Past Due")
    SUSPENDED = "suspended", _("Suspended")
    CANCELLED = "cancelled", _("Cancelled")


VALID_SUBSCRIPTION_TRANSITIONS = {
    SubscriptionStatus.TRIAL: [
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.CANCELLED,
    ],
    SubscriptionStatus.ACTIVE: [
        SubscriptionStatus.PAST_DUE,
        SubscriptionStatus.CANCELLED,
    ],
    SubscriptionStatus.PAST_DUE: [
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.SUSPENDED,
        SubscriptionStatus.CANCELLED,
    ],
    SubscriptionStatus.SUSPENDED: [
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.CANCELLED,
    ],
    SubscriptionStatus.CANCELLED: [],
}


class InvalidSubscriptionTransition(Exception):
    def __init__(self, from_status, to_status):
        super().__init__(
            f"Cannot transition subscription from {from_status!r} to {to_status!r}"
        )


class StoreSubscription(models.Model):
    """
    Store subscription — links a Store to a Plan with full lifecycle tracking.

    Created atomically during store provisioning (Story 1.4).
    Subscription period tracked via period_start / period_end DateFields.
    """

    store = models.OneToOneField(
        "store.Store",
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions",
    )
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.TRIAL,
        db_index=True,
    )

    # Period tracking
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True, db_index=True)
    trial_ends_at = models.DateField(null=True, blank=True)

    # Renewal payment (Story 9.3)
    current_payment_transaction = models.ForeignKey(
        "payment.MpesaTransaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    # Suspension / cancellation tracking (Story 9.7)
    past_due_since = models.DateField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "saas_storesubscription"

    def __str__(self):
        return f"{self.store.name} — {self.status}"

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def transition_status(self, new_status: str) -> None:
        """
        Transition to new_status following the allowed state machine.
        Raises InvalidSubscriptionTransition on illegal moves.
        Updates audit timestamps automatically.
        """
        allowed = VALID_SUBSCRIPTION_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise InvalidSubscriptionTransition(self.status, new_status)

        now = timezone.now()
        today = now.date()
        update_fields = ["status", "updated_at"]

        if new_status == SubscriptionStatus.PAST_DUE:
            self.past_due_since = today
            update_fields.append("past_due_since")
        elif new_status == SubscriptionStatus.SUSPENDED:
            self.suspended_at = now
            update_fields.append("suspended_at")
        elif new_status == SubscriptionStatus.CANCELLED:
            self.cancelled_at = now
            update_fields.append("cancelled_at")
        elif new_status == SubscriptionStatus.ACTIVE:
            # Clear past_due marker on reactivation
            self.past_due_since = None
            update_fields.append("past_due_since")

        self.status = new_status
        self.save(update_fields=update_fields)

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def is_expired(self) -> bool:
        """True when period_end is set and has passed."""
        if self.period_end is None:
            return False
        return self.period_end < timezone.localdate()

    @property
    def days_until_expiry(self) -> int | None:
        """Days remaining in current period; None if no period_end set."""
        if self.period_end is None:
            return None
        delta = self.period_end - timezone.localdate()
        return delta.days

    @property
    def renewal_amount_kes(self) -> Decimal:
        """Amount due for renewal (plan price, 0 if no plan)."""
        if self.plan is None:
            return Decimal("0.00")
        return self.plan.price_kes


# ---------------------------------------------------------------------------
# 9.4 — Plan limit helpers
# ---------------------------------------------------------------------------


class PlanLimitExceeded(Exception):
    """Raised when a store exceeds its plan resource limit."""

    def __init__(self, resource: str, limit: int):
        self.resource = resource
        self.limit = limit
        super().__init__(f"Plan limit exceeded: {resource} (limit={limit})")


def check_product_limit(store) -> None:
    """
    Raise PlanLimitExceeded if store is at or above max_products for its plan.
    Called before creating a new product.
    """
    try:
        sub = store.subscription
        plan = sub.plan
    except StoreSubscription.DoesNotExist:
        return  # No subscription = no limit enforced

    if plan is None or plan.max_products is None:
        return  # Unlimited

    from apps.product.models import Product

    current = Product.objects.filter(store=store).count()
    if current >= plan.max_products:
        raise PlanLimitExceeded("max_products", plan.max_products)


def check_monthly_order_limit(store) -> None:
    """
    Raise PlanLimitExceeded if store has reached its monthly order cap.
    Called before creating a new order.
    """
    try:
        sub = store.subscription
        plan = sub.plan
    except StoreSubscription.DoesNotExist:
        return

    if plan is None or plan.max_orders_per_month is None:
        return

    from apps.order.models import Order

    today = timezone.localdate()
    month_start = today.replace(day=1)
    current = Order.objects.filter(store=store, created_at__date__gte=month_start).count()
    if current >= plan.max_orders_per_month:
        raise PlanLimitExceeded("max_orders_per_month", plan.max_orders_per_month)
