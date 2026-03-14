"""Payment service layer — single entry point for all payment flows.

All commerce verticals (retail, restaurant, bar, SaaS) call
initiate_payment() here. Direct calls to DarajaClient from outside
this module are forbidden.

Implementation: Story 2.2
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

import sentry_sdk
import structlog

from apps.payment.daraja import get_daraja_client
from apps.payment.exceptions import (
    InvalidPhoneNumberError,
    PaymentReversalError,
    ReversalError,
    StkPushError,
    StkPushInitiationError,
    StkPushRateLimitedError,
    UnsupportedPaymentMethodError,
)
from apps.payment.models import MpesaTransaction, MpesaTransactionStatus
from apps.payment.phone import PhoneNormalizationError, normalize_phone

log = structlog.get_logger(__name__)

_RATE_LIMIT_WINDOW_HOURS = 1
_RATE_LIMIT_MAX_ATTEMPTS = 3


def initiate_payment(
    store,
    method: str,
    amount,
    phone: str,
    reference: str,
) -> MpesaTransaction:
    """Initiate an M-Pesa STK Push payment.

    Enforces phone normalization, rate limiting, and idempotency (via
    SELECT FOR UPDATE). Calls Daraja inside transaction.atomic() so a
    failed push never leaves a partial MpesaTransaction in the DB.

    Args:
        store: Store instance (from request.store via TenantMiddleware).
        method: Payment method — currently only "mpesa" is supported.
        amount: Payment amount (Decimal or numeric string).
        phone: Customer phone in any Kenyan format.
        reference: Unique order/tab/subscription identifier for this store.

    Returns:
        MpesaTransaction instance (existing if idempotent, new otherwise).

    Raises:
        InvalidPhoneNumberError: Unrecognised phone format.
        StkPushRateLimitedError: >3 attempts for the same reference in 1 hour.
        StkPushInitiationError: Daraja API call failed.
    """
    # Validate payment method — only M-Pesa STK Push is supported now
    if method != "mpesa":
        raise UnsupportedPaymentMethodError(
            f"Unsupported payment method: {method!r}. Only 'mpesa' is supported."
        )

    # Step 1 — Phone normalization
    try:
        normalized_phone = normalize_phone(phone, country_code=store.country)
    except PhoneNormalizationError as exc:
        raise InvalidPhoneNumberError(str(exc)) from exc
    log.info("payment_phone_normalized", reference=reference)

    # Step 2 — Rate limit check (outside atomic — read-only, no lock needed)
    one_hour_ago = timezone.now() - timedelta(hours=_RATE_LIMIT_WINDOW_HOURS)
    recent_attempts = MpesaTransaction.objects.filter(
        store=store,
        reference=reference,
        status__in=[
            MpesaTransactionStatus.STK_PUSH_INITIATED,
            MpesaTransactionStatus.EXPIRED,
        ],
        initiated_at__gte=one_hour_ago,
    )
    count = recent_attempts.count()
    if count >= _RATE_LIMIT_MAX_ATTEMPTS:
        oldest = recent_attempts.order_by("initiated_at").first()
        retry_after = oldest.initiated_at + timedelta(hours=_RATE_LIMIT_WINDOW_HOURS)
        log.warning("stk_push_rate_limited", reference=reference, count=count)
        raise StkPushRateLimitedError(retry_after)

    # Steps 3+4 — Idempotency check + Daraja call inside a single atomic block
    with transaction.atomic():
        existing = (
            MpesaTransaction.objects.select_for_update()
            .filter(
                store=store,
                reference=reference,
                status__in=[
                    MpesaTransactionStatus.STK_PUSH_INITIATED,
                    MpesaTransactionStatus.CONFIRMED,
                ],
            )
            .first()
        )
        if existing:
            log.info(
                "stk_push_idempotent_return",
                reference=reference,
                status=existing.status,
            )
            return existing

        # Call Daraja (still inside atomic — rollback on failure = no partial record)
        client = get_daraja_client()
        callback_url = settings.MPESA_CALLBACK_URL
        try:
            daraja_response = client.initiate_stk_push(
                phone=normalized_phone,
                amount=str(amount),
                reference=reference,
                callback_url=callback_url,
            )
        except StkPushError as exc:
            sentry_sdk.capture_exception(exc)
            log.error(
                "stk_push_daraja_error", reference=reference, error=str(exc)
            )
            raise StkPushInitiationError(str(exc)) from exc

        txn = MpesaTransaction(
            store=store,
            reference=reference,
            phone=normalized_phone,
            amount=amount,
            status=MpesaTransactionStatus.STK_PUSH_INITIATED,
            checkout_request_id=daraja_response.get("CheckoutRequestID", ""),
            merchant_request_id=daraja_response.get("MerchantRequestID", ""),
        )
        txn.save()
        log.info(
            "mpesa_transaction_created",
            transaction_id=str(txn.id),
            reference=reference,
        )
        return txn


def reverse_payment(transaction_id: str, reason: str) -> MpesaTransaction:
    """Reverse a confirmed M-Pesa payment via the Daraja Reversal API.

    Args:
        transaction_id: UUID string of the MpesaTransaction to reverse.
        reason: Human-readable reason for the reversal (stored on the record).

    Returns:
        Updated MpesaTransaction with status=REVERSED.

    Raises:
        MpesaTransaction.DoesNotExist: Transaction not found.
        PaymentReversalError: Transaction not in CONFIRMED status,
            or Daraja reversal API call failed.
    """
    txn = MpesaTransaction.objects.get(id=transaction_id)

    # Idempotency: already reversed — return without hitting Daraja again
    if txn.status == MpesaTransactionStatus.REVERSED:
        log.info("reverse_payment_already_reversed", transaction_id=transaction_id)
        return txn

    # Guard: only CONFIRMED transactions can be reversed
    if txn.status != MpesaTransactionStatus.CONFIRMED:
        raise PaymentReversalError(
            f"Cannot reverse transaction with status {txn.status!r}. "
            "Only CONFIRMED transactions can be reversed."
        )

    client = get_daraja_client()
    try:
        client.initiate_reversal(
            transaction_id=txn.mpesa_receipt_number,
            amount=str(int(txn.amount)),
            reason=reason,
        )
    except ReversalError as exc:
        sentry_sdk.capture_exception(exc)
        log.error(
            "daraja_reversal_failed",
            transaction_id=transaction_id,
            error=str(exc),
        )
        raise PaymentReversalError(f"Daraja reversal failed: {exc}") from exc

    txn.status = MpesaTransactionStatus.REVERSED
    txn.completed_at = timezone.now()
    txn.reversal_reason = reason
    txn.save(update_fields=["status", "completed_at", "reversal_reason"])

    log.info("payment_reversed", transaction_id=transaction_id, reason=reason)
    return txn
