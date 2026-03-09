"""
SaaS subscription models — stubs for Story 1.4.

Plan:
  - api_rate_limit: requests per minute per store (default 100)
  - Full fields added in Epic 9 (billing cycle, price tiers, feature flags)

StoreSubscription:
  - OneToOne to Store — every store gets one on provisioning
  - status: trial (default) — full lifecycle in Epic 9
  - plan FK (nullable) — null means default/free tier

Access pattern: request.store.subscription.plan.api_rate_limit
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Plan(models.Model):
    """
    Subscription plan stub.

    Epic 9 adds: name, price, billing_cycle, feature_flags, max_products,
    max_orders_per_month, etc.
    """

    name = models.CharField(max_length=100, default="Free Trial")
    api_rate_limit = models.IntegerField(
        default=100,
        help_text="Max API requests per minute per store.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "saas_plan"

    def __str__(self):
        return self.name


class SubscriptionStatus(models.TextChoices):
    TRIAL = "trial", _("Trial")
    ACTIVE = "active", _("Active")
    PAST_DUE = "past_due", _("Past Due")
    SUSPENDED = "suspended", _("Suspended")
    CANCELLED = "cancelled", _("Cancelled")


class StoreSubscription(models.Model):
    """
    Store subscription stub — links a Store to a Plan.

    Created atomically during store provisioning (Story 1.4).
    Full lifecycle (trial→active→past_due→suspended→cancelled) in Epic 9.
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
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "saas_storesubscription"

    def __str__(self):
        return f"{self.store.name} — {self.status}"
