"""
Tests for Story 2.5: Payment Reconciliation + Reversal.

Covers:
- AC1: reverse_payment() service — happy path sets REVERSED
- AC2: non-CONFIRMED status raises PaymentReversalError
- AC4: successful reversal saves status/completed_at/reversal_reason
- AC5: already-REVERSED returns existing transaction (idempotent)
- AC7: initiate_reversal task does NOT retry on PaymentReversalError
- AC8: reconcile_payments updates stale STK_PUSH_INITIATED txns
- AC10: ReversePaymentView returns 202 / 422

Implementation: Story 2.5
"""

import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from rest_framework.test import APIRequestFactory, force_authenticate

from apps.payment.exceptions import PaymentReversalError, ReversalError
from apps.payment.models import MpesaTransaction, MpesaTransactionStatus
from apps.payment.services import reverse_payment
from apps.payment.tasks import initiate_reversal, reconcile_payments
from apps.payment.views import ReversePaymentView


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store():
    from apps.store.models import Store

    return Store.objects.create(
        name="Reversal Test Store",
        slug=f"rev-{uuid.uuid4().hex[:8]}",
        domain=f"rev-{uuid.uuid4().hex[:8]}.joat.com",
        country="KE",
    )


def _make_user():
    from apps.users.tests.factories import UserFactory
    return UserFactory()


def _make_txn(store, status=MpesaTransactionStatus.CONFIRMED, receipt=None):
    txn = MpesaTransaction.objects.create(
        store=store,
        reference=f"ORDER-{uuid.uuid4().hex[:6]}",
        phone="+254712345678",
        amount="100.00",
        status=status,
        checkout_request_id=f"ws_CO_{uuid.uuid4().hex[:12]}",
        merchant_request_id=f"29115-{uuid.uuid4().hex[:6]}-1",
    )
    if receipt:
        MpesaTransaction.objects.filter(pk=txn.pk).update(
            mpesa_receipt_number=receipt
        )
        txn.refresh_from_db()
    return txn


def _backdate(txn, hours):
    MpesaTransaction.objects.filter(pk=txn.pk).update(
        initiated_at=timezone.now() - timedelta(hours=hours)
    )
    txn.refresh_from_db()


def _call_reverse_view(store, user, txn_id, payload=None):
    factory = APIRequestFactory()
    if payload is None:
        payload = {"reason": "Customer dispute"}
    request = factory.post(
        f"/api/v1/payments/{txn_id}/reverse/",
        data=payload,
        format="json",
    )
    force_authenticate(request, user=user)
    request.store = store
    view = ReversePaymentView.as_view()
    return view(request, transaction_id=txn_id)


# ---------------------------------------------------------------------------
# reverse_payment() service tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_reverse_payment_confirmed_success():
    """AC1/AC4: CONFIRMED txn → Daraja called → status=REVERSED, fields saved."""
    store = _make_store()
    txn = _make_txn(store, receipt="LGR7XXXXXXXX")

    with patch("apps.payment.services.get_daraja_client") as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_client.initiate_reversal.return_value = {
            "Result": {"ResultCode": 0, "ResultDesc": "Success"}
        }

        result = reverse_payment(str(txn.id), reason="Customer dispute")

    txn.refresh_from_db()
    assert result.status == MpesaTransactionStatus.REVERSED
    assert txn.status == MpesaTransactionStatus.REVERSED
    assert txn.reversal_reason == "Customer dispute"
    assert txn.completed_at is not None
    mock_client.initiate_reversal.assert_called_once()


@pytest.mark.django_db
def test_reverse_payment_already_reversed_idempotent():
    """AC5: already-REVERSED txn → returned immediately, no Daraja call."""
    store = _make_store()
    txn = _make_txn(store, status=MpesaTransactionStatus.REVERSED)

    with patch("apps.payment.services.get_daraja_client") as mock_factory:
        result = reverse_payment(str(txn.id), reason="Retry")
        mock_factory.assert_not_called()

    assert result.id == txn.id
    assert result.status == MpesaTransactionStatus.REVERSED


@pytest.mark.django_db
def test_reverse_payment_non_confirmed_raises():
    """AC2: non-CONFIRMED status raises PaymentReversalError, no Daraja call."""
    store = _make_store()
    txn = _make_txn(store, status=MpesaTransactionStatus.EXPIRED)

    with patch("apps.payment.services.get_daraja_client") as mock_factory:
        with pytest.raises(PaymentReversalError, match="EXPIRED"):
            reverse_payment(str(txn.id), reason="Dispute")
        mock_factory.assert_not_called()


@pytest.mark.django_db
def test_daraja_reversal_api_error_raises_payment_error():
    """AC3: DarajaClient raises ReversalError → service raises PaymentReversalError."""
    store = _make_store()
    txn = _make_txn(store, receipt="LGR7XXXXXXXX")

    with patch("apps.payment.services.get_daraja_client") as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_client.initiate_reversal.side_effect = ReversalError("Daraja rejected")

        with pytest.raises(PaymentReversalError, match="Daraja reversal failed"):
            reverse_payment(str(txn.id), reason="Dispute")

    # Status must NOT be changed to REVERSED
    txn.refresh_from_db()
    assert txn.status == MpesaTransactionStatus.CONFIRMED


# ---------------------------------------------------------------------------
# initiate_reversal task tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_initiate_reversal_task_non_confirmed_does_not_retry():
    """AC7: PaymentReversalError is caught and task exits without retry."""
    with patch(
        "apps.payment.services.reverse_payment",
        side_effect=PaymentReversalError("Not CONFIRMED"),
    ) as mock_rp:
        # Task must NOT raise — PaymentReversalError is a business error
        initiate_reversal(transaction_id="some-uuid", reason="Dispute")
        mock_rp.assert_called_once()


# ---------------------------------------------------------------------------
# reconcile_payments task tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_reconcile_payments_updates_confirmed():
    """AC8: stale STK_PUSH_INITIATED + Daraja returns ResultCode=0 → CONFIRMED."""
    store = _make_store()
    txn = _make_txn(store, status=MpesaTransactionStatus.STK_PUSH_INITIATED)
    _backdate(txn, hours=3)

    with patch("apps.payment.daraja.get_daraja_client") as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_client.query_transaction_status.return_value = {
            "ResultCode": 0,
            "ResultDesc": "Success",
        }

        reconcile_payments()

    txn.refresh_from_db()
    assert txn.status == MpesaTransactionStatus.CONFIRMED
    assert txn.completed_at is not None


@pytest.mark.django_db
def test_reconcile_payments_updates_expired():
    """AC8: stale STK_PUSH_INITIATED + ResultCode=1032 → EXPIRED."""
    store = _make_store()
    txn = _make_txn(store, status=MpesaTransactionStatus.STK_PUSH_INITIATED)
    _backdate(txn, hours=3)

    with patch("apps.payment.daraja.get_daraja_client") as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_client.query_transaction_status.return_value = {
            "ResultCode": 1032,
            "ResultDesc": "Cancelled",
        }

        reconcile_payments()

    txn.refresh_from_db()
    assert txn.status == MpesaTransactionStatus.EXPIRED


@pytest.mark.django_db
def test_reconcile_payments_skips_recent():
    """AC8: STK_PUSH_INITIATED txn < 2 hours old is not touched."""
    store = _make_store()
    txn = _make_txn(store, status=MpesaTransactionStatus.STK_PUSH_INITIATED)
    # initiated_at is auto_now_add — just created, well within 2h window

    with patch("apps.payment.daraja.get_daraja_client") as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client

        reconcile_payments()

        mock_client.query_transaction_status.assert_not_called()

    txn.refresh_from_db()
    assert txn.status == MpesaTransactionStatus.STK_PUSH_INITIATED


# ---------------------------------------------------------------------------
# ReversePaymentView tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_reverse_view_returns_202():
    """AC10: valid CONFIRMED txn → HTTP 202, task enqueued."""
    store = _make_store()
    user = _make_user()
    txn = _make_txn(store, status=MpesaTransactionStatus.CONFIRMED)

    with patch("apps.payment.views.initiate_reversal") as mock_task:
        response = _call_reverse_view(store, user, txn.id)

    assert response.status_code == 202
    assert response.data["status"] == "reversal_queued"
    assert response.data["transaction_id"] == str(txn.id)
    mock_task.delay.assert_called_once_with(
        transaction_id=str(txn.id), reason="Customer dispute"
    )


@pytest.mark.django_db
def test_reverse_view_non_confirmed_returns_422():
    """AC10: EXPIRED txn → HTTP 422 with REVERSAL_NOT_ALLOWED code."""
    store = _make_store()
    user = _make_user()
    txn = _make_txn(store, status=MpesaTransactionStatus.EXPIRED)

    response = _call_reverse_view(store, user, txn.id)

    assert response.status_code == 422
    assert response.data["code"] == "REVERSAL_NOT_ALLOWED"


@pytest.mark.django_db
def test_reverse_view_unknown_txn_returns_404():
    """L1: txn belonging to a different store → 404."""
    store = _make_store()
    other_store = _make_store()
    user = _make_user()
    txn = _make_txn(other_store, status=MpesaTransactionStatus.CONFIRMED)

    response = _call_reverse_view(store, user, txn.id)

    assert response.status_code == 404


@pytest.mark.django_db
def test_reverse_view_missing_reason_returns_400():
    """L2: missing/blank reason body → HTTP 400 REASON_REQUIRED."""
    store = _make_store()
    user = _make_user()
    txn = _make_txn(store, status=MpesaTransactionStatus.CONFIRMED)

    response = _call_reverse_view(store, user, txn.id, payload={"reason": ""})

    assert response.status_code == 400
    assert response.data["code"] == "REASON_REQUIRED"
