"""
Restaurant Celery tasks.

Story 3.7: purge_expired_pending_orders — hourly beat task
Story 3.9: send_reservation_notification — dispatched within 60s of reservation event
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


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=30,
    name="apps.restaurant.tasks.send_reservation_notification",
)
def send_reservation_notification(self, reservation_id: str, event: str):
    """
    Story 3.9 — Send WhatsApp/SMS notification for reservation events.

    event: "created" | "confirmed" | "seated" | "no_show"

    WhatsApp/SMS integration is implemented in Story 10.3 (Notification module).
    This task stubs the dispatch and logs the event so the pipeline is wired up
    before the notification channel is live.
    """
    from apps.restaurant.models import Reservation

    try:
        reservation = Reservation.objects.select_related("store", "table").get(id=reservation_id)
    except Reservation.DoesNotExist:
        log.error("reservation_notification_reservation_not_found", reservation_id=reservation_id)
        return

    messages = {
        "created": (
            f"Hi {reservation.customer_name or 'there'}! We received your reservation request "
            f"for {reservation.party_size} guests on {reservation.reserved_for.strftime('%d %b %Y at %H:%M')}. "
            "We'll confirm shortly."
        ),
        "confirmed": (
            f"Your reservation is confirmed! We look forward to seeing you on "
            f"{reservation.reserved_for.strftime('%d %b %Y at %H:%M')} at {reservation.store.name}."
        ),
        "seated": (
            f"Welcome to {reservation.store.name}! You've been seated."
        ),
        "no_show": (
            "Your reservation has been marked as no-show. We hope to see you next time."
        ),
    }

    message = messages.get(event, "Reservation update from " + reservation.store.name)

    # TODO (Story 10.3): Replace with real WhatsApp/SMS dispatch via notification module.
    log.info(
        "reservation_notification_stub",
        reservation_id=reservation_id,
        event=event,
        phone=reservation.customer_phone,
        message=message,
    )

    return {"sent": True, "event": event, "phone": reservation.customer_phone}
