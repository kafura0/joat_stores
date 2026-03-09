"""
Payment async tasks — queue: payments.reconciliation

DLQ pattern: max_retries=5, countdown=60 * (2 ** self.request.retries)
Full implementation in Epic 2.
"""

from celery import shared_task


@shared_task(bind=True, max_retries=5, queue="payments.reconciliation")
def reconcile_payment(self, payment_id: int) -> None:
    """Reconcile M-Pesa payment status with Daraja API. Epic 2 implements body."""
    try:
        pass  # TODO: Epic 2 — query Daraja transaction status, update payment record
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))
