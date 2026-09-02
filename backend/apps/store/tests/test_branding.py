"""
Tests for Story 1.7: Branding API (GET /api/v1/store/branding/).

Covers:
  - Returns branding fields for an active store
  - Unauthenticated access allowed (AllowAny)
  - Returns HTTP 503 + store_name for suspended store
  - get_or_create StoreSettings + StoreTheme on first access
  - Returns correct defaults when settings/theme not configured
  - Returns 404 if no store resolved by TenantMiddleware
  - Custom branding values (colours, tagline, logo)
"""

import pytest
from rest_framework.test import APIClient

from apps.store.models import Store, StoreSettings, StoreTheme


def make_store(name, domain, status="active"):
    from django.utils.text import slugify

    return Store.objects.create(
        name=name,
        slug=slugify(name),
        domain=domain,
        status=status,
    )


@pytest.mark.django_db
class TestBrandingEndpoint:
    """Test GET /api/v1/store/branding/."""

    def setup_method(self):
        self.client = APIClient()
        self.store = make_store("Nairobi Eats", "eats.joat.com")
        self.url = "/api/v1/store/branding/"

    def _request_with_store(self, store=None):
        """GET with X-Store-ID to simulate TenantMiddleware store resolution."""
        s = store or self.store
        return self.client.get(
            self.url,
            HTTP_X_STORE_ID=str(s.pk),
        )

    def test_returns_200_for_active_store(self):
        resp = self._request_with_store()
        assert resp.status_code == 200, resp.data

    def test_returns_required_fields(self):
        resp = self._request_with_store()
        data = resp.data["data"]
        assert data["store_name"] == "Nairobi Eats"
        assert "logo_url" in data
        assert "tagline" in data
        assert "theme" in data
        assert "primary_color" in data["theme"]
        assert "secondary_color" in data["theme"]
        assert data["currency"] == "KES"
        assert data["country"] == "KE"
        assert data["status"] == "active"

    def test_unauthenticated_access_allowed(self):
        """No auth header — AllowAny, should still return 200."""
        resp = self.client.get(self.url, HTTP_X_STORE_ID=str(self.store.pk))
        assert resp.status_code == 200

    def test_returns_503_for_suspended_store(self):
        """TenantMiddleware passes suspended stores through to branding endpoint
        so the view can return a 503 including store_name for branded error pages."""
        suspended = make_store("Closed Shop", "closed.joat.com", status="suspended")
        resp = self._request_with_store(store=suspended)
        assert resp.status_code == 503

    def test_suspended_response_includes_store_name(self):
        """503 body must include store_name so storefront renders branded page."""
        suspended = make_store("Closed Shop 2", "closed2.joat.com", status="suspended")
        resp = self._request_with_store(store=suspended)
        assert resp.data["data"]["store_name"] == "Closed Shop 2"
        assert resp.data["data"]["status"] == "suspended"

    def test_no_store_returns_404(self):
        """Missing X-Store-ID and unresolvable domain → 404."""
        resp = self.client.get(self.url)
        assert resp.status_code == 404

    def test_creates_storesettings_on_first_access(self):
        """get_or_create: StoreSettings must not exist before first call."""
        assert not StoreSettings.objects.filter(store=self.store).exists()
        self._request_with_store()
        assert StoreSettings.objects.filter(store=self.store).exists()

    def test_creates_storetheme_on_first_access(self):
        assert not StoreTheme.objects.filter(store=self.store).exists()
        self._request_with_store()
        assert StoreTheme.objects.filter(store=self.store).exists()

    def test_returns_default_colors_when_theme_not_configured(self):
        resp = self._request_with_store()
        data = resp.data["data"]
        assert data["theme"]["primary_color"] == "#1a1a1a"
        assert data["theme"]["secondary_color"] == "#6b7280"

    def test_returns_custom_branding_when_configured(self):
        StoreSettings.objects.create(
            store=self.store,
            tagline="Fresh food, fast delivery",
            logo_url="https://cdn.joat.com/logo.webp",
        )
        StoreTheme.objects.create(
            store=self.store,
            primary_color="#e63946",
            secondary_color="#457b9d",
        )
        resp = self._request_with_store()
        data = resp.data["data"]
        assert data["tagline"] == "Fresh food, fast delivery"
        assert data["logo_url"] == "https://cdn.joat.com/logo.webp"
        assert data["theme"]["primary_color"] == "#e63946"
        assert data["theme"]["secondary_color"] == "#457b9d"

    def test_idempotent_get_or_create_on_repeated_calls(self):
        """Multiple calls must not create duplicate settings/theme records."""
        self._request_with_store()
        self._request_with_store()
        self._request_with_store()
        assert StoreSettings.objects.filter(store=self.store).count() == 1
        assert StoreTheme.objects.filter(store=self.store).count() == 1

    def test_cancelled_store_returns_200(self):
        """Cancelled stores return 200 (not suspended — only suspended triggers 503)."""
        cancelled = make_store("Old Shop", "old.joat.com", status="cancelled")
        resp = self._request_with_store(store=cancelled)
        assert resp.status_code == 200
        assert resp.data["data"]["status"] == "cancelled"
