"""
Celery tasks for product catalog — Story 4.1.
"""

import structlog
from celery import shared_task

log = structlog.get_logger(__name__)


@shared_task(
    bind=True,
    max_retries=5,
    queue="inventory.alerts",
    default_retry_delay=60,
)
def send_low_stock_alert(self, variant_id: str) -> None:
    """
    Story 4.1 — Notify store owner when a variant's inventory_count is at or
    below the configured low-stock threshold.

    Dispatched via transaction.on_commit from Variant.save() → inventory.alerts queue.
    Exponential backoff: countdown = 60 * (2 ** retries), max 5 retries.
    """
    try:
        from apps.product.models import Variant

        variant = Variant.objects.select_related("product", "store").get(id=variant_id)
        store = variant.store

        log.info(
            "low_stock_alert",
            variant_id=variant_id,
            product_name=variant.product.name,
            inventory_count=variant.inventory_count,
            store_id=str(store.id),
        )
        # TODO Story 4.6: send supplier notification email when email backend is configured
        # For now: log only (WhatsApp/SMS stub in Story 10.3)

    except Exception as exc:
        log.error("low_stock_alert_failed", variant_id=variant_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
