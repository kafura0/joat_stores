"""
Tests for Story 3.5 — QR Scan Errors + Wrong-Table Guard.

Covers:
- AC1: Valid token → response includes confirmation_prompt and fallback_url
- AC2: Customer wrong-table flow → fallback URL /t/{table_id}/ returns table info
- AC3: Expired token → user-friendly message (not technical details)
- AC4: Tampered/invalid token → generic message (no internal details exposed)
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.restaurant.qr import QR_TOKEN_TTL, generate_qr_token
from apps.restaurant.tests.factories import TableFactory
from apps.restaurant.views import PublicTableView, QRTokenValidateView
from apps.store.tests.factories import StoreFactory
from apps.users.tests.factories import UserFactory

SECRET = "test-secret-key"


def _make_redis_fresh():
    """Return a Redis mock that always reports token as fresh (SET NX succeeds)."""
    mock = MagicMock()
    mock.set.return_value = True  # SET NX succeeded → token not yet used
    return mock


def _make_redis_used():
    """Return a Redis mock that reports token already used (SET NX fails)."""
    mock = MagicMock()
    mock.set.return_value = False  # SET NX failed → already used
    return mock


# ---------------------------------------------------------------------------
# AC1: Valid token → confirmation_prompt + fallback_url in response
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_valid_token_returns_confirmation_prompt():
    store = StoreFactory(name="Mama's Kitchen")
    table = TableFactory(store=store, number=7)
    token = generate_qr_token(str(store.id), str(table.id), SECRET)

    request = APIRequestFactory().get("/qr/validate/", {"token": token})
    force_authenticate(request, user=UserFactory())

    with patch("apps.restaurant.views.get_redis_connection", return_value=_make_redis_fresh()), \
         patch("apps.restaurant.views.settings") as mock_settings:
        mock_settings.HMAC_QR_SECRET = SECRET
        response = QRTokenValidateView.as_view()(request)

    assert response.status_code == 200
    data = response.data
    assert data["table_number"] == 7
    assert data["store_name"] == "Mama's Kitchen"
    assert "Table 7" in data["confirmation_prompt"]
    assert "Mama's Kitchen" in data["confirmation_prompt"]
    assert data["fallback_url"] == f"/t/{table.id}/"


# ---------------------------------------------------------------------------
# AC2: Fallback URL /t/{table_id}/ returns public table info
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fallback_url_returns_table_info():
    store = StoreFactory(name="Bahari Grill")
    table = TableFactory(store=store, number=3, is_active=True)

    request = APIRequestFactory().get(f"/t/{table.id}/")
    response = PublicTableView.as_view()(request, table_id=str(table.id))

    assert response.status_code == 200
    assert response.data["table_number"] == 3
    assert response.data["store_name"] == "Bahari Grill"
    assert "Table 3" in response.data["message"]
    assert "Bahari Grill" in response.data["message"]


@pytest.mark.django_db
def test_fallback_url_404_for_unknown_table():
    import uuid

    request = APIRequestFactory().get(f"/t/{uuid.uuid4()}/")
    response = PublicTableView.as_view()(request, table_id=str(uuid.uuid4()))

    assert response.status_code == 404


@pytest.mark.django_db
def test_fallback_url_404_for_inactive_table():
    table = TableFactory(is_active=False)

    request = APIRequestFactory().get(f"/t/{table.id}/")
    response = PublicTableView.as_view()(request, table_id=str(table.id))

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# AC3: Expired token → user-friendly message
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_expired_token_returns_user_friendly_message():
    store = StoreFactory()
    table = TableFactory(store=store)
    # Generate a token that expired 1 second ago
    token = generate_qr_token(str(store.id), str(table.id), SECRET, ttl=-1)

    request = APIRequestFactory().get("/qr/validate/", {"token": token})

    with patch("apps.restaurant.views.get_redis_connection", return_value=_make_redis_fresh()), \
         patch("apps.restaurant.views.settings") as mock_settings:
        mock_settings.HMAC_QR_SECRET = SECRET
        response = QRTokenValidateView.as_view()(request)

    assert response.status_code == 400
    error = response.data["errors"][0]
    assert error["code"] == "QR_TOKEN_EXPIRED"
    # Must be the user-friendly message, not the internal one
    assert "waiter" in error["message"].lower()
    assert "expired" in error["message"].lower()
    # Must NOT contain internal details
    assert "exception" not in error["message"].lower()
    assert "traceback" not in error["message"].lower()


# ---------------------------------------------------------------------------
# AC4: Tampered token → generic error, no technical details
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tampered_token_returns_generic_error():
    store = StoreFactory()
    table = TableFactory(store=store)
    token = generate_qr_token(str(store.id), str(table.id), SECRET)
    # Tamper: flip a character in the signature
    payload_b64, sig = token.rsplit(".", 1)
    bad_sig = sig[:-1] + ("a" if sig[-1] != "a" else "b")
    tampered = f"{payload_b64}.{bad_sig}"

    request = APIRequestFactory().get("/qr/validate/", {"token": tampered})

    with patch("apps.restaurant.views.get_redis_connection", return_value=_make_redis_fresh()), \
         patch("apps.restaurant.views.settings") as mock_settings:
        mock_settings.HMAC_QR_SECRET = SECRET
        response = QRTokenValidateView.as_view()(request)

    assert response.status_code == 400
    error = response.data["errors"][0]
    assert error["code"] == "INVALID_QR_TOKEN"
    # Generic message — must NOT leak signature details
    assert "signature" not in error["message"].lower()
    assert "hmac" not in error["message"].lower()
    assert "hash" not in error["message"].lower()
    # Must contain something helpful for the user
    assert "damaged" in error["message"].lower() or "invalid" in error["message"].lower()


@pytest.mark.django_db
def test_malformed_token_no_dot_returns_generic_error():
    request = APIRequestFactory().get("/qr/validate/", {"token": "notavalidtoken"})

    with patch("apps.restaurant.views.get_redis_connection", return_value=_make_redis_fresh()), \
         patch("apps.restaurant.views.settings") as mock_settings:
        mock_settings.HMAC_QR_SECRET = SECRET
        response = QRTokenValidateView.as_view()(request)

    assert response.status_code == 400
    assert response.data["errors"][0]["code"] == "INVALID_QR_TOKEN"
    assert "malformed" not in response.data["errors"][0]["message"].lower()


def test_missing_token_returns_generic_error():
    request = APIRequestFactory().get("/qr/validate/")
    response = QRTokenValidateView.as_view()(request)

    assert response.status_code == 400
    assert response.data["errors"][0]["code"] == "INVALID_QR_TOKEN"
