"""
Tests for Story 2.6 — Card payments (Stripe PaymentIntents).

POST /api/v1/payments/card/initiate/
"""

from unittest.mock import patch

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
class TestCardPaymentInitiate:

    def test_stripe_success(self, auth_client):
        with patch("apps.payment.services.stripe.PaymentIntent.create") as mock:
            mock.return_value.id = "pi_123"
            mock.return_value.client_secret = "pi_123_secret_abc"
            resp = auth_client.post(
                URL,
                {"provider": "stripe", "amount": "1500.00", "reference": "ORD-001"},
                format="json",
            )
        assert resp.status_code == 200
        assert "client_secret" in resp.data
        assert resp.data["amount"] == "1500.00"
        assert resp.data["currency"] == "kes"

    def test_requires_amount(self, auth_client):
        resp = auth_client.post(URL, {"provider": "stripe", "reference": "ORD-001"}, format="json")
        assert resp.status_code == 400
        assert resp.data["errors"][0]["code"] == "AMOUNT_REQUIRED"

    def test_requires_reference(self, auth_client):
        resp = auth_client.post(URL, {"provider": "stripe", "amount": "500"}, format="json")
        assert resp.status_code == 400
        assert resp.data["errors"][0]["code"] == "REFERENCE_REQUIRED"

    def test_invalid_provider_returns_400(self, auth_client):
        resp = auth_client.post(URL, {"provider": "flutterwave", "amount": "500", "reference": "ORD-002"}, format="json")
        assert resp.status_code == 400
        codes = [e["code"] for e in resp.data["errors"]]
        assert "INVALID_PROVIDER" in codes

    def test_unauthenticated_returns_401(self, store):
        client = APIClient()
        client.credentials(HTTP_X_STORE_ID=str(store.id))
        resp = client.post(URL, {"provider": "stripe", "amount": "500", "reference": "ORD-003"}, format="json")
        assert resp.status_code == 401


@pytest.mark.django_db
class TestCardPaymentWebhook:

    def test_stripe_webhook_invalid_signature(self, auth_client):
        client = APIClient()
        resp = client.post(
            "/api/v1/payments/stripe-webhook/",
            {"type": "payment_intent.succeeded", "data": {"object": {"id": "pi_123"}}},
            format="json",
            HTTP_STRIPE_SIGNATURE="bad_sig",
        )
        assert resp.status_code == 400
        assert "signature" in resp.data.get("error", "").lower()
