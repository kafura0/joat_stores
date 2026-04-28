"""
Payment async tasks — queue: payments.reconciliation

DLQ pattern: max_retries=5, countdown=60 * (2 ** self.request.retries)
Full implementation in Epic 2.
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

import structlog
from celery import shared_task

from apps.payment.exceptions import PaymentReversalError, TransactionStatusQueryError
from apps.payment.models import MpesaTransaction, MpesaTransactionStatus
from apps.payment.signals import payment_confirmed

log = structlog.get_logger(__name__)

_TERMINAL_STATUSES = {
    MpesaTransactionStatus.CONFIRMED,
    MpesaTransactionStatus.FAILED,
    MpesaTransactionStatus.EXPIRED,
    MpesaTransactionStatus.REVERSED,
}

_EXPIRED_RESULT_CODES = {1032, 1037}

_STK_PUSH_TIMEOUT_MINUTES = 5


@shared_task(bind=True, max_retries=5, queue="payments.reconciliation")
def reconcile_payment(self, payment_id: str) -> None:
    """Reconcile a single M-Pesa payment against Daraja Transaction Status API."""
    try:
        from apps.payment.daraja import get_daraja_client

        try:
            txn = MpesaTransaction.objects.get(id=payment_id)
        except MpesaTransaction.DoesNotExist:
            log.warning("reconcile_payment_not_found", payment_id=payment_id)
            return

        if txn.status in _TERMINAL_STATUSES:
            return

        client = get_daraja_client()
        try:
            result = client.query_transaction_status(txn.checkout_request_id)
            result_code = int(result.get("ResultCode", 999))
        except (TransactionStatusQueryError, ValueError):
            log.warning(
                "reconcile_payment_query_failed",
                payment_id=payment_id,
                checkout_request_id=txn.checkout_request_id,
            )
            raise self.retry(countdown=60 * (2**self.request.retries))

        now = timezone.now()
        if result_code == 0:
            txn.status = MpesaTransactionStatus.CONFIRMED
        elif result_code in _EXPIRED_RESULT_CODES:
            txn.status = MpesaTransactionStatus.EXPIRED
        else:
            txn.status = MpesaTransactionStatus.FAILED
        txn.completed_at = now
        txn.save(update_fields=["status", "completed_at"])
        log.info("reconcile_payment_complete", payment_id=payment_id, status=txn.status)

    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


@shared_task(bind=True, max_retries=5, queue="payments.reconciliation")
def process_mpesa_callback(self, payload: dict) -> None:
    """Process a Daraja STK Push webhook callback.

    Called asynchronously by MpesaCallbackView. Idempotent — safe to
    call multiple times for the same CheckoutRequestID.
    """
    try:
        _handle_mpesa_callback(self, payload)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


def _handle_mpesa_callback(task, payload: dict) -> None:
    """Inner handler for process_mpesa_callback — separated for clarity."""
    try:
        stk_callback = payload["Body"]["stkCallback"]
        checkout_request_id = stk_callback["CheckoutRequestID"]
        result_code = int(stk_callback["ResultCode"])
    except (KeyError, ValueError, TypeError) as exc:
        log.error("mpesa_callback_malformed_payload", error=str(exc))
        return  # Do not retry on malformed payload

    with transaction.atomic():
        try:
            txn = MpesaTransaction.objects.select_for_update().get(
                checkout_request_id=checkout_request_id
            )
        except MpesaTransaction.DoesNotExist:
            log.warning(
                "mpesa_callback_unknown_checkout_request_id",
                checkout_request_id=checkout_request_id,
            )
            return  # No retry — we have no record of this transaction

        # Idempotency guard
        if txn.status in _TERMINAL_STATUSES:
            log.info(
                "mpesa_callback_already_terminal",
                checkout_request_id=checkout_request_id,
                status=txn.status,
            )
            return

        now = timezone.now()

        if result_code == 0:
            # Extract receipt number from CallbackMetadata defensively
            items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
            receipt = next(
                (
                    item["Value"]
                    for item in items
                    if item.get("Name") == "MpesaReceiptNumber"
                ),
                None,
            )
            if receipt is None:
                log.error(
                    "mpesa_callback_missing_receipt_number",
                    checkout_request_id=checkout_request_id,
                )
            txn.status = MpesaTransactionStatus.CONFIRMED
            txn.mpesa_receipt_number = receipt
            txn.completed_at = now
            txn.save(update_fields=["status", "mpesa_receipt_number", "completed_at"])
            log.info(
                "mpesa_payment_confirmed",
                checkout_request_id=checkout_request_id,
                receipt=receipt,
            )
            # Emit signal after atomic commit so receivers see committed state
            transaction.on_commit(
                lambda: payment_confirmed.send(sender=MpesaTransaction, transaction=txn)
            )

        elif result_code in _EXPIRED_RESULT_CODES:
            txn.status = MpesaTransactionStatus.EXPIRED
            txn.completed_at = now
            txn.save(update_fields=["status", "completed_at"])
            log.info(
                "mpesa_payment_expired",
                checkout_request_id=checkout_request_id,
                result_code=result_code,
            )

        else:
            txn.status = MpesaTransactionStatus.FAILED
            txn.completed_at = now
            txn.save(update_fields=["status", "completed_at"])
            log.warning(
                "mpesa_payment_failed",
                checkout_request_id=checkout_request_id,
                result_code=result_code,
                result_desc=stk_callback.get("ResultDesc", ""),
            )


@shared_task(bind=True, max_retries=5, queue="payments.reconciliation")
def expire_stale_stk_pushes(self) -> None:
    """Expire STK Push transactions that passed Safaricom's 5-minute window.

    Runs every 2 minutes via Celery Beat. Idempotent — safe to run
    multiple times. Uses queryset.update() for performance (not per-row save).
    No Daraja API calls — purely local DB state management.
    """
    try:
        cutoff = timezone.now() - timedelta(minutes=_STK_PUSH_TIMEOUT_MINUTES)
        expired_count = MpesaTransaction.objects.filter(
            status=MpesaTransactionStatus.STK_PUSH_INITIATED,
            initiated_at__lt=cutoff,
        ).update(
            status=MpesaTransactionStatus.EXPIRED,
            completed_at=timezone.now(),
        )
        log.info("stk_push_expire_run_complete", expired_count=expired_count)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


@shared_task(bind=True, max_retries=5, queue="payments.reconciliation")
def initiate_reversal(self, transaction_id: str, reason: str) -> None:
    """Async wrapper around reverse_payment() for use by other verticals.

    PaymentReversalError (business logic error) is logged and NOT retried.
    Infrastructure errors are retried with exponential backoff.
    """
    from apps.payment.services import reverse_payment

    try:
        reverse_payment(transaction_id=transaction_id, reason=reason)
    except PaymentReversalError as exc:
        log.warning(
            "initiate_reversal_business_error",
            transaction_id=transaction_id,
            error=str(exc),
        )
        return
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


@shared_task(bind=True, max_retries=3, queue="payments.reconciliation")
def reconcile_payments(self) -> None:
    """Daily reconciliation: query Daraja for stale STK_PUSH_INITIATED txns.

    Fetches transactions older than 2 hours and updates their status
    by querying the Daraja Transaction Status API.
    """
    from apps.payment.daraja import get_daraja_client

    try:
        cutoff = timezone.now() - timedelta(hours=2)
        stale_qs = MpesaTransaction.objects.filter(
            status=MpesaTransactionStatus.STK_PUSH_INITIATED,
            initiated_at__lt=cutoff,
        )
        client = get_daraja_client()
        confirmed = expired = failed = 0

        for txn in stale_qs.iterator():
            try:
                result = client.query_transaction_status(txn.checkout_request_id)
                result_code = int(result.get("ResultCode", 999))
            except (TransactionStatusQueryError, ValueError):
                log.warning(
                    "reconcile_query_failed",
                    checkout_request_id=txn.checkout_request_id,
                )
                continue

            now = timezone.now()
            if result_code == 0:
                txn.status = MpesaTransactionStatus.CONFIRMED
                confirmed += 1
            elif result_code in (1032, 1037):
                txn.status = MpesaTransactionStatus.EXPIRED
                expired += 1
            else:
                txn.status = MpesaTransactionStatus.FAILED
                failed += 1
            txn.completed_at = now
            txn.save(update_fields=["status", "completed_at"])

        log.info(
            "reconcile_payments_complete",
            confirmed=confirmed,
            expired=expired,
            failed=failed,
        )
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))
