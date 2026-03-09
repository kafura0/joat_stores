"""
SaaS / billing async tasks — queue: billing.reminders

DLQ pattern: max_retries=5, countdown=60 * (2 ** self.request.retries)
Full implementation in Epic 9.
"""

from celery import shared_task


@shared_task(bind=True, max_retries=5, queue="billing.reminders")
def send_billing_reminder(self, store_id: int) -> None:
    """Send subscription renewal reminder. Epic 9 implements the full body."""
    try:
        pass  # TODO: Epic 9 — check subscription expiry, send M-Pesa STK push reminder
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))
