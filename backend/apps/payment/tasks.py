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
    """Process a Daraja STK Push webhook callback."""
    try:
        _handle_mpesa_callback(self, payload)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


def _handle_mpesa_callback(task, payload: dict) -> None:
    """Inner handler for process_mpesa_callback."""
    try:
        stk_callback = payload["Body"]["stkCallback"]
        checkout_request_id = stk_callback["CheckoutRequestID"]
        result_code = int(stk_callback["ResultCode"])
    except (KeyError, ValueError, TypeError) as exc:
        log.error("mpesa_callback_malformed_payload", error=str(exc))
        return

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
            return

        if txn.status in _TERMINAL_STATUSES:
            log.info(
                "mpesa_callback_already_terminal",
                checkout_request_id=checkout_request_id,
                status=txn.status,
            )
            return

        now = timezone.now()

        if result_code == 0:
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
    """Expire STK Push transactions that passed Safaricom's 5-minute window."""
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
    """Async wrapper around reverse_payment()."""
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
    """Daily reconciliation: query Daraja for stale STK_PUSH_INITIATED txns."""
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


# ---------------------------------------------------------------------------
# C2B (Customer to Business) — till number / paybill payments
# ---------------------------------------------------------------------------


@shared_task(bind=True, max_retries=5, queue="payments.reconciliation")
def process_c2b_callback(self, payload: dict) -> None:
    """Process a Daraja C2B callback (customer pays to till/paybill).

    Matching strategy:
    1. Try Order (retail) — reference prefix "order-"
    2. Try PendingOrder (restaurant) — reference prefix "pending-"
    3. Try DineInOrder — reference prefix "dinein-"
    4. Try Tab (bar) — reference prefix "tab-"
    5. Log unmatched payment for manual reconciliation
    """
    try:
        _handle_c2b_callback(self, payload)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


def _handle_c2b_callback(task, payload: dict) -> None:
    """Inner handler for process_c2b_callback."""
    try:
        trans_id = payload.get("TransID", "")
        trans_amount = payload.get("TransAmount", "0")
        bill_ref = payload.get("BillRefNumber", "")
        msisdn = payload.get("MSISDN", "")
        first_name = payload.get("FirstName", "")
        last_name = payload.get("LastName", "")
        short_code = payload.get("BusinessShortCode", "")
    except (KeyError, ValueError, TypeError) as exc:
        log.error("c2b_callback_malformed_payload", error=str(exc))
        return

    if not trans_id or not bill_ref:
        log.error("c2b_callback_missing_fields", trans_id=trans_id, bill_ref=bill_ref)
        return

    log.info(
        "c2b_payment_received",
        trans_id=trans_id,
        amount=trans_amount,
        bill_ref=bill_ref,
        msisdn=msisdn,
    )

    from apps.store.models import Store

    # Find store by shortcode
    store = Store.objects.filter(mpesa_shortcode=short_code).first()
    if not store:
        last_txn = MpesaTransaction.objects.order_by("-id").first()
        store = last_txn.store if last_txn else None

    if not store:
        log.warning("c2b_callback_no_store_found", short_code=short_code)
        return

    # Create transaction record
    txn, created = MpesaTransaction.objects.get_or_create(
        store=store,
        mpesa_receipt_number=trans_id,
        defaults={
            "reference": bill_ref,
            "phone": msisdn,
            "amount": trans_amount,
            "status": MpesaTransactionStatus.CONFIRMED,
            "completed_at": timezone.now(),
        },
    )

    if not created and txn.status == MpesaTransactionStatus.CONFIRMED:
        log.info("c2b_callback_already_processed", trans_id=trans_id)
        return

    # Match to order based on BillRefNumber prefix
    reference = bill_ref.upper().strip()

    if reference.startswith("ORDER-"):
        _match_retail_order(store, reference[6:], trans_id, trans_amount, msisdn, first_name, last_name)
    elif reference.startswith("PENDING-"):
        _match_pending_order(store, reference[8:], trans_id, trans_amount)
    elif reference.startswith("DINEIN-"):
        _match_dinein_order(store, reference[7:], trans_id, trans_amount)
    elif reference.startswith("TAB-"):
        _match_bar_tab(store, reference[4:], trans_id, trans_amount)
    else:
        log.warning("c2b_callback_unmatched_payment", trans_id=trans_id, bill_ref=bill_ref)

    # Emit signal
    transaction.on_commit(
        lambda: payment_confirmed.send(sender=MpesaTransaction, transaction=txn)
    )


def _match_retail_order(store, order_id, receipt, amount, phone, first_name, last_name):
    from apps.order.models import Order, OrderStatus, InvalidOrderTransition

    try:
        order = Order.objects.get(id=order_id, store=store)
    except (Order.DoesNotExist, ValueError):
        log.warning("c2b_order_not_found", order_id=order_id)
        return

    try:
        order.transition_status(OrderStatus.CONFIRMED)
        log.info("c2b_order_confirmed", order_id=order_id, receipt=receipt)
    except InvalidOrderTransition:
        log.warning("c2b_order_invalid_transition", order_id=order_id, status=order.status)


def _match_pending_order(store, order_id, receipt, amount):
    from apps.restaurant.models import PendingOrder, PendingOrderStatus

    try:
        po = PendingOrder.objects.get(id=order_id, store=store)
    except (PendingOrder.DoesNotExist, ValueError):
        log.warning("c2b_pending_order_not_found", order_id=order_id)
        return

    if po.status != PendingOrderStatus.PAID:
        po.status = PendingOrderStatus.PAID
        po.save(update_fields=["status", "updated_at"])
        log.info("c2b_pending_order_paid", order_id=order_id, receipt=receipt)


def _match_dinein_order(store, order_id, receipt, amount):
    from apps.restaurant.models import DineInOrder, DineInOrderStatus

    try:
        order = DineInOrder.objects.get(id=order_id, store=store)
    except (DineInOrder.DoesNotExist, ValueError):
        log.warning("c2b_dinein_order_not_found", order_id=order_id)
        return

    if order.status != DineInOrderStatus.PAID:
        order.status = DineInOrderStatus.PAID
        order.save(update_fields=["status", "updated_at"])
        log.info("c2b_dinein_order_paid", order_id=order_id, receipt=receipt)


def _match_bar_tab(store, tab_id, receipt, amount):
    from apps.bar.models import Tab, TabStatus

    try:
        tab = Tab.objects.get(id=tab_id, store=store)
    except (Tab.DoesNotExist, ValueError):
        log.warning("c2b_tab_not_found", tab_id=tab_id)
        return

    if tab.status != TabStatus.SETTLED:
        tab.status = TabStatus.SETTLED
        tab.save(update_fields=["status", "updated_at"])
        log.info("c2b_tab_settled", tab_id=tab_id, receipt=receipt)
