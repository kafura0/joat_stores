"""
Inventory async tasks — queue: inventory.alerts

DLQ pattern: max_retries=5, countdown=60 * (2 ** self.request.retries)
Full implementation in Epic 4.
"""

from celery import shared_task


@shared_task(bind=True, max_retries=5, queue="inventory.alerts")
def check_low_stock(self, store_id: str = None) -> None:
    """Detect low-stock variants and dispatch alerts.

    If store_id is provided, checks one store.
    If store_id is None (cron job), checks all active stores.
    """
    import structlog
    log = structlog.get_logger(__name__)

    try:
        from apps.product.models import Variant
        from apps.store.models import Store, StoreSettings

        if store_id:
            stores = Store.objects.filter(id=store_id)
        else:
            stores = Store.objects.filter(status="active")

        total_alerts = 0
        for store in stores:
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
                total_alerts += 1

        log.info(
            "check_low_stock_complete",
            store_id=store_id or "all",
            alerts_dispatched=total_alerts,
        )
    except Exception as exc:
        log.exception("check_low_stock_failed", store_id=store_id)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
