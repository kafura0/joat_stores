"""
Tests for Epic 9 — SaaS Plans + Subscription Management.

Story 9.1: Plan model — pricing, feature flags, resource limits
Story 9.2: StoreSubscription lifecycle — state machine, period tracking
Story 9.3: M-Pesa renewal — STK Push initiation, signal activation
Story 9.4: Plan limit enforcement — max_products, max_orders_per_month
Story 9.5: AI scaffold — 501 endpoints
Story 9.7: Automated suspension + PII anonymisation tasks
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.saas.models import (
    InvalidSubscriptionTransition,
    Plan,
    PlanLimitExceeded,
    StoreSubscription,
    SubscriptionStatus,
    check_monthly_order_limit,
    check_product_limit,
)
from apps.store.tests.factories import StoreFactory
from apps.users.tests.factories import UserFactory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def free_plan(db):
    return Plan.objects.create(
        slug="free",
        name="Free",
        price_kes=Decimal("0.00"),
        max_products=10,
        max_orders_per_month=50,
        has_analytics=False,
        has_qr_codes=True,
    )


@pytest.fixture
def growth_plan(db):
    return Plan.objects.create(
        slug="growth",
        name="Growth",
        price_kes=Decimal("4999.00"),
        billing_cycle="monthly",
        max_products=500,
        max_orders_per_month=None,  # unlimited
        has_analytics=True,
        has_qr_codes=True,
        has_ai_features=True,
    )


@pytest.fixture
def store(db):
    return StoreFactory()


@pytest.fixture
def subscription(store, free_plan):
    sub, _ = StoreSubscription.objects.get_or_create(
        store=store,
        defaults={"plan": free_plan, "status": SubscriptionStatus.TRIAL},
    )
    sub.plan = free_plan
    sub.save(update_fields=["plan"])
    return sub


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


# ---------------------------------------------------------------------------
# Story 9.1 — Plan model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPlanModel:

    def test_plan_created_with_defaults(self, free_plan):
        assert free_plan.slug == "free"
        assert free_plan.price_kes == Decimal("0.00")
        assert free_plan.trial_days == 14
        assert free_plan.has_qr_codes is True
        assert free_plan.has_analytics is False

    def test_plan_slug_unique(self, free_plan):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            Plan.objects.create(slug="free", name="Another Free", price_kes=Decimal("0.00"))

    def test_plan_ordering_by_price(self, free_plan, growth_plan):
        plans = list(Plan.objects.filter(slug__in=["free", "growth"]))
        assert plans[0].price_kes < plans[1].price_kes

    def test_plan_feature_flags(self, growth_plan):
        assert growth_plan.has_analytics is True
        assert growth_plan.has_ai_features is True

    def test_plan_list_api_returns_public_plans(self, owner_client, free_plan, growth_plan):
        resp = owner_client.get("/api/v1/saas/plans/")
        assert resp.status_code == 200
        slugs = [p["slug"] for p in resp.data]
        assert "free" in slugs
        assert "growth" in slugs

    def test_platform_admin_can_create_plan(self, admin_client):
        resp = admin_client.post("/api/v1/saas/plans/", {
            "slug": "pro",
            "name": "Pro",
            "price_kes": "9999.00",
            "billing_cycle": "monthly",
            "has_analytics": True,
            "has_ai_features": True,
        }, format="json")
        assert resp.status_code == 201
        assert resp.data["slug"] == "pro"

    def test_store_owner_cannot_create_plan(self, owner_client):
        resp = owner_client.post("/api/v1/saas/plans/", {
            "slug": "owner-plan", "name": "Owner", "price_kes": "0.00",
        }, format="json")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Story 9.2 — StoreSubscription lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSubscriptionLifecycle:

    def test_subscription_starts_as_trial(self, subscription):
        assert subscription.status == SubscriptionStatus.TRIAL

    def test_trial_to_active_transition(self, subscription):
        subscription.transition_status(SubscriptionStatus.ACTIVE)
        assert subscription.status == SubscriptionStatus.ACTIVE
        assert subscription.past_due_since is None

    def test_active_to_past_due_sets_date(self, subscription):
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.save(update_fields=["status"])
        subscription.transition_status(SubscriptionStatus.PAST_DUE)
        assert subscription.status == SubscriptionStatus.PAST_DUE
        assert subscription.past_due_since == timezone.localdate()

    def test_invalid_transition_raises(self, subscription):
        with pytest.raises(InvalidSubscriptionTransition):
            subscription.transition_status(SubscriptionStatus.SUSPENDED)

    def test_cancelled_is_terminal(self, subscription):
        subscription.transition_status(SubscriptionStatus.ACTIVE)
        subscription.transition_status(SubscriptionStatus.CANCELLED)
        with pytest.raises(InvalidSubscriptionTransition):
            subscription.transition_status(SubscriptionStatus.ACTIVE)

    def test_is_expired_false_when_no_period_end(self, subscription):
        assert subscription.is_expired is False

    def test_is_expired_true_when_past_end(self, subscription):
        subscription.period_end = timezone.localdate() - timedelta(days=1)
        assert subscription.is_expired is True

    def test_days_until_expiry_none_when_no_period(self, subscription):
        assert subscription.days_until_expiry is None

    def test_days_until_expiry_calculation(self, subscription):
        subscription.period_end = timezone.localdate() + timedelta(days=5)
        assert subscription.days_until_expiry == 5

    def test_renewal_amount_is_plan_price(self, subscription, free_plan):
        assert subscription.renewal_amount_kes == free_plan.price_kes

    def test_subscription_api_returns_plan_details(self, owner_client, subscription):
        resp = owner_client.get("/api/v1/saas/subscription/")
        assert resp.status_code == 200
        assert resp.data["status"] == "trial"
        assert resp.data["plan"]["slug"] == "free"

    def test_platform_admin_can_list_subscriptions(self, admin_client, subscription):
        resp = admin_client.get("/api/v1/platform/subscriptions/")
        assert resp.status_code == 200
        assert len(resp.data) >= 1

    def test_platform_admin_can_transition_subscription(self, admin_client, subscription):
        resp = admin_client.patch(
            f"/api/v1/platform/subscriptions/{subscription.id}/",
            {"status": "active"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["status"] == "active"

    def test_store_owner_cannot_access_platform_subscriptions(self, owner_client, subscription):
        resp = owner_client.get("/api/v1/platform/subscriptions/")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Story 9.3 — M-Pesa renewal
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSubscriptionRenewal:

    def test_renew_free_plan_returns_400(self, owner_client, subscription):
        # Free plan → renewal_amount_kes == 0
        resp = owner_client.post("/api/v1/saas/subscription/renew/", {"phone": "+254700000001"}, format="json")
        assert resp.status_code == 400
        assert resp.data["errors"][0]["code"] == "FREE_PLAN"

    def test_renew_paid_plan_initiates_stk_push(self, owner_client, subscription, growth_plan):
        subscription.plan = growth_plan
        subscription.save(update_fields=["plan"])

        mock_tx = MagicMock()
        mock_tx.id = "tx-123"
        with patch("apps.payment.services.initiate_payment", return_value=mock_tx) as mock_pay:
            resp = owner_client.post(
                "/api/v1/saas/subscription/renew/",
                {"phone": "+254700000001"},
                format="json",
            )
        assert resp.status_code == 202
        mock_pay.assert_called_once()
        call_kwargs = mock_pay.call_args.kwargs
        assert call_kwargs["reference"].startswith("subscription-")

    def test_payment_signal_activates_subscription(self, subscription, growth_plan):
        """payment_confirmed with ref 'subscription-{store_id}' → activates subscription."""
        from apps.payment.tests.factories import MpesaTransactionFactory

        subscription.plan = growth_plan
        subscription.status = SubscriptionStatus.PAST_DUE
        subscription.save(update_fields=["plan", "status"])

        from apps.saas.apps import _handle_subscription_payment_confirmed

        txn = MpesaTransactionFactory(
            store=subscription.store,
            reference=f"subscription-{subscription.store_id}",
        )

        _handle_subscription_payment_confirmed(sender=None, transaction=txn)

        subscription.refresh_from_db()
        assert subscription.status == SubscriptionStatus.ACTIVE
        assert subscription.period_end is not None

    def test_payment_signal_extends_active_period(self, subscription, growth_plan):
        from apps.payment.tests.factories import MpesaTransactionFactory

        today = timezone.localdate()
        subscription.plan = growth_plan
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.period_start = today
        subscription.period_end = today + timedelta(days=10)
        subscription.save(update_fields=["plan", "status", "period_start", "period_end"])

        from apps.saas.apps import _handle_subscription_payment_confirmed

        txn = MpesaTransactionFactory(
            store=subscription.store,
            reference=f"subscription-{subscription.store_id}",
        )

        _handle_subscription_payment_confirmed(sender=None, transaction=txn)

        subscription.refresh_from_db()
        # New period starts day after current period_end
        expected_start = today + timedelta(days=11)
        assert subscription.period_start == expected_start


# ---------------------------------------------------------------------------
# Story 9.4 — Plan limit enforcement
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPlanLimits:

    def test_product_limit_not_raised_when_unlimited(self, store, subscription, growth_plan):
        subscription.plan = growth_plan
        subscription.save(update_fields=["plan"])
        # max_products is None for growth_plan — should not raise
        check_product_limit(store)  # No exception

    def test_product_limit_raised_at_cap(self, store, subscription, free_plan, db):
        """Free plan cap is 10 products. Simulate store at cap."""
        from apps.product.models import Product

        # Create 10 products to hit the cap
        for i in range(10):
            Product.objects.create(
                store=store,
                name=f"Product {i}",
                is_available=True,
            )

        with pytest.raises(PlanLimitExceeded) as exc_info:
            check_product_limit(store)
        assert exc_info.value.resource == "max_products"
        assert exc_info.value.limit == 10

    def test_monthly_order_limit_not_raised_when_no_plan(self, store, db):
        # No subscription → no limit
        StoreSubscription.objects.filter(store=store).delete()
        check_monthly_order_limit(store)  # No exception


# ---------------------------------------------------------------------------
# Story 9.5 — AI scaffold (501 endpoints)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAIScaffold:

    def test_recommendations_returns_501(self, owner_client):
        """Without AI plan, returns 402 (AI_PLAN_REQUIRED)."""
        resp = owner_client.get("/api/v1/ai/recommendations/")
        assert resp.status_code == 402
        assert resp.data["errors"][0]["code"] == "AI_PLAN_REQUIRED"

    def test_peak_hour_predictions_returns_501(self, owner_client):
        """Without AI plan, returns 402 (AI_PLAN_REQUIRED)."""
        resp = owner_client.get("/api/v1/ai/predictions/peak-hours/")
        assert resp.status_code == 402
        assert resp.data["errors"][0]["code"] == "AI_PLAN_REQUIRED"

    def test_nlp_search_returns_501(self, owner_client):
        """NLP search is available on all plans (no AI plan required)."""
        resp = owner_client.post("/api/v1/ai/search/", {"q": "burgers"}, format="json")
        assert resp.status_code == 200
        assert "results" in resp.data

    def test_ai_endpoints_require_auth(self, store):
        c = APIClient()
        c.credentials(HTTP_X_STORE_ID=str(store.id))
        resp = c.get("/api/v1/ai/recommendations/")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Story 9.7 — Auto-suspension + PII anonymisation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAutoSuspensionAndPII:

    def test_suspend_past_due_subscriptions_task(self, subscription):
        from apps.saas.tasks import suspend_past_due_subscriptions

        subscription.status = SubscriptionStatus.PAST_DUE
        subscription.past_due_since = timezone.localdate() - timedelta(days=8)
        subscription.save(update_fields=["status", "past_due_since"])

        suspend_past_due_subscriptions()

        subscription.refresh_from_db()
        assert subscription.status == SubscriptionStatus.SUSPENDED
        assert subscription.suspended_at is not None

    def test_suspend_does_not_affect_recent_past_due(self, subscription):
        from apps.saas.tasks import suspend_past_due_subscriptions

        subscription.status = SubscriptionStatus.PAST_DUE
        subscription.past_due_since = timezone.localdate() - timedelta(days=3)  # Only 3 days
        subscription.save(update_fields=["status", "past_due_since"])

        suspend_past_due_subscriptions()

        subscription.refresh_from_db()
        assert subscription.status == SubscriptionStatus.PAST_DUE  # Unchanged

    def test_anonymise_cancelled_store_pii_task(self, store, subscription):
        from apps.order.models import Order, OrderStatus
        from apps.saas.tasks import anonymise_cancelled_store_pii

        # Create an order with PII
        order = Order.objects.create(
            store=store,
            status=OrderStatus.CONFIRMED,
            total_amount=Decimal("500.00"),
            customer_phone="+254700000001",
            customer_name="John Doe",
            customer_email="john@example.com",
            items_snapshot=[],
            confirmed_at=timezone.now(),
        )

        # Set subscription as cancelled 31 days ago
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = timezone.now() - timedelta(days=31)
        subscription.save(update_fields=["status", "cancelled_at"])

        anonymise_cancelled_store_pii()

        order.refresh_from_db()
        assert order.customer_phone == "ANONYMISED"
        assert order.customer_name == ""
        assert order.customer_email == ""

    def test_anonymise_does_not_touch_recent_cancellation(self, store, subscription):
        from apps.order.models import Order, OrderStatus
        from apps.saas.tasks import anonymise_cancelled_store_pii

        order = Order.objects.create(
            store=store,
            status=OrderStatus.CONFIRMED,
            total_amount=Decimal("500.00"),
            customer_phone="+254700000001",
            items_snapshot=[],
            confirmed_at=timezone.now(),
        )

        # Cancelled only 5 days ago — not due for anonymisation yet
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = timezone.now() - timedelta(days=5)
        subscription.save(update_fields=["status", "cancelled_at"])

        anonymise_cancelled_store_pii()

        order.refresh_from_db()
        assert order.customer_phone == "+254700000001"  # Untouched
