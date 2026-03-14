"""
SaaS / billing async tasks.

Story 7.2: send_subscription_renewal_reminder (Beat schedule)
Story 9.x: Full subscription lifecycle (Epic 9)

Queue: billing.reminders
DLQ pattern: max_retries=5, countdown=60 * (2 ** retries)
"""

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
    """Send subscription renewal reminder for a specific store. Epic 9 full body."""
    try:
        pass  # TODO: Epic 9 — check subscription expiry, send M-Pesa STK push reminder
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(
    bind=True,
    base=DLQTask,
    queue="billing.reminders",
    max_retries=3,
)
def send_subscription_renewal_reminder(self) -> None:
    """
    Story 7.2 — Scan all active subscriptions expiring in 3 days and
    dispatch renewal reminders.

    Scheduled: daily at 09:00 via Celery Beat.

    Full subscription model query implemented in Epic 9 (Story 9.2).
    Currently scans StoreSubscription stubs.
    """
    try:
        from datetime import timedelta

        target_date = timezone.localdate() + timedelta(days=3)
        logger.info("send_subscription_renewal_reminder_start", target_date=str(target_date))

        # TODO: Epic 9 — query StoreSubscription.period_end == target_date
        # for statuses: active, trial, past_due → enqueue send_billing_reminder per store
        logger.info("send_subscription_renewal_reminder_complete")

    except Exception as exc:
        logger.exception("send_subscription_renewal_reminder_failed")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
