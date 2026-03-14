"""
Tests for Story 2.2: STK Push initiation + idempotency.

Covers:
- AC1: idempotency — returns existing STK_PUSH_INITIATED / CONFIRMED
- AC2: new reference → DarajaClient.initiate_stk_push() called, record created
- AC3: CheckoutRequestID stored on MpesaTransaction
- AC5: SELECT FOR UPDATE concurrent safety (threading test)
- AC6: phone normalization + InvalidPhoneNumberError propagation
- AC7: rate limiting — 4th attempt blocked, window expiry allows
- AC8: Daraja error → StkPushInitiationError, Sentry captured, no record
- AC12: InitiateStkPushView HTTP status codes (200/422/429/502)

Mock strategy:
- apps.payment.services.get_daraja_client: patched to inject a mock DarajaClient
- apps.payment.services.normalize_phone: patched to control normalization output
- apps.payment.services.sentry_sdk.capture_exception: patched for Sentry assertions
- View tests: APIRequestFactory + view.as_view() called directly with request.store set

Implementation: Story 2.2
"""

import datetime
import threading
import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.payment.exceptions import (
    InvalidPhoneNumberError,
    StkPushError,
    StkPushInitiationError,
    StkPushRateLimitedError,
)
from apps.payment.models import MpesaTransaction, MpesaTransactionStatus
from apps.payment.phone import PhoneNormalizationError
from apps.payment.services import initiate_payment
from apps.payment.views import InitiateStkPushView

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NORMALIZED_PHONE = "+254712345678"

DARAJA_SUCCESS = {
    "MerchantRequestID": "29115-34620561-1",
    "CheckoutRequestID": "ws_CO_191220191020363925",
    "ResponseCode": "0",
    "ResponseDescription": "Success. Request accepted for processing",
    "CustomerMessage": "Success. Request accepted for processing",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store():
    from apps.store.models import Store

    return Store.objects.create(
        name="Test Store",
        slug=f"test-{uuid.uuid4().hex[:8]}",
        domain=f"test-{uuid.uuid4().hex[:8]}.joat.com",
        country="KE",
    )


def _make_txn(
    store,
    reference="ORDER-001",
    status=MpesaTransactionStatus.STK_PUSH_INITIATED,
    initiated_at=None,
):
    txn = MpesaTransaction(
        store=store,
        reference=reference,
        phone=NORMALIZED_PHONE,
        amount="100.00",
        status=status,
        checkout_request_id="ws_CO_test_123",
        merchant_request_id="29115-test-1",
    )
    txn.save()
    if initiated_at is not None:
        MpesaTransaction.objects.filter(pk=txn.pk).update(initiated_at=initiated_at)
        txn.refresh_from_db()
    return txn


def _mock_daraja_client(response=None):
    client = MagicMock()
    client.initiate_stk_push.return_value = response or DARAJA_SUCCESS
    return client


def _call_view(store, user, payload):
    """Call InitiateStkPushView directly, injecting request.store."""
    factory = APIRequestFactory()
    request = factory.post(
        "/api/v1/payments/initiate-stk/", payload, format="json"
    )
    force_authenticate(request, user=user)
    request.store = store  # simulate TenantMiddleware
    view = InitiateStkPushView.as_view()
    return view(request)


# ---------------------------------------------------------------------------
# AC1 — Idempotency: existing pending/confirmed returned
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_idempotent_returns_existing_pending():
    """AC1: existing STK_PUSH_INITIATED → returned, no Daraja call."""
    store = _make_store()
    existing = _make_txn(store, reference="ORDER-IDEM-1")

    with (
        patch("apps.payment.services.normalize_phone", return_value=NORMALIZED_PHONE),
        patch("apps.payment.services.get_daraja_client") as mock_factory,
    ):
        result = initiate_payment(
            store=store, method="mpesa", amount="100",
            phone="0712345678", reference="ORDER-IDEM-1",
        )

    assert result.pk == existing.pk
    mock_factory.assert_not_called()


@pytest.mark.django_db
def test_idempotent_returns_existing_confirmed():
    """AC1: existing CONFIRMED → returned, no Daraja call."""
    store = _make_store()
    existing = _make_txn(
        store, reference="ORDER-IDEM-2", status=MpesaTransactionStatus.CONFIRMED
    )

    with (
        patch("apps.payment.services.normalize_phone", return_value=NORMALIZED_PHONE),
        patch("apps.payment.services.get_daraja_client") as mock_factory,
    ):
        result = initiate_payment(
            store=store, method="mpesa", amount="100",
            phone="0712345678", reference="ORDER-IDEM-2",
        )

    assert result.pk == existing.pk
    mock_factory.assert_not_called()


# ---------------------------------------------------------------------------
# AC2 — New reference initiates STK Push
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_new_reference_initiates_stk_push():
    """AC2: no existing record → Daraja called, new MpesaTransaction created."""
    store = _make_store()
    mock_client = _mock_daraja_client()

    with (
        patch("apps.payment.services.normalize_phone", return_value=NORMALIZED_PHONE),
        patch("apps.payment.services.get_daraja_client", return_value=mock_client),
        patch("apps.payment.services.settings") as s,
    ):
        s.MPESA_CALLBACK_URL = "https://example.com/callback/"
        txn = initiate_payment(
            store=store, method="mpesa", amount="100",
            phone="0712345678", reference="ORDER-NEW",
        )

    mock_client.initiate_stk_push.assert_called_once()
    assert txn.status == MpesaTransactionStatus.STK_PUSH_INITIATED
    assert MpesaTransaction.objects.filter(store=store, reference="ORDER-NEW").count() == 1


# ---------------------------------------------------------------------------
# AC3 — CheckoutRequestID stored
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_checkout_request_id_stored():
    """AC3: CheckoutRequestID from Daraja response saved on MpesaTransaction."""
    store = _make_store()
    mock_client = _mock_daraja_client()

    with (
        patch("apps.payment.services.normalize_phone", return_value=NORMALIZED_PHONE),
        patch("apps.payment.services.get_daraja_client", return_value=mock_client),
        patch("apps.payment.services.settings") as s,
    ):
        s.MPESA_CALLBACK_URL = "https://example.com/callback/"
        txn = initiate_payment(
            store=store, method="mpesa", amount="100",
            phone="0712345678", reference="ORDER-CRID",
        )

    assert txn.checkout_request_id == DARAJA_SUCCESS["CheckoutRequestID"]
    assert txn.merchant_request_id == DARAJA_SUCCESS["MerchantRequestID"]


# ---------------------------------------------------------------------------
# AC5 — Concurrent idempotency via SELECT FOR UPDATE
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_concurrent_idempotency_via_select_for_update():
    """AC5: two concurrent calls for same reference produce exactly one record.

    Note: unittest.mock.patch modifies module globals and is not strictly
    thread-safe. Both threads patch the same names to the same values, so
    interleaving the patches is safe here. The critical section being tested
    is the SELECT FOR UPDATE lock inside transaction.atomic(), which is
    thread- and process-safe at the DB level.
    """
    store = _make_store()
    results = []
    errors = []

    def call():
        try:
            with (
                patch("apps.payment.services.normalize_phone", return_value=NORMALIZED_PHONE),
                patch(
                    "apps.payment.services.get_daraja_client",
                    return_value=_mock_daraja_client(),
                ),
                patch("apps.payment.services.settings") as s,
            ):
                s.MPESA_CALLBACK_URL = "https://example.com/callback/"
                txn = initiate_payment(
                    store=store, method="mpesa", amount="100",
                    phone="0712345678", reference="ORDER-CONCURRENT",
                )
                results.append(txn.pk)
        except Exception as exc:
            errors.append(exc)

    t1, t2 = threading.Thread(target=call), threading.Thread(target=call)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert not errors, f"Unexpected errors: {errors}"
    count = MpesaTransaction.objects.filter(
        store=store, reference="ORDER-CONCURRENT"
    ).count()
    assert count == 1, f"Expected 1 record, got {count}"


# ---------------------------------------------------------------------------
# AC6 — Phone normalization
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_phone_normalization_called_with_store_country():
    """AC6: normalize_phone called with raw phone + country_code=store.country."""
    store = _make_store()
    mock_client = _mock_daraja_client()

    with (
        patch("apps.payment.services.normalize_phone", return_value=NORMALIZED_PHONE) as mock_norm,
        patch("apps.payment.services.get_daraja_client", return_value=mock_client),
        patch("apps.payment.services.settings") as s,
    ):
        s.MPESA_CALLBACK_URL = "https://example.com/callback/"
        initiate_payment(
            store=store, method="mpesa", amount="100",
            phone="0712345678", reference="ORDER-PHONE",
        )

    mock_norm.assert_called_once_with("0712345678", country_code="KE")


@pytest.mark.django_db
def test_invalid_phone_raises_and_no_daraja_call():
    """AC6: PhoneNormalizationError → InvalidPhoneNumberError, Daraja not called."""
    store = _make_store()

    with (
        patch(
            "apps.payment.services.normalize_phone",
            side_effect=PhoneNormalizationError("bad number"),
        ),
        patch("apps.payment.services.get_daraja_client") as mock_factory,
    ):
        with pytest.raises(InvalidPhoneNumberError, match="bad number"):
            initiate_payment(
                store=store, method="mpesa", amount="100",
                phone="bad", reference="ORDER-BADPH",
            )

    mock_factory.assert_not_called()


# ---------------------------------------------------------------------------
# AC7 — Rate limiting
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_rate_limit_blocks_4th_attempt():
    """AC7: 3 recent initiations → 4th raises StkPushRateLimitedError."""
    store = _make_store()
    for _ in range(3):
        _make_txn(store, reference="ORDER-RL", status=MpesaTransactionStatus.STK_PUSH_INITIATED)

    with (
        patch("apps.payment.services.normalize_phone", return_value=NORMALIZED_PHONE),
        patch("apps.payment.services.get_daraja_client") as mock_factory,
    ):
        with pytest.raises(StkPushRateLimitedError):
            initiate_payment(
                store=store, method="mpesa", amount="100",
                phone="0712345678", reference="ORDER-RL",
            )

    mock_factory.assert_not_called()


@pytest.mark.django_db
def test_rate_limit_does_not_block_old_records():
    """AC7: records older than 1 hour are outside the rate-limit window.

    Use EXPIRED status so old records are not caught by the idempotency check
    (which only catches STK_PUSH_INITIATED + CONFIRMED). The rate limiter counts
    both STK_PUSH_INITIATED and EXPIRED, so old EXPIRED records correctly test
    the time-window cutoff without triggering an early return.
    """
    from django.utils import timezone

    store = _make_store()
    old_time = timezone.now() - timedelta(hours=2)
    for _ in range(3):
        _make_txn(
            store, reference="ORDER-OLD",
            status=MpesaTransactionStatus.EXPIRED,
            initiated_at=old_time,
        )

    mock_client = _mock_daraja_client()
    with (
        patch("apps.payment.services.normalize_phone", return_value=NORMALIZED_PHONE),
        patch("apps.payment.services.get_daraja_client", return_value=mock_client),
        patch("apps.payment.services.settings") as s,
    ):
        s.MPESA_CALLBACK_URL = "https://example.com/callback/"
        txn = initiate_payment(
            store=store, method="mpesa", amount="100",
            phone="0712345678", reference="ORDER-OLD",
        )

    assert txn.status == MpesaTransactionStatus.STK_PUSH_INITIATED
    mock_client.initiate_stk_push.assert_called_once()


# ---------------------------------------------------------------------------
# AC8 — Daraja error handling
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_daraja_error_raises_initiation_error_and_no_record():
    """AC8: StkPushError → StkPushInitiationError, Sentry captured, no DB record."""
    store = _make_store()
    mock_client = MagicMock()
    mock_client.initiate_stk_push.side_effect = StkPushError("network timeout")

    with (
        patch("apps.payment.services.normalize_phone", return_value=NORMALIZED_PHONE),
        patch("apps.payment.services.get_daraja_client", return_value=mock_client),
        patch("apps.payment.services.sentry_sdk.capture_exception") as mock_capture,
        patch("apps.payment.services.settings") as s,
    ):
        s.MPESA_CALLBACK_URL = "https://example.com/callback/"
        with pytest.raises(StkPushInitiationError):
            initiate_payment(
                store=store, method="mpesa", amount="100",
                phone="0712345678", reference="ORDER-ERR",
            )

    mock_capture.assert_called_once()
    assert MpesaTransaction.objects.filter(store=store, reference="ORDER-ERR").count() == 0


# ---------------------------------------------------------------------------
# AC12 — InitiateStkPushView HTTP responses
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_view_200_on_success():
    """AC12: HTTP 200 with transaction_id and status on success."""
    from apps.users.models import User

    store = _make_store()
    user = User.objects.create_user(email="v1@test.com", password="pass")

    fake_txn = MagicMock()
    fake_txn.id = uuid.uuid4()
    fake_txn.status = MpesaTransactionStatus.STK_PUSH_INITIATED

    with patch("apps.payment.views.initiate_payment", return_value=fake_txn):
        response = _call_view(
            store, user,
            {"phone": "0712345678", "amount": "100.00", "reference": "V1", "method": "mpesa"},
        )

    assert response.status_code == 200
    assert str(fake_txn.id) == response.data["transaction_id"]
    assert response.data["status"] == MpesaTransactionStatus.STK_PUSH_INITIATED


@pytest.mark.django_db
def test_view_422_on_invalid_phone():
    """AC12: HTTP 422 with INVALID_PHONE_NUMBER code."""
    from apps.users.models import User

    store = _make_store()
    user = User.objects.create_user(email="v2@test.com", password="pass")

    with patch(
        "apps.payment.views.initiate_payment",
        side_effect=InvalidPhoneNumberError("cannot parse phone"),
    ):
        response = _call_view(
            store, user,
            {"phone": "bad", "amount": "100.00", "reference": "V2", "method": "mpesa"},
        )

    assert response.status_code == 422
    assert response.data["code"] == "INVALID_PHONE_NUMBER"


@pytest.mark.django_db
def test_view_429_on_rate_limited():
    """AC12: HTTP 429 with STK_PUSH_RATE_LIMITED code and retry_after."""
    from apps.users.models import User

    store = _make_store()
    user = User.objects.create_user(email="v3@test.com", password="pass")
    retry_at = datetime.datetime(2030, 6, 1, 12, 0, 0)

    with patch(
        "apps.payment.views.initiate_payment",
        side_effect=StkPushRateLimitedError(retry_at),
    ):
        response = _call_view(
            store, user,
            {"phone": "0712345678", "amount": "100.00", "reference": "V3", "method": "mpesa"},
        )

    assert response.status_code == 429
    assert response.data["code"] == "STK_PUSH_RATE_LIMITED"
    assert "retry_after" in response.data


@pytest.mark.django_db
def test_view_502_on_gateway_error():
    """AC12: HTTP 502 with PAYMENT_GATEWAY_ERROR code."""
    from apps.users.models import User

    store = _make_store()
    user = User.objects.create_user(email="v4@test.com", password="pass")

    with patch(
        "apps.payment.views.initiate_payment",
        side_effect=StkPushInitiationError("Daraja down"),
    ):
        response = _call_view(
            store, user,
            {"phone": "0712345678", "amount": "100.00", "reference": "V4", "method": "mpesa"},
        )

    assert response.status_code == 502
    assert response.data["code"] == "PAYMENT_GATEWAY_ERROR"
