"""
Tests for Epic 12 — Production Hardening.

Story 12.3: Security headers (OWASP)
Story 12.4: Request ID correlation tracing
Story 12.5: PWA offline inventory snapshot
Story 12.6: CSV data export
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.store.tests.factories import StoreFactory
from apps.users.tests.factories import UserFactory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(db):
    return StoreFactory()


@pytest.fixture
def owner(store):
    return UserFactory(store=store, role="store_owner")


@pytest.fixture
def owner_client(owner, store):
    c = APIClient()
    c.force_authenticate(user=owner)
    c.credentials(HTTP_X_STORE_ID=str(store.id))
    return c


# ---------------------------------------------------------------------------
# Story 12.3 — Security headers
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSecurityHeaders:

    def test_csp_header_not_set(self, owner_client):
        """CSP is intentionally omitted — it blocks cross-origin API calls from Vercel frontends."""
        resp = owner_client.get("/api/v1/saas/plans/")
        assert "Content-Security-Policy" not in resp

    def test_x_content_type_options_header(self, owner_client):
        resp = owner_client.get("/api/v1/saas/plans/")
        assert resp["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options_deny(self, owner_client):
        resp = owner_client.get("/api/v1/saas/plans/")
        assert resp["X-Frame-Options"] == "DENY"

    def test_referrer_policy_header(self, owner_client):
        resp = owner_client.get("/api/v1/saas/plans/")
        assert resp["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_permissions_policy_header(self, owner_client):
        resp = owner_client.get("/api/v1/saas/plans/")
        assert "camera=()" in resp["Permissions-Policy"]


# ---------------------------------------------------------------------------
# Story 12.4 — Request ID correlation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRequestIDMiddleware:

    def test_request_id_echoed_in_response(self, owner_client):
        resp = owner_client.get("/api/v1/saas/plans/", HTTP_X_REQUEST_ID="test-uuid-12345")
        assert resp["X-Request-ID"] == "test-uuid-12345"

    def test_request_id_generated_if_absent(self, owner_client):
        resp = owner_client.get("/api/v1/saas/plans/")
        assert "X-Request-ID" in resp
        assert len(resp["X-Request-ID"]) == 36  # UUID4 format


# ---------------------------------------------------------------------------
# Story 12.5 — PWA offline inventory snapshot
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOfflineInventorySnapshot:

    def test_snapshot_returns_products(self, owner_client, store):
        from apps.product.models import Product, ProductStatus
        Product.objects.create(
            store=store,
            name="Test Product",
            slug="test-product",
            base_price=Decimal("500.00"),
            status=ProductStatus.ACTIVE,
        )
        resp = owner_client.get("/api/v1/store/offline-snapshot/")
        assert resp.status_code == 200
        assert "products" in resp.data
        assert resp.data["product_count"] >= 1
        assert resp.data["products"][0]["name"] == "Test Product"

    def test_snapshot_includes_generated_at(self, owner_client):
        resp = owner_client.get("/api/v1/store/offline-snapshot/")
        assert "generated_at" in resp.data

    def test_snapshot_only_active_products(self, owner_client, store):
        from apps.product.models import Product, ProductStatus
        Product.objects.create(
            store=store, name="Inactive", slug="inactive-prod",
            base_price=Decimal("100.00"), status=ProductStatus.DRAFT,
        )
        resp = owner_client.get("/api/v1/store/offline-snapshot/")
        names = [p["name"] for p in resp.data["products"]]
        assert "Inactive" not in names

    def test_snapshot_no_auth_required(self, store):
        """Service worker fetches this without auth."""
        c = APIClient()
        c.credentials(HTTP_X_STORE_ID=str(store.id))
        resp = c.get("/api/v1/store/offline-snapshot/")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Story 12.6 — CSV data export
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCSVExport:

    def test_csv_export_returns_file(self, owner_client, store):
        from apps.analytics.models import DailyRevenueSummary
        from django.utils import timezone
        from datetime import timedelta

        DailyRevenueSummary.objects.create(
            store=store,
            date=timezone.localdate() - timedelta(days=1),
            total_revenue=Decimal("5000.00"),
            order_count=10,
            aov=Decimal("500.00"),
            amount_usd=Decimal("39.00"),
        )
        resp = owner_client.get("/api/v1/analytics/export/csv/")
        assert resp.status_code == 200
        assert resp["Content-Type"] == "text/csv"
        assert "Content-Disposition" in resp

    def test_csv_contains_data_rows(self, owner_client, store):
        from apps.analytics.models import DailyRevenueSummary
        from django.utils import timezone
        from datetime import timedelta
        import io

        DailyRevenueSummary.objects.create(
            store=store,
            date=timezone.localdate() - timedelta(days=2),
            total_revenue=Decimal("8000.00"),
            order_count=8,
        )
        resp = owner_client.get("/api/v1/analytics/export/csv/")
        content = b"".join(resp.streaming_content).decode()
        assert "total_revenue_kes" in content  # header row
        assert "8000.00" in content

    def test_csv_invalid_date_returns_400(self, owner_client):
        resp = owner_client.get("/api/v1/analytics/export/csv/?from_date=not-a-date")
        assert resp.status_code == 400

    def test_csv_requires_auth(self, store):
        c = APIClient()
        c.credentials(HTTP_X_STORE_ID=str(store.id))
        resp = c.get("/api/v1/analytics/export/csv/")
        assert resp.status_code == 401
