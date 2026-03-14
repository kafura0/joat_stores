"""
SaaS app config — Epic 9.

Connects payment_confirmed signal to handle subscription renewal payments.
Reference format: "subscription-{store_id}"
"""

import structlog
from django.apps import AppConfig

log = structlog.get_logger(__name__)


class SaasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.saas"

    def ready(self):
        from apps.payment.signals import payment_confirmed
        payment_confirmed.connect(_handle_subscription_payment_confirmed)


def _handle_subscription_payment_confirmed(sender, transaction, **kwargs):
    """
    Story 9.3 — When M-Pesa confirms a subscription renewal payment,
    activate the subscription and extend the billing period by one month.

    Reference format: "subscription-{store_id}"
    """
    ref = getattr(transaction, "reference", "")
    if not ref.startswith("subscription-"):
        return

    store_id = ref[len("subscription-"):]
    try:
        from datetime import timedelta
        from django.utils import timezone

        from apps.saas.models import StoreSubscription, SubscriptionStatus

        sub = StoreSubscription.objects.select_related("plan").get(store_id=store_id)

        today = timezone.localdate()

        # Extend period: if currently active, extend from period_end; otherwise start from today
        if sub.status == SubscriptionStatus.ACTIVE and sub.period_end and sub.period_end >= today:
            new_period_start = sub.period_end + timedelta(days=1)
        else:
            new_period_start = today

        # Monthly billing = 30 days; annual = 365 days
        billing_days = 365 if (sub.plan and sub.plan.billing_cycle == "annual") else 30
        new_period_end = new_period_start + timedelta(days=billing_days)

        sub.period_start = new_period_start
        sub.period_end = new_period_end
        sub.current_payment_transaction = transaction
        update_fields = ["period_start", "period_end", "current_payment_transaction", "updated_at"]

        # Transition to ACTIVE if not already
        if sub.status != SubscriptionStatus.ACTIVE:
            sub.past_due_since = None
            sub.status = SubscriptionStatus.ACTIVE
            update_fields += ["status", "past_due_since"]

        sub.save(update_fields=update_fields)

        log.info(
            "subscription_renewal_confirmed",
            store_id=store_id,
            period_end=str(new_period_end),
        )
    except StoreSubscription.DoesNotExist:
        log.warning("subscription_not_found_for_renewal", store_id=store_id)
    except Exception as exc:
        log.error("subscription_renewal_signal_error", store_id=store_id, error=str(exc))
