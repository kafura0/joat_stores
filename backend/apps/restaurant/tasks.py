"""
Restaurant Celery tasks — Story 3.7.

purge_expired_pending_orders — hourly beat task that soft-deletes PendingOrders
past their expires_at timestamp. PAID orders are flagged for manual review
(Story 3.8 extension) and dispatched to billing.reminders queue instead.
"""

import structlog
from celery import shared_task
from django.utils import timezone

log = structlog.get_logger(__name__)


@shared_task(
    bind=True,
    queue="default",
    max_retries=3,
    default_retry_delay=60,
    name="apps.restaurant.tasks.purge_expired_pending_orders",
)
def purge_expired_pending_orders(self):
    """
    Hourly: soft-delete PENDING PendingOrders past expires_at.

    PAID orders past expires_at are NOT auto-deleted — they are dispatched to
    billing.reminders for operator review (Story 3.8).
    """
    from apps.restaurant.models import PendingOrder

    now = timezone.now()

    # Regular expired pending orders — soft-delete
    expired_qs = PendingOrder.objects.filter(
        status=PendingOrder.STATUS_PENDING,
        expires_at__lte=now,
    )
    count = expired_qs.count()
    expired_qs.update(status=PendingOrder.STATUS_EXPIRED)
    # Soft-delete via delete() on the queryset respects safedelete policy
    for order in PendingOrder.objects.filter(status=PendingOrder.STATUS_EXPIRED, expires_at__lte=now):
        order.delete()

    log.info("pending_orders_purged", count=count)

    # PAID + expired: flag for manual review (Story 3.8 hook)
    paid_expired = PendingOrder.objects.filter(
        status=PendingOrder.STATUS_PAID,
        expires_at__lte=now,
    )
    for order in paid_expired:
        log.warning(
            "paid_pending_order_expired_needs_review",
            order_id=str(order.id),
            store_id=str(order.store_id),
            phone=order.phone,
            total_amount=str(order.total_amount),
        )

    return {"purged": count, "paid_expired_flagged": paid_expired.count()}
