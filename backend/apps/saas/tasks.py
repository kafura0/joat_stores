"""
SaaS / billing async tasks — Epic 9.

Story 7.2 (updated): send_subscription_renewal_reminder — scan + dispatch
Story 9.3: send_billing_reminder — single-store renewal STK Push
Story 9.7: suspend_past_due_subscriptions — auto-suspend after 7 days past_due
            anonymise_cancelled_store_pii — GDPR/DPA erasure 30 days after cancel

Queue: billing.reminders
DLQ pattern: max_retries=5, countdown=60 * (2 ** retries)
"""

from datetime import timedelta

import structlog
from celery import shared_task
from django.utils import timezone

from core.tasks import DLQTask

logger = structlog.get_logger(__name__)


@shared_task(
    bind=True,
    base=DLQTask,
    queue="billing.reminders",
    max_retries=5,
)
def send_billing_reminder(self, store_id: str) -> None:
    """
    Story 9.3 — Send a subscription renewal reminder for a specific store.

    Fetches the store's billing contact phone and initiates an M-Pesa STK Push
    for the renewal amount. The payment signal (apps.saas.apps) activates the
    subscription when M-Pesa confirms.
    """
    try:
        from apps.store.models import Store
        from apps.saas.models import StoreSubscription, SubscriptionStatus

        store = Store.objects.get(id=store_id)
        sub = StoreSubscription.objects.select_related("plan").get(store=store)

        # Skip if already active with time remaining
        if sub.status == SubscriptionStatus.ACTIVE and not sub.is_expired:
            logger.info("billing_reminder_skip_active", store_id=store_id)
            return

        if sub.renewal_amount_kes <= 0:
            logger.info("billing_reminder_skip_free", store_id=store_id)
            return

        # Use store owner's phone for STK (first staff member with role store_owner)
        from apps.users.models import User
        owner = User.objects.filter(store=store, role="store_owner").first()
        if not owner or not getattr(owner, "phone", None):
            logger.warning("billing_reminder_no_owner_phone", store_id=store_id)
            return

        from apps.payment.services import initiate_payment
        reference = f"subscription-{store.id}"
        tx = initiate_payment(
            store=store,
            method="mpesa",
            amount=sub.renewal_amount_kes,
            phone=owner.phone,
            reference=reference,
        )
        logger.info("billing_reminder_stk_sent", store_id=store_id, tx_id=str(tx.id))

    except Exception as exc:
        logger.exception("billing_reminder_error", store_id=store_id)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(
    bind=True,
    base=DLQTask,
    queue="billing.reminders",
    max_retries=3,
)
def send_subscription_renewal_reminder(self) -> None:
    """
    Story 7.2 / 9.3 — Scan subscriptions expiring in 3 days; dispatch
    send_billing_reminder per store.

    Scheduled: daily at 09:00 via Celery Beat.
    """
    try:
        from apps.saas.models import StoreSubscription, SubscriptionStatus

        target_date = timezone.localdate() + timedelta(days=3)
        logger.info("renewal_reminder_scan_start", target_date=str(target_date))

        expiring = StoreSubscription.objects.filter(
            period_end=target_date,
            status__in=[
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.TRIAL,
                SubscriptionStatus.PAST_DUE,
            ],
        ).values_list("store_id", flat=True)

        dispatched = 0
        for store_id in expiring:
            send_billing_reminder.delay(str(store_id))
            dispatched += 1

        logger.info("renewal_reminder_scan_complete", dispatched=dispatched)

    except Exception as exc:
        logger.exception("renewal_reminder_scan_failed")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(
    bind=True,
    base=DLQTask,
    queue="billing.reminders",
    max_retries=3,
)
def suspend_past_due_subscriptions(self) -> None:
    """
    Story 9.7 — Suspend stores that have been past_due for more than 7 days.

    Scheduled: daily at 01:00 via Celery Beat (added in 9.7 settings update).
    """
    try:
        from apps.saas.models import StoreSubscription, SubscriptionStatus, InvalidSubscriptionTransition

        cutoff = timezone.localdate() - timedelta(days=7)
        to_suspend = StoreSubscription.objects.filter(
            status=SubscriptionStatus.PAST_DUE,
            past_due_since__lte=cutoff,
        )

        suspended = 0
        for sub in to_suspend:
            try:
                sub.transition_status(SubscriptionStatus.SUSPENDED)
                suspended += 1
                logger.info("subscription_suspended", store_id=str(sub.store_id))
            except InvalidSubscriptionTransition:
                pass

        logger.info("suspend_past_due_complete", suspended=suspended)

    except Exception as exc:
        logger.exception("suspend_past_due_failed")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(
    bind=True,
    base=DLQTask,
    queue="billing.reminders",
    max_retries=3,
)
def anonymise_cancelled_store_pii(self) -> None:
    """
    Story 9.7 — Kenya DPA 2019 compliance: anonymise PII for stores that have
    been cancelled for more than 30 days.

    Anonymised fields:
    - Order.customer_phone → "ANONYMISED"
    - Order.customer_name  → ""
    - Order.customer_email → ""

    Scheduled: daily at 02:00 via Celery Beat.
    """
    try:
        from apps.saas.models import StoreSubscription, SubscriptionStatus
        from apps.order.models import Order

        cutoff = timezone.now() - timedelta(days=30)
        to_anonymise = StoreSubscription.objects.filter(
            status=SubscriptionStatus.CANCELLED,
            cancelled_at__lte=cutoff,
        ).select_related("store")

        anonymised_stores = 0
        for sub in to_anonymise:
            store = sub.store
            updated = Order.objects.filter(store=store).exclude(
                customer_phone="ANONYMISED"
            ).update(
                customer_phone="ANONYMISED",
                customer_name="",
                customer_email="",
            )
            if updated > 0:
                logger.info(
                    "pii_anonymised",
                    store_id=str(store.id),
                    orders_updated=updated,
                )
            anonymised_stores += 1

        logger.info("anonymise_pii_complete", stores_processed=anonymised_stores)

    except Exception as exc:
        logger.exception("anonymise_pii_failed")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


# ---------------------------------------------------------------------------
# Trial expiration pipeline
# ---------------------------------------------------------------------------


@shared_task(
    bind=True,
    base=DLQTask,
    queue="billing.reminders",
    max_retries=3,
)
def expire_trials(self) -> None:
    """
    Transition trials that have passed their trial_ends_at date to past_due.

    Scheduled: daily at 00:30 via Celery Beat.
    """
    try:
        from apps.saas.models import StoreSubscription, SubscriptionStatus, InvalidSubscriptionTransition

        today = timezone.localdate()
        expired_trials = StoreSubscription.objects.filter(
            status=SubscriptionStatus.TRIAL,
            trial_ends_at__lte=today,
        )

        expired = 0
        for sub in expired_trials:
            try:
                # If they have a paid plan, move to past_due; otherwise cancel
                if sub.plan and sub.plan.price_kes > 0:
                    sub.transition_status(SubscriptionStatus.PAST_DUE)
                else:
                    sub.transition_status(SubscriptionStatus.CANCELLED)
                expired += 1
                logger.info("trial_expired", store_id=str(sub.store_id), new_status=sub.status)
            except InvalidSubscriptionTransition:
                pass

        logger.info("expire_trials_complete", expired=expired)

    except Exception as exc:
        logger.exception("expire_trials_failed")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(
    bind=True,
    base=DLQTask,
    queue="billing.reminders",
    max_retries=3,
)
def activate_trial_subscriptions(self) -> None:
    """
    Set trial_ends_at for new subscriptions that don't have it set yet.

    Runs on store creation — sets trial period from the plan's trial_days.
    """
    try:
        from apps.saas.models import StoreSubscription, SubscriptionStatus

        # Find trial subscriptions without trial_ends_at
        unset = StoreSubscription.objects.filter(
            status=SubscriptionStatus.TRIAL,
            trial_ends_at__isnull=True,
        ).select_related("plan")

        activated = 0
        for sub in unset:
            trial_days = sub.plan.trial_days if sub.plan else 14
            sub.trial_ends_at = timezone.localdate() + timedelta(days=trial_days)
            sub.save(update_fields=["trial_ends_at", "updated_at"])
            activated += 1

        logger.info("activate_trials_complete", activated=activated)

    except Exception as exc:
        logger.exception("activate_trials_failed")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
