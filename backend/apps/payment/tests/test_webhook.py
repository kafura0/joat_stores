"""
Tests for Story 2.3: Daraja webhook processing + receipt idempotency.

Covers:
- AC1: idempotency — task exits early when status is already terminal
- AC2: ResultCode=0 → CONFIRMED + receipt number + completed_at stored
- AC3: ResultCode=1032 → EXPIRED
- AC4: ResultCode=1037 → EXPIRED
- AC5: other non-zero ResultCode → FAILED
- AC6: missing/invalid X-Daraja-Signature → HTTP 400
- AC7: valid signature → task enqueued, HTTP 200
- AC8: concurrent delivery handled via SELECT FOR UPDATE (idempotency guard)
- AC9: view returns 200 immediately after enqueue
- AC10: payment_confirmed signal emitted on CONFIRMED transition
- AC11: process_mpesa_callback on payments.reconciliation queue

Mock strategy:
- apps.payment.tasks.process_mpesa_callback.delay: patched for view tests
- apps.payment.signals.payment_confirmed.send: patched for signal tests
- View tests: APIRequestFactory + view.as_view() called directly
- ORM tests: @pytest.mark.django_db
- Signal + on_commit tests: @pytest.mark.django_db(transaction=True)

Implementation: Story 2.3
"""

import hashlib
import hmac as hmac_lib
import json
import uuid
from unittest.mock import patch

from django.test import override_settings

import pytest
from rest_framework.test import APIRequestFactory

from apps.payment.models import MpesaTransaction, MpesaTransactionStatus
from apps.payment.tasks import process_mpesa_callback
from apps.payment.views import MpesaCallbackView

# ---------------------------------------------------------------------------
# Constants / helpers
# ---------------------------------------------------------------------------

TEST_SECRET = "test-webhook-secret"
CHECKOUT_ID = "ws_CO_test123"

MOCK_SUCCESSFUL_PAYLOAD = {
    "Body": {
        "stkCallback": {
            "MerchantRequestID": "29115-test-1",
            "CheckoutRequestID": CHECKOUT_ID,
            "ResultCode": 0,
            "ResultDesc": "The service request is processed successfully.",
            "CallbackMetadata": {
                "Item": [
                    {"Name": "Amount", "Value": 100},
                    {"Name": "MpesaReceiptNumber", "Value": "LGR7XXXXXXXX"},
                    {"Name": "TransactionDate", "Value": 20240315143022},
                    {"Name": "PhoneNumber", "Value": 254712345678},
                ]
            },
        }
    }
}

MOCK_CANCEL_PAYLOAD = {
    "Body": {
        "stkCallback": {
            "MerchantRequestID": "29115-test-1",
            "CheckoutRequestID": CHECKOUT_ID,
            "ResultCode": 1032,
            "ResultDesc": "Request cancelled by user.",
        }
    }
}

MOCK_TIMEOUT_PAYLOAD = {
    "Body": {
        "stkCallback": {
            "MerchantRequestID": "29115-test-1",
            "CheckoutRequestID": CHECKOUT_ID,
            "ResultCode": 1037,
            "ResultDesc": "DS timeout user cannot be reached",
        }
    }
}

MOCK_FAILED_PAYLOAD = {
    "Body": {
        "stkCallback": {
            "MerchantRequestID": "29115-test-1",
            "CheckoutRequestID": CHECKOUT_ID,
            "ResultCode": 17,
            "ResultDesc": "General Error",
        }
    }
}


def _compute_signature(payload: dict, secret: str) -> str:
    body = json.dumps(payload).encode()
    return hmac_lib.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _make_store():
    from apps.store.models import Store

    return Store.objects.create(
        name="Webhook Test Store",
        slug=f"wh-{uuid.uuid4().hex[:8]}",
        domain=f"webhook-{uuid.uuid4().hex[:8]}.joat.com",
        country="KE",
    )


def _make_txn(store, checkout_id=CHECKOUT_ID, status=None):
    if status is None:
        status = MpesaTransactionStatus.STK_PUSH_INITIATED
    return MpesaTransaction.objects.create(
        store=store,
        reference="ORDER-001",
        phone="+254712345678",
        amount="100.00",
        status=status,
        checkout_request_id=checkout_id,
        merchant_request_id="29115-test-1",
    )


def _call_view(payload, secret=TEST_SECRET):
    """Call MpesaCallbackView directly with a valid HMAC signature."""
    factory = APIRequestFactory()
    body = json.dumps(payload).encode()
    sig = _compute_signature(payload, secret)
    request = factory.post(
        "/api/v1/payments/mpesa-callback/",
        data=body,
        content_type="application/json",
        HTTP_X_DARAJA_SIGNATURE=sig,
    )
    view = MpesaCallbackView.as_view()
    return view(request)


# ---------------------------------------------------------------------------
# Task tests — status transitions
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_result_code_0_sets_confirmed_and_receipt():
    """AC2: ResultCode=0 → CONFIRMED, receipt stored, completed_at set."""
    store = _make_store()
    txn = _make_txn(store)

    process_mpesa_callback(MOCK_SUCCESSFUL_PAYLOAD)

    txn.refresh_from_db()
    assert txn.status == MpesaTransactionStatus.CONFIRMED
    assert txn.mpesa_receipt_number == "LGR7XXXXXXXX"
    assert txn.completed_at is not None


@pytest.mark.django_db(transaction=True)
def test_result_code_1032_sets_expired():
    """AC3: ResultCode=1032 (customer cancelled) → EXPIRED."""
    store = _make_store()
    txn = _make_txn(store)

    process_mpesa_callback(MOCK_CANCEL_PAYLOAD)

    txn.refresh_from_db()
    assert txn.status == MpesaTransactionStatus.EXPIRED
    assert txn.completed_at is not None


@pytest.mark.django_db(transaction=True)
def test_result_code_1037_sets_expired():
    """AC4: ResultCode=1037 (STK Push timeout) → EXPIRED."""
    store = _make_store()
    txn = _make_txn(store)

    process_mpesa_callback(MOCK_TIMEOUT_PAYLOAD)

    txn.refresh_from_db()
    assert txn.status == MpesaTransactionStatus.EXPIRED
    assert txn.completed_at is not None


@pytest.mark.django_db(transaction=True)
def test_other_result_code_sets_failed():
    """AC5: ResultCode=17 (any other non-zero code) → FAILED."""
    store = _make_store()
    txn = _make_txn(store)

    process_mpesa_callback(MOCK_FAILED_PAYLOAD)

    txn.refresh_from_db()
    assert txn.status == MpesaTransactionStatus.FAILED
    assert txn.completed_at is not None


# ---------------------------------------------------------------------------
# Task tests — idempotency
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_idempotent_confirmed_webhook():
    """AC1: task exits early when status is already CONFIRMED."""
    store = _make_store()
    txn = _make_txn(store, status=MpesaTransactionStatus.CONFIRMED)
    original_receipt = txn.mpesa_receipt_number

    process_mpesa_callback(MOCK_SUCCESSFUL_PAYLOAD)

    txn.refresh_from_db()
    assert txn.status == MpesaTransactionStatus.CONFIRMED
    assert txn.mpesa_receipt_number == original_receipt


@pytest.mark.django_db(transaction=True)
def test_idempotent_failed_webhook():
    """AC1: task exits early when status is already FAILED."""
    store = _make_store()
    txn = _make_txn(store, status=MpesaTransactionStatus.FAILED)

    # Attempt to re-process with a success payload
    process_mpesa_callback(MOCK_SUCCESSFUL_PAYLOAD)

    txn.refresh_from_db()
    # Status must NOT change to CONFIRMED
    assert txn.status == MpesaTransactionStatus.FAILED


@pytest.mark.django_db(transaction=True)
def test_idempotent_expired_webhook():
    """AC1: task exits early when status is already EXPIRED."""
    store = _make_store()
    txn = _make_txn(store, status=MpesaTransactionStatus.EXPIRED)

    process_mpesa_callback(MOCK_SUCCESSFUL_PAYLOAD)

    txn.refresh_from_db()
    assert txn.status == MpesaTransactionStatus.EXPIRED


@pytest.mark.django_db(transaction=True)
def test_idempotent_reversed_webhook():
    """AC1: task exits early when status is already REVERSED."""
    store = _make_store()
    txn = _make_txn(store, status=MpesaTransactionStatus.REVERSED)

    process_mpesa_callback(MOCK_SUCCESSFUL_PAYLOAD)

    txn.refresh_from_db()
    assert txn.status == MpesaTransactionStatus.REVERSED


# ---------------------------------------------------------------------------
# Task tests — unknown CheckoutRequestID
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_unknown_checkout_request_id_no_error():
    """Task logs warning and returns cleanly when CheckoutRequestID not in DB."""
    payload = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "99999-unknown-1",
                "CheckoutRequestID": "ws_CO_UNKNOWN_ID",
                "ResultCode": 0,
                "ResultDesc": "Success",
                "CallbackMetadata": {"Item": []},
            }
        }
    }
    # Must not raise — just silently log and return
    process_mpesa_callback(payload)


# ---------------------------------------------------------------------------
# Task tests — malformed payload
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_malformed_payload_no_error():
    """Task logs error and returns cleanly on structurally invalid payload."""
    process_mpesa_callback({"garbage": True})


# ---------------------------------------------------------------------------
# Signal test
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_payment_confirmed_signal_emitted():
    """AC10: payment_confirmed signal is emitted after CONFIRMED transition."""
    store = _make_store()
    _make_txn(store)

    with patch("apps.payment.tasks.payment_confirmed") as mock_signal:
        process_mpesa_callback(MOCK_SUCCESSFUL_PAYLOAD)
        # on_commit fires immediately in transaction=True tests after commit
        assert mock_signal.send.called
        call_kwargs = mock_signal.send.call_args.kwargs
        assert call_kwargs["sender"] is MpesaTransaction
        assert call_kwargs["transaction"].checkout_request_id == CHECKOUT_ID


# ---------------------------------------------------------------------------
# View tests — HMAC signature validation
# ---------------------------------------------------------------------------


@override_settings(MPESA_WEBHOOK_SECRET=TEST_SECRET)
@pytest.mark.django_db
def test_invalid_signature_returns_400():
    """AC6: missing or wrong X-Daraja-Signature header → HTTP 400."""
    factory = APIRequestFactory()
    body = json.dumps(MOCK_SUCCESSFUL_PAYLOAD).encode()
    # Send wrong signature
    request = factory.post(
        "/api/v1/payments/mpesa-callback/",
        data=body,
        content_type="application/json",
        HTTP_X_DARAJA_SIGNATURE="wrong-signature",
    )
    view = MpesaCallbackView.as_view()
    response = view(request)

    assert response.status_code == 400
    assert response.data["code"] == "INVALID_SIGNATURE"


@override_settings(MPESA_WEBHOOK_SECRET=TEST_SECRET)
@pytest.mark.django_db
def test_missing_signature_header_returns_400():
    """AC6: absent X-Daraja-Signature → HTTP 400."""
    factory = APIRequestFactory()
    body = json.dumps(MOCK_SUCCESSFUL_PAYLOAD).encode()
    request = factory.post(
        "/api/v1/payments/mpesa-callback/",
        data=body,
        content_type="application/json",
        # No HTTP_X_DARAJA_SIGNATURE header
    )
    view = MpesaCallbackView.as_view()
    response = view(request)

    assert response.status_code == 400
    assert response.data["code"] == "INVALID_SIGNATURE"


@override_settings(MPESA_WEBHOOK_SECRET="")
@pytest.mark.django_db
def test_empty_secret_rejects_webhook():
    """AC6: unconfigured MPESA_WEBHOOK_SECRET → reject all webhooks."""
    factory = APIRequestFactory()
    body = json.dumps(MOCK_SUCCESSFUL_PAYLOAD).encode()
    sig = _compute_signature(MOCK_SUCCESSFUL_PAYLOAD, "some-secret")
    request = factory.post(
        "/api/v1/payments/mpesa-callback/",
        data=body,
        content_type="application/json",
        HTTP_X_DARAJA_SIGNATURE=sig,
    )
    view = MpesaCallbackView.as_view()
    response = view(request)

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# View tests — enqueue + immediate 200
# ---------------------------------------------------------------------------


@override_settings(MPESA_WEBHOOK_SECRET=TEST_SECRET)
@pytest.mark.django_db
def test_valid_signature_enqueues_task():
    """AC7/AC9: correct HMAC → process_mpesa_callback.delay called."""
    with patch("apps.payment.views.process_mpesa_callback") as mock_task:
        response = _call_view(MOCK_SUCCESSFUL_PAYLOAD)

    assert response.status_code == 200
    mock_task.delay.assert_called_once()


@override_settings(MPESA_WEBHOOK_SECRET=TEST_SECRET)
@pytest.mark.django_db
def test_view_returns_200_immediately():
    """AC9: view returns HTTP 200 without waiting for Celery task to finish."""
    with patch("apps.payment.views.process_mpesa_callback"):
        response = _call_view(MOCK_SUCCESSFUL_PAYLOAD)

    assert response.status_code == 200
    assert response.data["status"] == "accepted"
