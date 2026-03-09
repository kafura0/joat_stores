"""
Tests for core.middleware.TenantMiddleware.

Tests use Django's RequestFactory to build requests without a live server.
TenantMiddleware.process_request() is called directly.

Cross-tenant tests are named with "cross_tenant" so `pytest -k cross_tenant`
picks them up for the CI enforcement suite (architecture.md#CI Enforcement).
"""

import uuid

from django.test import RequestFactory

import pytest

from apps.store.models import Store, StoreStatus, TenantType
from core.middleware import TenantMiddleware


def make_store(**kwargs):
    """Helper: create a Store with sensible defaults."""
    defaults = {
        "name": "Test Store",
        "slug": f"test-{uuid.uuid4().hex[:8]}",
        "domain": f"test-{uuid.uuid4().hex[:8]}.joat.com",
        "tenant_type": TenantType.RETAIL,
        "status": StoreStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Store.objects.create(**defaults)


@pytest.fixture
def factory():
    return RequestFactory()


@pytest.fixture
def middleware():
    return TenantMiddleware(get_response=lambda r: None)


@pytest.mark.django_db
class TestTenantResolution:
    def test_resolves_store_from_domain(self, factory, middleware):
        """Host header matching store.domain sets request.store (AC2)."""
        store = make_store(domain="techstore.joat.com")
        request = factory.get("/api/v1/products/", HTTP_HOST="techstore.joat.com")
        result = middleware.process_request(request)
        assert result is None  # passes through
        assert request.store == store

    def test_resolves_store_from_x_store_id(self, factory, middleware):
        """X-Store-ID header matching store.id sets request.store (AC3)."""
        store = make_store(domain="hdr.joat.com")
        request = factory.get(
            "/api/v1/products/",
            HTTP_HOST="somehost.joat.com",
            HTTP_X_STORE_ID=str(store.id),
        )
        result = middleware.process_request(request)
        assert result is None
        assert request.store == store

    def test_x_store_id_takes_priority_over_domain(self, factory, middleware):
        """X-Store-ID lookup wins when both header and domain provided."""
        store_by_id = make_store(domain="by-id.joat.com")
        make_store(domain="by-domain.joat.com")
        request = factory.get(
            "/api/v1/products/",
            HTTP_HOST="by-domain.joat.com",
            HTTP_X_STORE_ID=str(store_by_id.id),
        )
        middleware.process_request(request)
        assert request.store == store_by_id

    def test_invalid_x_store_id_falls_back_to_domain(self, factory, middleware):
        """Invalid UUID in X-Store-ID falls back to domain lookup."""
        store = make_store(domain="fallback.joat.com")
        request = factory.get(
            "/api/v1/products/",
            HTTP_HOST="fallback.joat.com",
            HTTP_X_STORE_ID="not-a-uuid",
        )
        middleware.process_request(request)
        assert request.store == store


@pytest.mark.django_db
class TestTenantMiddlewareErrors:
    def test_404_on_unknown_domain(self, factory, middleware):
        """Unknown domain returns 404 before reaching any view (AC4)."""
        request = factory.get("/api/v1/products/", HTTP_HOST="unknown.joat.com")
        response = middleware.process_request(request)
        assert response is not None
        assert response.status_code == 404

    def test_404_response_body_has_errors_key(self, factory, middleware):
        """404 response follows {errors:[...]} envelope."""
        import json

        request = factory.get("/", HTTP_HOST="nobody.joat.com")
        response = middleware.process_request(request)
        data = json.loads(response.content)
        assert "errors" in data
        assert data["errors"][0]["code"] == "NOT_FOUND"

    def test_503_on_suspended_store(self, factory, middleware):
        """Suspended store returns 503 (AC5)."""
        make_store(domain="suspended.joat.com", status=StoreStatus.SUSPENDED)
        request = factory.get("/api/v1/products/", HTTP_HOST="suspended.joat.com")
        response = middleware.process_request(request)
        assert response is not None
        assert response.status_code == 503

    def test_503_response_body_has_errors_key(self, factory, middleware):
        """503 response follows {errors:[...]} envelope."""
        import json

        make_store(domain="susp2.joat.com", status=StoreStatus.SUSPENDED)
        request = factory.get("/", HTTP_HOST="susp2.joat.com")
        response = middleware.process_request(request)
        data = json.loads(response.content)
        assert data["errors"][0]["code"] == "STORE_SUSPENDED"


@pytest.mark.django_db
class TestTenantMiddlewareBypass:
    def test_platform_subdomain_bypass(self, factory, middleware, settings):
        """Platform subdomains skip store resolution, request.store = None (AC6)."""
        settings.PLATFORM_SUBDOMAINS = ["admin.joat.com"]
        request = factory.get("/dashboard/", HTTP_HOST="admin.joat.com")
        result = middleware.process_request(request)
        assert result is None  # passes through
        assert request.store is None

    def test_health_path_bypass(self, factory, middleware, settings):
        """Health check path bypasses store resolution (AC9)."""
        settings.MIDDLEWARE_BYPASS_PATHS = ["/health/"]
        request = factory.get("/health/", HTTP_HOST="unknown.joat.com")
        result = middleware.process_request(request)
        assert result is None  # passes through — no 404
        assert request.store is None

    def test_admin_path_bypass(self, factory, middleware, settings):
        """Django admin path bypasses store resolution (AC9)."""
        settings.MIDDLEWARE_BYPASS_PATHS = ["/health/", "/admin/"]
        request = factory.get("/admin/login/", HTTP_HOST="unknown.joat.com")
        result = middleware.process_request(request)
        assert result is None
        assert request.store is None

    def test_localhost_bypass(self, factory, middleware, settings):
        """localhost in PLATFORM_SUBDOMAINS — used by Docker health check."""
        settings.PLATFORM_SUBDOMAINS = ["localhost", "127.0.0.1"]
        settings.MIDDLEWARE_BYPASS_PATHS = []
        request = factory.get("/api/v1/products/", HTTP_HOST="localhost")
        result = middleware.process_request(request)
        assert result is None
        assert request.store is None


@pytest.mark.django_db
class TestCrossTenantIsolation:
    def test_cross_tenant_isolation_domain_returns_correct_store(
        self, factory, middleware
    ):
        """Each domain resolves to its own store — no cross-tenant leakage."""
        store_a = make_store(name="Store A", domain="store-a.joat.com")
        store_b = make_store(name="Store B", domain="store-b.joat.com")

        request_a = factory.get("/api/v1/products/", HTTP_HOST="store-a.joat.com")
        middleware.process_request(request_a)
        assert request_a.store == store_a
        assert request_a.store != store_b

        request_b = factory.get("/api/v1/products/", HTTP_HOST="store-b.joat.com")
        middleware.process_request(request_b)
        assert request_b.store == store_b
        assert request_b.store != store_a

    def test_cross_tenant_isolation_x_store_id_cannot_access_other_store(
        self, factory, middleware
    ):
        """X-Store-ID resolves to correct store only — no cross-tenant leakage."""
        store_a = make_store(name="Store A", domain="xid-a.joat.com")
        store_b = make_store(name="Store B", domain="xid-b.joat.com")

        # Request with Store A's ID
        request = factory.get(
            "/api/v1/orders/",
            HTTP_HOST="xid-b.joat.com",
            HTTP_X_STORE_ID=str(store_a.id),
        )
        middleware.process_request(request)
        # Must resolve to Store A (from header), NOT Store B (from host)
        assert request.store == store_a
        assert request.store.id != store_b.id
