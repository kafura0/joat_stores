"""
Tests for Story 3.3 — HMAC QR Table Token.

Covers:
- AC1: Token generation encodes store_id + table_id + timestamp with HMAC-SHA256
- AC2: Valid token → table+store details; invalid → 400; expired → 400
- AC3: Replay guard — second use → 400 QR_TOKEN_ALREADY_USED
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.restaurant.qr import (
    QRTokenError,
    generate_qr_token,
    validate_qr_token,
)
from apps.restaurant.tests.factories import TableFactory
from apps.restaurant.views import QRTokenGenerateView, QRTokenValidateView
from apps.store.tests.factories import StoreFactory
from apps.users.tests.factories import UserFactory

SECRET = "test-secret-key"


# ---------------------------------------------------------------------------
# qr.py unit tests
# ---------------------------------------------------------------------------


def test_generate_token_returns_string():
    token = generate_qr_token("store-1", "table-1", SECRET)
    assert "." in token
    payload_b64, sig = token.rsplit(".", 1)
    assert len(sig) == 64  # SHA256 hex


def test_validate_valid_token():
    token = generate_qr_token("store-1", "table-1", SECRET)
    redis = MagicMock()
    redis.set.return_value = True  # not already used
    payload = validate_qr_token(token, SECRET, redis)
    assert payload["store_id"] == "store-1"
    assert payload["table_id"] == "table-1"


def test_validate_tampered_token_raises():
    token = generate_qr_token("store-1", "table-1", SECRET)
    tampered = token[:-5] + "aaaaa"
    redis = MagicMock()
    with pytest.raises(QRTokenError) as exc_info:
        validate_qr_token(tampered, SECRET, redis)
    assert exc_info.value.code == "INVALID_QR_TOKEN"


def test_validate_expired_token_raises():
    token = generate_qr_token("store-1", "table-1", SECRET, ttl=1)
    time.sleep(2)
    redis = MagicMock()
    with pytest.raises(QRTokenError) as exc_info:
        validate_qr_token(token, SECRET, redis)
    assert exc_info.value.code == "QR_TOKEN_EXPIRED"


def test_validate_replay_raises():
    token = generate_qr_token("store-1", "table-1", SECRET)
    redis = MagicMock()
    # First call: SET NX returns True (not used)
    redis.set.return_value = True
    validate_qr_token(token, SECRET, redis)
    # Second call: SET NX returns False (already used)
    redis.set.return_value = False
    with pytest.raises(QRTokenError) as exc_info:
        validate_qr_token(token, SECRET, redis)
    assert exc_info.value.code == "QR_TOKEN_ALREADY_USED"


def test_validate_malformed_token_raises():
    redis = MagicMock()
    with pytest.raises(QRTokenError) as exc_info:
        validate_qr_token("notavalidtoken", SECRET, redis)
    assert exc_info.value.code == "INVALID_QR_TOKEN"


# ---------------------------------------------------------------------------
# View tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_qr_generate_view_returns_token():
    store = StoreFactory()
    user = UserFactory()
    table = TableFactory(store=store)

    factory = APIRequestFactory()
    request = factory.post(f"/api/v1/restaurant/tables/{table.id}/qr-token/")
    force_authenticate(request, user=user)
    request.store = store
    view = QRTokenGenerateView.as_view()
    response = view(request, table_id=table.id)

    assert response.status_code == 200
    assert "token" in response.data
    assert "." in response.data["token"]


@pytest.mark.django_db
def test_qr_generate_view_wrong_store_returns_404():
    store1 = StoreFactory()
    store2 = StoreFactory()
    user = UserFactory()
    table = TableFactory(store=store1)

    factory = APIRequestFactory()
    request = factory.post(f"/api/v1/restaurant/tables/{table.id}/qr-token/")
    force_authenticate(request, user=user)
    request.store = store2
    view = QRTokenGenerateView.as_view()
    response = view(request, table_id=table.id)
    assert response.status_code == 404


@pytest.mark.django_db
def test_qr_validate_view_valid_token():
    store = StoreFactory()
    table = TableFactory(store=store)
    token = generate_qr_token(str(store.id), str(table.id), "dev-qr-secret-change-in-prod")

    factory = APIRequestFactory()
    request = factory.get(f"/api/v1/restaurant/qr/validate/?token={token}")
    request.store = store

    with patch("django_redis.get_redis_connection") as mock_redis:
        mock_client = MagicMock()
        mock_client.set.return_value = True
        mock_redis.return_value = mock_client

        view = QRTokenValidateView.as_view()
        response = view(request)

    assert response.status_code == 200
    assert response.data["table_id"] == str(table.id)


@pytest.mark.django_db
def test_qr_validate_view_invalid_token_returns_400():
    store = StoreFactory()
    factory = APIRequestFactory()
    request = factory.get("/api/v1/restaurant/qr/validate/?token=bad.token")
    request.store = store

    with patch("django_redis.get_redis_connection") as mock_redis:
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        view = QRTokenValidateView.as_view()
        response = view(request)

    assert response.status_code == 400
    assert response.data["errors"][0]["code"] == "INVALID_QR_TOKEN"


@pytest.mark.django_db
def test_qr_validate_view_already_used_returns_400():
    store = StoreFactory()
    table = TableFactory(store=store)
    token = generate_qr_token(str(store.id), str(table.id), "dev-qr-secret-change-in-prod")

    factory = APIRequestFactory()
    request = factory.get(f"/api/v1/restaurant/qr/validate/?token={token}")
    request.store = store

    with patch("django_redis.get_redis_connection") as mock_redis:
        mock_client = MagicMock()
        mock_client.set.return_value = False  # already used
        mock_redis.return_value = mock_client
        view = QRTokenValidateView.as_view()
        response = view(request)

    assert response.status_code == 400
    assert response.data["errors"][0]["code"] == "QR_TOKEN_ALREADY_USED"
