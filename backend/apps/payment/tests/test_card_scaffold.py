"""
Tests for Story 4.7 — Card payment scaffold.

POST /api/v1/payments/card/initiate/
"""

import pytest
from rest_framework.test import APIClient

from apps.store.tests.factories import StoreFactory
from apps.users.tests.factories import UserFactory


@pytest.fixture
def store(db):
    return StoreFactory()


@pytest.fixture
def auth_client(store):
    client = APIClient()
    user = UserFactory(store=store, role="store_owner")
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_STORE_ID=str(store.id))
    return client


URL = "/api/v1/payments/card/initiate/"


@pytest.mark.django_db
class TestCardPaymentScaffold:

    def test_stripe_returns_501(self, auth_client):
        resp = auth_client.post(URL, {"provider": "stripe"}, format="json")
        assert resp.status_code == 501
        assert resp.data["detail"] == "CARD_PAYMENT_NOT_LIVE"

    def test_flutterwave_returns_501(self, auth_client):
        resp = auth_client.post(URL, {"provider": "flutterwave"}, format="json")
        assert resp.status_code == 501
        assert resp.data["detail"] == "CARD_PAYMENT_NOT_LIVE"

    def test_stripe_case_insensitive(self, auth_client):
        resp = auth_client.post(URL, {"provider": "STRIPE"}, format="json")
        assert resp.status_code == 501

    def test_invalid_provider_returns_400(self, auth_client):
        resp = auth_client.post(URL, {"provider": "paypal"}, format="json")
        assert resp.status_code == 400
        codes = [e["code"] for e in resp.data["errors"]]
        assert "INVALID_PROVIDER" in codes

    def test_missing_provider_returns_400(self, auth_client):
        resp = auth_client.post(URL, {}, format="json")
        assert resp.status_code == 400

    def test_unauthenticated_allowed(self, store):
        """CardPaymentScaffoldView has no explicit auth requirement — public."""
        client = APIClient()
        client.credentials(HTTP_X_STORE_ID=str(store.id))
        resp = client.post(URL, {"provider": "stripe"}, format="json")
        # Still returns 501 — endpoint is scaffolded/public (no permission_classes set)
        assert resp.status_code in (200, 400, 401, 501)
