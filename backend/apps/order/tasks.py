"""
Order async tasks — Stories 4.3, 4.6.

Queue: order.notifications
DLQ: max_retries=5, countdown = 60 * (2 ** retries)
"""

import structlog
from celery import shared_task

log = structlog.get_logger(__name__)


@shared_task(
    bind=True,
    max_retries=5,
    queue="order.notifications",
    default_retry_delay=60,
)
def send_order_confirmation(self, order_id: str) -> None:
    """
    Story 4.3 / 4.6 — Send order confirmation email within 60s of order.confirmed.
    Dispatched via transaction.on_commit when order transitions to 'confirmed'.

    Email includes: order number, itemized variants, total paid, delivery/pickup details.
    Exponential backoff: countdown = 60 * (2 ** retries), max 5 retries → DLQ.
    """
    try:
        from apps.order.models import Order

        order = Order.objects.select_related("store").get(id=order_id)
        log.info(
            "order_confirmation_email",
            order_id=order_id,
            store_id=str(order.store_id),
            customer_email=order.customer_email or "no-email",
            status=order.status,
        )
        # TODO Story 4.6 full implementation: render email template + send via Django email backend
        # For now: log only (email infra wired in Epic 12 production hardening)

    except Exception as exc:
        log.error("order_confirmation_failed", order_id=order_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(
    bind=True,
    max_retries=5,
    queue="inventory.alerts",
    default_retry_delay=60,
)
def send_low_stock_alert_for_order(self, order_id: str) -> None:
    """
    Story 4.6 — After order confirmed, check if any ordered variants are now low-stock.
    Dispatched alongside send_order_confirmation on order.confirmed.
    """
    try:
        from apps.order.models import Order
        from apps.product.models import Variant, DEFAULT_LOW_STOCK_THRESHOLD

        order = Order.objects.get(id=order_id)
        for item in order.items_snapshot:
            vid = item.get("variant_id")
            if not vid:
                continue
            try:
                variant = Variant.objects.select_related("product").get(id=vid)
                threshold = variant._get_low_stock_threshold()
                if variant.inventory_count <= threshold:
                    log.info(
                        "low_stock_after_order",
                        order_id=order_id,
                        variant_id=vid,
                        inventory_count=variant.inventory_count,
                    )
            except Variant.DoesNotExist:
                pass

    except Exception as exc:
        log.error("low_stock_order_check_failed", order_id=order_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
