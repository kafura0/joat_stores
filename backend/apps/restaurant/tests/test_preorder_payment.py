"""
Tests for Story 3.8 — Pre-Order + Advance M-Pesa Payment.

Covers:
- AC1: POST /pending-orders/{id}/pay/ → initiates STK Push; returns transaction_id
- AC2: payment_confirmed signal → PendingOrder.status→PAID
- AC3: Convert PAID order → DineInOrder with payment_transaction linked
- AC4: PAID+expired order not auto-deleted (verified in test_pending_order.py)
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIRequestFactory

from apps.payment.models import MpesaTransaction, MpesaTransactionStatus
from apps.restaurant.apps import _handle_payment_confirmed
from apps.restaurant.models import DineInOrder, PendingOrder
from apps.restaurant.tests.factories import (
    PendingOrderFactory,
    TableSessionFactory,
)
from apps.restaurant.views import PendingOrderConvertView, PendingOrderPayView
from apps.store.tests.factories import StoreFactory
from apps.users.tests.factories import UserFactory


# ---------------------------------------------------------------------------
# AC1: Initiate advance payment
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pay_endpoint_initiates_stk_push():
    store = StoreFactory()
    pending = PendingOrderFactory(store=store, phone="+254712345678", total_amount=Decimal("500.00"))

    mock_txn = MagicMock()
    mock_txn.id = "00000000-0000-0000-0000-000000000099"
    mock_txn.checkout_request_id = "ws_CO_123"

    request = APIRequestFactory().post(f"/pending-orders/{pending.id}/pay/", {}, format="json")
    request.store = store

    with patch("apps.restaurant.views.initiate_payment", return_value=mock_txn) as mock_init:
        response = PendingOrderPayView.as_view()(request, order_id=str(pending.id))

    assert response.status_code == 200
    mock_init.assert_called_once_with(
        store=store,
        method="mpesa",
        amount=pending.total_amount,
        phone=pending.phone,
        reference=f"pending-{pending.id}",
    )
    assert response.data["transaction_id"] == str(mock_txn.id)


@pytest.mark.django_db
def test_pay_endpoint_returns_404_for_paid_order():
    store = StoreFactory()
    pending = PendingOrderFactory(store=store, status=PendingOrder.STATUS_PAID)

    request = APIRequestFactory().post(f"/pending-orders/{pending.id}/pay/", {}, format="json")
    request.store = store

    response = PendingOrderPayView.as_view()(request, order_id=str(pending.id))
    assert response.status_code == 404


@pytest.mark.django_db
def test_pay_endpoint_rate_limited_returns_429():
    from datetime import datetime, timezone

    from apps.payment.exceptions import StkPushRateLimitedError

    store = StoreFactory()
    pending = PendingOrderFactory(store=store)

    retry_after = datetime(2026, 3, 14, 12, 0, tzinfo=timezone.utc)
    request = APIRequestFactory().post(f"/pending-orders/{pending.id}/pay/", {}, format="json")
    request.store = store

    with patch("apps.restaurant.views.initiate_payment", side_effect=StkPushRateLimitedError(retry_after)):
        response = PendingOrderPayView.as_view()(request, order_id=str(pending.id))

    assert response.status_code == 429
    assert response.data["errors"][0]["code"] == "RATE_LIMITED"


# ---------------------------------------------------------------------------
# AC2: Signal handler transitions PendingOrder to PAID
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_payment_confirmed_signal_marks_pending_order_paid():
    store = StoreFactory()
    pending = PendingOrderFactory(store=store, status=PendingOrder.STATUS_PENDING)

    mock_txn = MagicMock()
    mock_txn.reference = f"pending-{pending.id}"
    mock_txn.id = "some-txn-id"

    _handle_payment_confirmed(sender=None, transaction=mock_txn)

    pending.refresh_from_db()
    assert pending.status == PendingOrder.STATUS_PAID


@pytest.mark.django_db
def test_payment_confirmed_signal_ignores_non_pending_reference():
    store = StoreFactory()
    pending = PendingOrderFactory(store=store, status=PendingOrder.STATUS_PENDING)

    mock_txn = MagicMock()
    mock_txn.reference = "order-some-other-id"

    _handle_payment_confirmed(sender=None, transaction=mock_txn)

    pending.refresh_from_db()
    assert pending.status == PendingOrder.STATUS_PENDING  # unchanged


@pytest.mark.django_db
def test_payment_confirmed_signal_handles_missing_order_gracefully():
    """Signal should not raise even if PendingOrder not found."""
    import uuid

    mock_txn = MagicMock()
    mock_txn.reference = f"pending-{uuid.uuid4()}"
    mock_txn.id = "txn-id"

    # Should not raise
    _handle_payment_confirmed(sender=None, transaction=mock_txn)


# ---------------------------------------------------------------------------
# AC3: Convert PAID order links MpesaTransaction to DineInOrder
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_convert_paid_order_links_payment_transaction():
    store = StoreFactory()
    session = TableSessionFactory(store=store)
    pending = PendingOrderFactory(store=store, status=PendingOrder.STATUS_PAID)
    user = UserFactory()

    # Create a confirmed MpesaTransaction for this pending order
    txn = MpesaTransaction.objects.create(
        store=store,
        reference=f"pending-{pending.id}",
        phone=pending.phone,
        amount=pending.total_amount,
        status=MpesaTransactionStatus.CONFIRMED,
    )

    request = APIRequestFactory().post(
        f"/pending-orders/{pending.id}/convert/",
        data={"session_id": str(session.id)},
        format="json",
    )
    request.store = store
    from rest_framework.test import force_authenticate
    force_authenticate(request, user=user)

    response = PendingOrderConvertView.as_view()(request, order_id=str(pending.id))

    assert response.status_code == 201
    order = DineInOrder.objects.get(id=response.data["id"])
    assert order.payment_transaction_id == txn.id
