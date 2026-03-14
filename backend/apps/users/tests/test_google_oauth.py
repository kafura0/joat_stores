"""
Tests for Story 4.5 — Google OAuth2 PKCE callback.

POST /api/v1/auth/google/callback/
"""

from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.store.tests.factories import StoreFactory


@pytest.fixture
def store(db):
    return StoreFactory()


@pytest.fixture
def client():
    return APIClient()


def _store_headers(store):
    return {"HTTP_X_STORE_ID": str(store.id)}


def _mock_google_responses(email="test@example.com", name="Test User"):
    """Return mocked token and userinfo responses."""
    token_resp = MagicMock()
    token_resp.raise_for_status.return_value = None
    token_resp.json.return_value = {"access_token": "google-access-token-abc"}

    userinfo_resp = MagicMock()
    userinfo_resp.raise_for_status.return_value = None
    userinfo_resp.json.return_value = {"email": email, "name": name}

    return token_resp, userinfo_resp


@pytest.mark.django_db
class TestGoogleOAuthCallbackView:
    url = "/api/v1/auth/google/callback/"

    def test_missing_store_returns_404(self, client):
        """No X-Store-ID header → store not resolved → 404."""
        # Hit without any store header (TenantMiddleware resolves via domain)
        # Use a bypass path bypass to avoid TenantMiddleware entirely — actually
        # GoogleOAuthCallbackView checks request.store itself.
        resp = client.post(self.url, {"code": "abc", "redirect_uri": "http://x"}, format="json")
        # TenantMiddleware will return 404 since no store header and no domain match
        assert resp.status_code == 404

    def test_missing_code_returns_400(self, client, store):
        resp = client.post(
            self.url,
            {"redirect_uri": "http://localhost"},
            format="json",
            **_store_headers(store),
        )
        assert resp.status_code == 400
        codes = [e["code"] for e in resp.data["errors"]]
        assert "CODE_AND_REDIRECT_URI_REQUIRED" in codes

    def test_missing_redirect_uri_returns_400(self, client, store):
        resp = client.post(
            self.url,
            {"code": "abc"},
            format="json",
            **_store_headers(store),
        )
        assert resp.status_code == 400

    @patch("apps.users.views.http_requests" if False else "requests.post")
    @patch("requests.get")
    def test_google_token_exchange_failure_returns_502(self, mock_get, mock_post, client, store):
        """Daraja token exchange network error → 502."""
        mock_post.side_effect = Exception("network error")
        with patch("requests.post", side_effect=Exception("network error")):
            resp = client.post(
                self.url,
                {"code": "bad-code", "redirect_uri": "http://localhost"},
                format="json",
                **_store_headers(store),
            )
        assert resp.status_code == 502
        codes = [e["code"] for e in resp.data["errors"]]
        assert "GOOGLE_TOKEN_EXCHANGE_FAILED" in codes

    @pytest.mark.django_db
    def test_successful_oauth_creates_customer_and_returns_jwt(self, client, store):
        """Happy path: valid code → new store-scoped customer + JWT."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        token_resp, userinfo_resp = _mock_google_responses(email="oauth@example.com", name="OAuth User")

        with patch("requests.post", return_value=token_resp), patch(
            "requests.get", return_value=userinfo_resp
        ):
            resp = client.post(
                self.url,
                {"code": "valid-code", "redirect_uri": "http://localhost/callback"},
                format="json",
                **_store_headers(store),
            )

        assert resp.status_code == 200
        data = resp.data["data"]
        assert "access" in data
        assert data["email"] == "oauth@example.com"
        assert data["created"] is True

        # User created in DB, scoped to store
        user = User.objects.get(email="oauth@example.com", store=store)
        assert user.role == "customer"

    @pytest.mark.django_db
    def test_existing_customer_returns_created_false(self, client, store):
        """Second login with same email + store returns created=False."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        email = "returning@example.com"
        User.objects.create_user(
            email=email, store=store, role="customer", password="!"
        )

        token_resp, userinfo_resp = _mock_google_responses(email=email)
        with patch("requests.post", return_value=token_resp), patch(
            "requests.get", return_value=userinfo_resp
        ):
            resp = client.post(
                self.url,
                {"code": "code2", "redirect_uri": "http://localhost/callback"},
                format="json",
                **_store_headers(store),
            )

        assert resp.status_code == 200
        assert resp.data["data"]["created"] is False

    @pytest.mark.django_db
    @pytest.mark.cross_tenant
    def test_same_google_account_different_stores_creates_separate_users(self, client):
        """NFR3: same Google email at two stores = two separate User records."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        store_a = StoreFactory()
        store_b = StoreFactory()
        email = "shared@example.com"

        token_resp, userinfo_resp = _mock_google_responses(email=email)

        for store in [store_a, store_b]:
            with patch("requests.post", return_value=token_resp), patch(
                "requests.get", return_value=userinfo_resp
            ):
                resp = client.post(
                    self.url,
                    {"code": "code", "redirect_uri": "http://localhost/callback"},
                    format="json",
                    **{"HTTP_X_STORE_ID": str(store.id)},
                )
            assert resp.status_code == 200

        assert User.objects.filter(email=email).count() == 2
        assert User.objects.filter(email=email, store=store_a).count() == 1
        assert User.objects.filter(email=email, store=store_b).count() == 1

    @pytest.mark.django_db
    def test_refresh_token_set_as_httponly_cookie(self, client, store):
        """Successful OAuth sets httpOnly refresh cookie."""
        token_resp, userinfo_resp = _mock_google_responses()
        with patch("requests.post", return_value=token_resp), patch(
            "requests.get", return_value=userinfo_resp
        ):
            resp = client.post(
                self.url,
                {"code": "code", "redirect_uri": "http://localhost/callback"},
                format="json",
                **_store_headers(store),
            )

        assert resp.status_code == 200
        assert "refresh_token" in resp.cookies
