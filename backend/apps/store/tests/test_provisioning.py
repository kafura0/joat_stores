"""
Tests for Story 1.4: Atomic Store Provisioning API.

Covers:
  - Atomic provisioning (Store + StoreSubscription + store_owner User)
  - Domain conflict detection (HTTP 409-equivalent via 400)
  - Rollback on failure (no partial records)
  - Store list endpoint (platform admin only)
  - Status transitions (valid + invalid)
  - StoreSubscription + Plan stubs
"""

import uuid

from django.test import TestCase

import pytest
from rest_framework.test import APIClient

from apps.saas.models import Plan, StoreSubscription, SubscriptionStatus
from apps.store.models import Store, StoreStatus, TenantType
from apps.store.serializers import (
    VALID_STATUS_TRANSITIONS,
    StoreDetailSerializer,
    StoreProvisionSerializer,
    StoreStatusSerializer,
)
from apps.users.models import User

# ---------------------------------------------------------------------------
# Unit tests — serializer validation (no DB needed for some)
# ---------------------------------------------------------------------------


class TestStoreStatusSerializerValidation(TestCase):
    """Test status transition validation logic without DB."""

    def test_valid_transitions_set_is_complete(self):
        expected = {
            ("pending", "active"),
            ("active", "suspended"),
            ("suspended", "cancelled"),
        }
        assert VALID_STATUS_TRANSITIONS == expected


# ---------------------------------------------------------------------------
# Integration tests — require PostgreSQL
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestStoreProvisionSerializer(TestCase):
    """Test atomic provisioning via StoreProvisionSerializer."""

    def test_provision_creates_store_subscription_owner(self):
        data = {
            "name": "Test Shop",
            "domain": "test.joat.com",
            "tenant_type": "retail",
            "owner_email": "owner@test.com",
        }
        serializer = StoreProvisionSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        store = serializer.save()

        # Store created
        assert Store.objects.filter(pk=store.pk).exists()
        assert store.name == "Test Shop"
        assert store.domain == "test.joat.com"
        assert store.tenant_type == "retail"
        assert store.status == "pending"

        # StoreSubscription created with trial status
        sub = StoreSubscription.objects.get(store=store)
        assert sub.status == SubscriptionStatus.TRIAL

        # store_owner User created
        owner = User.objects.get(store=store, role="store_owner")
        assert owner.email == "owner@test.com"
        assert not owner.has_usable_password()

    def test_provision_domain_conflict_returns_error(self):
        Store.objects.create(
            name="Existing",
            slug="existing",
            domain="taken.joat.com",
        )
        data = {
            "name": "New Shop",
            "domain": "taken.joat.com",
            "tenant_type": "retail",
            "owner_email": "owner@new.com",
        }
        serializer = StoreProvisionSerializer(data=data)
        assert not serializer.is_valid()
        assert "domain" in serializer.errors

    def test_provision_generates_unique_slug(self):
        data1 = {
            "name": "My Shop",
            "domain": "shop1.joat.com",
            "tenant_type": "retail",
            "owner_email": "a@test.com",
        }
        data2 = {
            "name": "My Shop",
            "domain": "shop2.joat.com",
            "tenant_type": "retail",
            "owner_email": "b@test.com",
        }
        s1 = StoreProvisionSerializer(data=data1)
        s1.is_valid(raise_exception=True)
        store1 = s1.save()

        s2 = StoreProvisionSerializer(data=data2)
        s2.is_valid(raise_exception=True)
        store2 = s2.save()

        assert store1.slug != store2.slug
        assert store2.slug.startswith("my-shop")

    def test_provision_defaults(self):
        data = {
            "name": "Default Shop",
            "domain": "defaults.joat.com",
            "tenant_type": "restaurant",
            "owner_email": "o@test.com",
        }
        serializer = StoreProvisionSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        store = serializer.save()
        assert store.currency == "KES"
        assert store.country == "KE"
        assert store.timezone == "Africa/Nairobi"
        assert store.payment_methods == []

    def test_provision_all_tenant_types(self):
        for i, tt in enumerate(TenantType.values):
            data = {
                "name": f"Shop {tt}",
                "domain": f"{tt}-{i}.joat.com",
                "tenant_type": tt,
                "owner_email": f"{tt}@test.com",
            }
            s = StoreProvisionSerializer(data=data)
            assert s.is_valid(), s.errors
            store = s.save()
            assert store.tenant_type == tt

    def test_provision_rollback_on_mid_transaction_failure(self):
        """AC2: verify actual DB atomicity — no partial records on mid-tx failure."""
        from unittest.mock import patch as mock_patch

        data = {
            "name": "Rollback Shop",
            "domain": "rollback.joat.com",
            "tenant_type": "retail",
            "owner_email": "rollback@test.com",
        }
        serializer = StoreProvisionSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        # Inject failure after Store is created but before User is created
        with mock_patch.object(
            User.objects,
            "create_user",
            side_effect=Exception("injected failure"),
        ):
            with pytest.raises(Exception, match="injected failure"):
                serializer.save()

        # Verify atomicity: Store AND StoreSubscription must have been rolled back
        assert not Store.objects.filter(domain="rollback.joat.com").exists()
        assert not StoreSubscription.objects.filter(
            store__domain="rollback.joat.com"
        ).exists()


@pytest.mark.django_db
class TestStoreStatusTransitions(TestCase):
    """Test status transition validation."""

    def setUp(self):
        self.store = Store.objects.create(
            name="Status Test",
            slug="status-test",
            domain="status.joat.com",
            status=StoreStatus.PENDING,
        )

    def test_valid_transition_pending_to_active(self):
        serializer = StoreStatusSerializer(
            data={"status": "active"},
            context={"store": self.store},
        )
        assert serializer.is_valid(), serializer.errors

    def test_valid_transition_active_to_suspended(self):
        self.store.status = StoreStatus.ACTIVE
        self.store.save()
        serializer = StoreStatusSerializer(
            data={"status": "suspended"},
            context={"store": self.store},
        )
        assert serializer.is_valid(), serializer.errors

    def test_valid_transition_suspended_to_cancelled(self):
        self.store.status = StoreStatus.SUSPENDED
        self.store.save()
        serializer = StoreStatusSerializer(
            data={"status": "cancelled"},
            context={"store": self.store},
        )
        assert serializer.is_valid(), serializer.errors

    def test_invalid_transition_pending_to_suspended(self):
        serializer = StoreStatusSerializer(
            data={"status": "suspended"},
            context={"store": self.store},
        )
        assert not serializer.is_valid()

    def test_invalid_transition_active_to_pending(self):
        self.store.status = StoreStatus.ACTIVE
        self.store.save()
        serializer = StoreStatusSerializer(
            data={"status": "pending"},
            context={"store": self.store},
        )
        assert not serializer.is_valid()

    def test_invalid_transition_cancelled_to_active(self):
        self.store.status = StoreStatus.CANCELLED
        self.store.save()
        serializer = StoreStatusSerializer(
            data={"status": "active"},
            context={"store": self.store},
        )
        assert not serializer.is_valid()


@pytest.mark.django_db
class TestStoreDetailSerializer(TestCase):
    """Test read-only store serializer."""

    def test_includes_subscription_status(self):
        store = Store.objects.create(
            name="Detail Test",
            slug="detail-test",
            domain="detail.joat.com",
        )
        StoreSubscription.objects.create(store=store, status="trial")
        data = StoreDetailSerializer(store).data
        assert data["subscription_status"] == "trial"
        assert "id" in data
        assert "domain" in data

    def test_subscription_status_none_when_missing(self):
        store = Store.objects.create(
            name="No Sub",
            slug="no-sub",
            domain="nosub.joat.com",
        )
        data = StoreDetailSerializer(store).data
        assert data["subscription_status"] is None


@pytest.mark.django_db
class TestPlanAndSubscriptionModels(TestCase):
    """Test SaaS stub models."""

    def test_plan_defaults(self):
        plan = Plan.objects.create(name="Free Trial", slug="free", api_rate_limit=100)
        assert plan.name == "Free Trial"
        assert plan.api_rate_limit == 100

    def test_subscription_with_plan(self):
        store = Store.objects.create(
            name="Plan Test",
            slug="plan-test",
            domain="plan.joat.com",
        )
        plan = Plan.objects.create(name="Pro", api_rate_limit=500)
        StoreSubscription.objects.create(store=store, plan=plan, status="active")
        # Access pattern from architecture: request.store.subscription.plan
        assert store.subscription.plan.api_rate_limit == 500

    def test_subscription_plan_nullable(self):
        store = Store.objects.create(
            name="No Plan",
            slug="no-plan",
            domain="noplan.joat.com",
        )
        subscription = StoreSubscription.objects.create(store=store)
        assert subscription.plan is None
        assert subscription.status == "trial"


@pytest.mark.django_db
class TestUserStoreFK(TestCase):
    """Test User model store FK and unique constraint."""

    def test_user_with_store(self):
        store = Store.objects.create(
            name="User Test",
            slug="user-test",
            domain="user.joat.com",
        )
        user = User.objects.create_user(
            email="staff@test.com",
            password=None,
            store=store,
            role="store_owner",
        )
        assert user.store == store
        assert user.role == "store_owner"

    def test_platform_admin_no_store(self):
        user = User.objects.create_user(
            email="admin@joat.com",
            password="testpass",
            store=None,
            role="platform_admin",
        )
        assert user.store is None
        assert user.role == "platform_admin"

    def test_duplicate_platform_admin_email_rejected(self):
        """M4: uq_platform_admin_email partial index prevents duplicate admin emails."""
        from django.db import IntegrityError

        User.objects.create_user(
            email="admin@joat.com",
            password="pass1",
            store=None,
            role="platform_admin",
        )
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                email="admin@joat.com",
                password="pass2",
                store=None,
                role="platform_admin",
            )


# ---------------------------------------------------------------------------
# API endpoint tests (require PostgreSQL)
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestStoreProvisionEndpoint(TestCase):
    """Test POST /api/v1/platform/stores/."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@joat.com",
            password="adminpass",
            role="platform_admin",
        )
        self.client.force_authenticate(user=self.admin)
        self.url = "/api/v1/platform/stores/"

    def test_provision_success(self):
        resp = self.client.post(
            self.url,
            {
                "name": "New Store",
                "domain": "new.joat.com",
                "tenant_type": "retail",
                "owner_email": "owner@new.com",
            },
            format="json",
        )
        assert resp.status_code == 201, resp.data
        assert resp.data["data"]["name"] == "New Store"
        assert resp.data["data"]["subscription_status"] == "trial"

    def test_provision_domain_conflict(self):
        Store.objects.create(
            name="Existing",
            slug="existing",
            domain="taken.joat.com",
        )
        resp = self.client.post(
            self.url,
            {
                "name": "Conflict",
                "domain": "taken.joat.com",
                "tenant_type": "retail",
                "owner_email": "owner@conflict.com",
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_provision_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.client.post(
            self.url,
            {
                "name": "Unauth",
                "domain": "unauth.joat.com",
                "tenant_type": "retail",
                "owner_email": "o@test.com",
            },
            format="json",
        )
        assert resp.status_code in (401, 403)


@pytest.mark.django_db
class TestStoreListEndpoint(TestCase):
    """Test GET /api/v1/platform/stores/list/."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@joat.com",
            password="adminpass",
            role="platform_admin",
        )
        self.client.force_authenticate(user=self.admin)
        self.url = "/api/v1/platform/stores/list/"

    def test_list_returns_stores(self):
        store = Store.objects.create(
            name="Listed Store",
            slug="listed",
            domain="listed.joat.com",
        )
        StoreSubscription.objects.create(store=store, status="trial")
        resp = self.client.get(self.url)
        assert resp.status_code == 200
        assert len(resp.data) >= 1

    def test_list_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get(self.url)
        assert resp.status_code in (401, 403)


@pytest.mark.django_db
class TestStoreStatusEndpoint(TestCase):
    """Test PATCH /api/v1/platform/stores/{id}/status/."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@joat.com",
            password="adminpass",
            role="platform_admin",
        )
        self.client.force_authenticate(user=self.admin)
        self.store = Store.objects.create(
            name="Status Store",
            slug="status-store",
            domain="status-ep.joat.com",
            status=StoreStatus.PENDING,
        )

    def test_valid_transition(self):
        url = f"/api/v1/platform/stores/{self.store.pk}/status/"
        resp = self.client.patch(url, {"status": "active"}, format="json")
        assert resp.status_code == 200
        assert resp.data["data"]["status"] == "active"

    def test_invalid_transition(self):
        url = f"/api/v1/platform/stores/{self.store.pk}/status/"
        resp = self.client.patch(url, {"status": "cancelled"}, format="json")
        assert resp.status_code == 400

    def test_nonexistent_store(self):
        fake_id = uuid.uuid4()
        url = f"/api/v1/platform/stores/{fake_id}/status/"
        resp = self.client.patch(url, {"status": "active"}, format="json")
        assert resp.status_code == 404
