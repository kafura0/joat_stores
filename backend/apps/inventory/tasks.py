"""
Inventory async tasks — queue: inventory.alerts

DLQ pattern: max_retries=5, countdown=60 * (2 ** self.request.retries)
Full implementation in Epic 4.
"""

from celery import shared_task


@shared_task(bind=True, max_retries=5, queue="inventory.alerts")
def check_low_stock(self, store_id: str) -> None:
    """Detect low-stock variants and dispatch alerts to store owners."""
    try:
        from apps.product.models import Variant
        from apps.store.models import Store, StoreSettings

        store = Store.objects.get(id=store_id)
        threshold = StoreSettings.objects.filter(store=store).values_list(
            "low_stock_threshold", flat=True
        ).first() or 5

        low_stock_variants = Variant.objects.filter(
            store=store,
            inventory_count__lte=threshold,
            is_available=True,
        ).select_related("product")[:50]

        for variant in low_stock_variants:
            from apps.product.tasks import send_low_stock_alert

            send_low_stock_alert.delay(variant_id=str(variant.id))

        import structlog
        log = structlog.get_logger(__name__)
        log.info(
            "check_low_stock_complete",
            store_id=store_id,
            alerts_dispatched=low_stock_variants.count(),
        )
    except Exception as exc:
        import structlog
        log = structlog.get_logger(__name__)
        log.exception("check_low_stock_failed", store_id=store_id)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
