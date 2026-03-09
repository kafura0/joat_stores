"""
Inventory async tasks — queue: inventory.alerts

DLQ pattern: max_retries=5, countdown=60 * (2 ** self.request.retries)
Full implementation in Epic 4.
"""

from celery import shared_task


@shared_task(bind=True, max_retries=5, queue="inventory.alerts")
def check_low_stock(self, store_id: int) -> None:
    """Detect low-stock products and notify supplier. Epic 4 implements body."""
    try:
        pass  # TODO: Epic 4 — query inventory, compare thresholds, send alerts
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))
