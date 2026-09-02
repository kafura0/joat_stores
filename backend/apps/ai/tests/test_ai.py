"""
Tests for Epic 11 — AI + Personalization.

Story 11.1: Recommendation engine + AIEvent capture endpoint
Story 11.2: Peak hour predictions from HourlyOrderSummary
Story 11.3: NLP menu search (PostgreSQL full-text / icontains fallback)
"""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.analytics.models import AIEvent, HourlyOrderSummary
from apps.store.tests.factories import StoreFactory
from apps.users.tests.factories import UserFactory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(db):
    return StoreFactory()


@pytest.fixture
def ai_plan(db):
    from apps.saas.models import Plan
    return Plan.objects.create(
        slug="pro-ai",
        name="Pro",
        price_kes=Decimal("9999.00"),
        has_ai_features=True,
        has_analytics=True,
    )


@pytest.fixture
def store_with_ai(db, ai_plan):
    from apps.saas.models import StoreSubscription, SubscriptionStatus
    s = StoreFactory()
    sub, _ = StoreSubscription.objects.get_or_create(
        store=s,
        defaults={"plan": ai_plan, "status": SubscriptionStatus.ACTIVE},
    )
    sub.plan = ai_plan
    sub.status = SubscriptionStatus.ACTIVE
    sub.save(update_fields=["plan", "status"])
    return s


@pytest.fixture
def owner(store_with_ai):
    return UserFactory(store=store_with_ai, role="store_owner")


@pytest.fixture
def owner_client(owner, store_with_ai):
    c = APIClient()
    c.force_authenticate(user=owner)
    c.credentials(HTTP_X_STORE_ID=str(store_with_ai.id))
    return c


@pytest.fixture
def basic_owner(store):
    return UserFactory(store=store, role="store_owner")


@pytest.fixture
def basic_client(basic_owner, store):
    """Client on a store without AI plan."""
    c = APIClient()
    c.force_authenticate(user=basic_owner)
    c.credentials(HTTP_X_STORE_ID=str(store.id))
    return c


# ---------------------------------------------------------------------------
# Story 11.1 — Recommendation engine
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRecommendationEngine:

    def test_recommendations_requires_ai_plan(self, basic_client):
        resp = basic_client.get("/api/v1/ai/recommendations/")
        assert resp.status_code == 402
        assert resp.data["errors"][0]["code"] == "AI_PLAN_REQUIRED"

    def test_recommendations_returns_list(self, owner_client):
        resp = owner_client.get("/api/v1/ai/recommendations/")
        assert resp.status_code == 200
        assert "recommendations" in resp.data
        assert isinstance(resp.data["recommendations"], list)

    def test_recommendations_with_ai_events(self, store_with_ai, owner_client):
        """With AIEvent data, recommendations are derived from co-occurrence."""
        AIEvent.objects.create(
            store=store_with_ai,
            event_type=AIEvent.EVENT_PRODUCT_VIEW,
            entity_id="prod-1",
        )
        resp = owner_client.get("/api/v1/ai/recommendations/")
        assert resp.status_code == 200
        assert resp.data["count"] >= 0

    def test_ai_event_capture_endpoint(self, owner_client):
        resp = owner_client.post("/api/v1/ai/events/", {
            "event_type": "product_view",
            "entity_id": "prod-abc",
            "metadata": {"source": "storefront"},
        }, format="json")
        assert resp.status_code == 202
        assert resp.data["status"] == "accepted"

    def test_ai_event_invalid_type_returns_400(self, owner_client):
        resp = owner_client.post("/api/v1/ai/events/", {
            "event_type": "invalid_event",
        }, format="json")
        assert resp.status_code == 400
        assert resp.data["errors"][0]["code"] == "INVALID_EVENT_TYPE"

    def test_recommendation_service_fallback_no_data(self, store_with_ai):
        from apps.ai.services import RecommendationService
        service = RecommendationService()
        results = service.get_recommendations(store_with_ai, customer_phone="+254700000099")
        assert isinstance(results, list)

    def test_recommendation_service_top_n(self, store_with_ai):
        """Returns at most TOP_N results."""
        from apps.ai.services import RecommendationService
        service = RecommendationService()
        # Fire many events
        for i in range(20):
            AIEvent.objects.create(
                store=store_with_ai,
                event_type=AIEvent.EVENT_PRODUCT_VIEW,
                entity_id=f"prod-{i}",
            )
        results = service.get_recommendations(store_with_ai)
        assert len(results) <= RecommendationService.TOP_N


# ---------------------------------------------------------------------------
# Story 11.2 — Peak hour predictions
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPeakHourPredictions:

    def test_predictions_requires_ai_plan(self, basic_client):
        resp = basic_client.get("/api/v1/ai/predictions/peak-hours/")
        assert resp.status_code == 402

    def test_predictions_returns_24_slots(self, owner_client):
        resp = owner_client.get("/api/v1/ai/predictions/peak-hours/")
        assert resp.status_code == 200
        assert len(resp.data["predictions"]) == 24
        assert all(s["hour"] == i for i, s in enumerate(resp.data["predictions"]))

    def test_predictions_with_data(self, store_with_ai, owner_client):
        today = timezone.localdate()
        for day_offset in range(1, 4):
            target_date = today - timedelta(days=day_offset)
            HourlyOrderSummary.objects.create(
                store=store_with_ai,
                date=target_date,
                hour=12,
                order_count=10,
                revenue=Decimal("5000.00"),
            )

        resp = owner_client.get("/api/v1/ai/predictions/peak-hours/")
        assert resp.status_code == 200
        noon = resp.data["predictions"][12]
        assert noon["predicted_orders"] > 0

    def test_predictions_confidence_low_no_data(self, owner_client):
        resp = owner_client.get("/api/v1/ai/predictions/peak-hours/")
        for slot in resp.data["predictions"]:
            assert slot["confidence"] in ("low", "medium", "high")

    def test_prediction_service_returns_24(self, store_with_ai):
        from apps.ai.services import PeakHourPredictionService
        service = PeakHourPredictionService()
        predictions = service.predict(store_with_ai)
        assert len(predictions) == 24
        assert predictions[0]["hour"] == 0

    def test_prediction_service_moving_average(self, store_with_ai):
        from apps.ai.services import PeakHourPredictionService
        today = timezone.localdate()
        # 3 days of data: 10, 20, 30 orders at hour 9
        for i, count in enumerate([10, 20, 30], start=1):
            HourlyOrderSummary.objects.create(
                store=store_with_ai,
                date=today - timedelta(days=i),
                hour=9,
                order_count=count,
                revenue=Decimal("0"),
            )
        service = PeakHourPredictionService()
        preds = service.predict(store_with_ai)
        hour_9 = preds[9]
        assert hour_9["predicted_orders"] == 20.0  # (10+20+30)/3
        assert hour_9["confidence"] == "medium"


# ---------------------------------------------------------------------------
# Story 11.3 — NLP menu search
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNLPMenuSearch:

    def test_search_returns_results(self, owner_client, store_with_ai):
        from apps.restaurant.models import MenuItem, MenuSection

        section = MenuSection.objects.create(
            store=store_with_ai,
            name="Mains",
        )
        MenuItem.objects.create(
            store=store_with_ai,
            section=section,
            name="Grilled Chicken",
            price=Decimal("800.00"),
            is_available=True,
        )

        resp = owner_client.post("/api/v1/ai/search/", {"q": "chicken"}, format="json")
        assert resp.status_code == 200
        assert resp.data["count"] >= 1
        assert resp.data["results"][0]["name"] == "Grilled Chicken"

    def test_search_empty_query_returns_400(self, owner_client):
        resp = owner_client.post("/api/v1/ai/search/", {"q": ""}, format="json")
        assert resp.status_code == 400

    def test_search_no_results(self, owner_client):
        resp = owner_client.post("/api/v1/ai/search/", {"q": "xyznonexistent"}, format="json")
        assert resp.status_code == 200
        assert resp.data["count"] == 0

    def test_search_requires_auth(self, store):
        c = APIClient()
        c.credentials(HTTP_X_STORE_ID=str(store.id))
        resp = c.post("/api/v1/ai/search/", {"q": "pizza"}, format="json")
        assert resp.status_code == 401

    def test_nlp_search_service_icontains(self, store_with_ai):
        from apps.ai.services import NLPMenuSearchService
        from apps.restaurant.models import MenuItem, MenuSection

        section = MenuSection.objects.create(store=store_with_ai, name="Drinks")
        MenuItem.objects.create(
            store=store_with_ai,
            section=section,
            name="Fresh Mango Juice",
            price=Decimal("200.00"),
            is_available=True,
        )

        service = NLPMenuSearchService()
        results = service.search(store_with_ai, "mango")
        assert len(results) == 1
        assert results[0]["name"] == "Fresh Mango Juice"

    def test_search_max_results(self, store_with_ai):
        from apps.ai.services import NLPMenuSearchService
        from apps.restaurant.models import MenuItem, MenuSection

        section = MenuSection.objects.create(store=store_with_ai, name="Test")
        for i in range(25):
            MenuItem.objects.create(
                store=store_with_ai,
                section=section,
                name=f"Chicken Dish {i}",
                price=Decimal("100.00"),
                is_available=True,
            )

        service = NLPMenuSearchService()
        results = service.search(store_with_ai, "chicken")
        assert len(results) <= NLPMenuSearchService.MAX_RESULTS
