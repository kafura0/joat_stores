"""
Tests for Epic 8 — Merchant Analytics Dashboard.

Story 8.1: DailyRevenueSummary + HourlyOrderSummary pre-aggregated models
Story 8.2: AIEvent append-only enforcement
Story 8.3: Per-store analytics API
Story 8.4: Restaurant analytics
Story 8.5: Bar analytics
Story 8.6: Platform analytics (GMV, unit economics) — platform admin only
Story 8.7: First order milestone
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.analytics.models import (
    AIEvent,
    DailyRevenueSummary,
    HourlyOrderSummary,
    StoreFirstOrderEvent,
    TenantHealthSnapshot,
)
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
def platform_admin(db):
    return UserFactory(role="platform_admin")


@pytest.fixture
def owner_client(owner, store):
    c = APIClient()
    c.force_authenticate(user=owner)
    c.credentials(HTTP_X_STORE_ID=str(store.id))
    return c


@pytest.fixture
def admin_client(platform_admin, store):
    c = APIClient()
    c.force_authenticate(user=platform_admin)
    c.credentials(HTTP_X_STORE_ID=str(store.id))
    return c


@pytest.fixture
def daily_summary(store):
    yesterday = timezone.localdate() - timedelta(days=1)
    return DailyRevenueSummary.objects.create(
        store=store,
        date=yesterday,
        total_revenue=Decimal("15000.00"),
        order_count=10,
        aov=Decimal("1500.00"),
        amount_usd=Decimal("117.00"),
    )


# ---------------------------------------------------------------------------
# Story 8.1 — Pre-aggregated models
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPreAggregatedModels:

    def test_daily_revenue_summary_created(self, store):
        yesterday = timezone.localdate() - timedelta(days=1)
        summary = DailyRevenueSummary.objects.create(
            store=store, date=yesterday,
            total_revenue=Decimal("5000.00"), order_count=5,
            aov=Decimal("1000.00"), amount_usd=Decimal("39.00"),
        )
        assert summary.total_revenue == Decimal("5000.00")

    def test_upsert_is_idempotent(self, store):
        """update_or_create called twice for same date = one record."""
        yesterday = timezone.localdate() - timedelta(days=1)
        for _ in range(2):
            DailyRevenueSummary.objects.update_or_create(
                store=store, date=yesterday,
                defaults={"total_revenue": Decimal("1000.00"), "order_count": 3},
            )
        assert DailyRevenueSummary.objects.filter(store=store, date=yesterday).count() == 1

    def test_hourly_summary_covers_all_hours(self, store):
        today = timezone.localdate()
        for h in range(24):
            HourlyOrderSummary.objects.create(
                store=store, date=today, hour=h,
                order_count=0, revenue=Decimal("0"),
            )
        assert HourlyOrderSummary.objects.filter(store=store, date=today).count() == 24


# ---------------------------------------------------------------------------
# Story 8.2 — AIEvent append-only
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAIEvent:

    def test_create_ai_event(self, store):
        event = AIEvent.objects.create(
            store=store,
            event_type=AIEvent.EVENT_PRODUCT_VIEW,
            entity_id="product-123",
        )
        assert event.pk is not None

    def test_update_ai_event_raises(self, store):
        event = AIEvent.objects.create(
            store=store, event_type=AIEvent.EVENT_CART_ADD, entity_id="variant-1"
        )
        with pytest.raises(ValueError, match="append-only"):
            event.metadata = {"updated": True}
            event.save()

    def test_all_event_types_valid(self, store):
        for event_type, _ in AIEvent.EVENT_TYPE_CHOICES:
            AIEvent.objects.create(store=store, event_type=event_type)
        assert AIEvent.objects.filter(store=store).count() == len(AIEvent.EVENT_TYPE_CHOICES)


# ---------------------------------------------------------------------------
# Story 8.3 — Per-store analytics API
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestStoreSummaryAPI:

    def test_summary_returns_data_from_pre_aggregated_model(self, owner_client, daily_summary):
        resp = owner_client.get("/api/v1/analytics/summary/?date=yesterday")
        assert resp.status_code == 200
        assert resp.data["order_count"] == 10
        assert resp.data["total_revenue"] == "15000.00"

    def test_summary_returns_zeros_when_no_data(self, owner_client, store):
        resp = owner_client.get("/api/v1/analytics/summary/?date=yesterday")
        assert resp.status_code == 200
        assert resp.data["order_count"] == 0
        assert resp.data["total_revenue"] == "0.00"
        assert "pending" in resp.data["note"].lower() or "no data" in resp.data["note"].lower()

    def test_summary_note_mentions_daily_update(self, owner_client, daily_summary):
        resp = owner_client.get("/api/v1/analytics/summary/?date=yesterday")
        assert "00:05" in resp.data["note"] or "daily" in resp.data["note"].lower()


# ---------------------------------------------------------------------------
# Story 8.4 — Restaurant analytics
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRestaurantAnalytics:

    def test_peak_hours_returns_24_slots(self, owner_client):
        resp = owner_client.get("/api/v1/analytics/restaurant/peak-hours/")
        assert resp.status_code == 200
        assert len(resp.data["peak_hours"]) == 24
        assert all(s["hour"] == i for i, s in enumerate(resp.data["peak_hours"]))

    def test_table_turn_rate_no_sessions(self, owner_client):
        resp = owner_client.get("/api/v1/analytics/restaurant/table-turn-rate/")
        assert resp.status_code == 200
        assert resp.data["avg_turn_rate_minutes"] is None


# ---------------------------------------------------------------------------
# Story 8.5 — Bar analytics
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBarAnalytics:

    def test_tab_metrics_no_tabs(self, owner_client):
        resp = owner_client.get("/api/v1/analytics/bar/tab-metrics/")
        assert resp.status_code == 200
        assert resp.data["tab_completion_rate"] is None
        assert resp.data["tabs_opened"] == 0

    def test_occupancy_no_tabs(self, owner_client):
        resp = owner_client.get("/api/v1/analytics/bar/occupancy/")
        assert resp.status_code == 200
        assert resp.data["occupied_days"] == 0


# ---------------------------------------------------------------------------
# Story 8.6 — Platform analytics (platform admin only)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPlatformAnalytics:

    def test_gmv_requires_platform_admin(self, owner_client):
        resp = owner_client.get("/api/v1/platform/analytics/gmv/")
        assert resp.status_code == 403

    def test_gmv_returns_data_for_platform_admin(self, admin_client, daily_summary):
        resp = admin_client.get("/api/v1/platform/analytics/gmv/")
        assert resp.status_code == 200
        assert "total_gmv_kes" in resp.data

    def test_unit_economics_requires_platform_admin(self, owner_client):
        resp = owner_client.get("/api/v1/platform/analytics/unit-economics/")
        assert resp.status_code == 403

    def test_unit_economics_returns_per_tenant_data(self, admin_client, store):
        resp = admin_client.get("/api/v1/platform/analytics/unit-economics/")
        assert resp.status_code == 200
        assert "active_tenants" in resp.data


# ---------------------------------------------------------------------------
# Story 8.7 — First order milestone
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFirstOrderMilestone:

    def test_store_first_order_event_is_unique_per_store(self, store):
        """Only one StoreFirstOrderEvent per store (OneToOneField)."""
        from django.db import IntegrityError

        StoreFirstOrderEvent.objects.create(store=store, first_order_amount=Decimal("500.00"))
        with pytest.raises(IntegrityError):
            StoreFirstOrderEvent.objects.create(store=store, first_order_amount=Decimal("600.00"))

    def test_record_first_order_event_idempotent(self, store, db):
        """Calling the task twice does not create a second record."""
        from apps.analytics.tasks import record_first_order_event

        # Create dummy order
        from apps.order.models import Order, OrderStatus

        order = Order.objects.create(
            store=store,
            status=OrderStatus.CONFIRMED,
            total_amount=Decimal("1000.00"),
            customer_phone="+254700000001",
            items_snapshot=[],
            confirmed_at=timezone.now(),
        )

        # First call
        record_first_order_event(str(store.id), str(order.id))
        assert StoreFirstOrderEvent.objects.filter(store=store).count() == 1

        # Second call — idempotent
        record_first_order_event(str(store.id), str(order.id))
        assert StoreFirstOrderEvent.objects.filter(store=store).count() == 1

    def test_platform_store_first_order_endpoint(self, admin_client, store, db):
        from apps.order.models import Order, OrderStatus

        order = Order.objects.create(
            store=store, status=OrderStatus.CONFIRMED,
            total_amount=Decimal("2500.00"), customer_phone="+254700000001",
            items_snapshot=[], confirmed_at=timezone.now(),
        )
        StoreFirstOrderEvent.objects.create(
            store=store, order=order, first_order_amount=Decimal("2500.00")
        )
        resp = admin_client.get(f"/api/v1/platform/stores/{store.id}/first-order/")
        assert resp.status_code == 200
        assert resp.data["first_order_amount"] == "2500.00"
        assert resp.data["first_order_at"] is not None
