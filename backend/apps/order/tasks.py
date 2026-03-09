"""
Order async tasks — queue: order.notifications

DLQ pattern: max_retries=5, countdown=60 * (2 ** self.request.retries)
Full implementation in Epic 4.
"""

from celery import shared_task


@shared_task(bind=True, max_retries=5, queue="order.notifications")
def send_order_confirmation(self, order_id: int) -> None:
    """Send order confirmation email. Epic 4 implements the full body."""
    try:
        pass  # TODO: Epic 4 — fetch order, render template, send via email backend
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))
