"""
Tests for customer_hub app — cross-tenant customer portal.

Covers:
  - HubRegisterView (POST /hub/auth/register/)
  - HubLoginView (POST /hub/auth/login/)
  - HubMeView (GET /hub/me/)
  - HubStoresView (GET /hub/stores/)
  - HubOrdersView (GET /hub/orders/)
  - HubLoyaltyView (GET /hub/loyalty/)
  - FCMRegisterView (POST /hub/fcm/register/)
  - FCMUnregisterView (POST /hub/fcm/unregister/)
  - HubJWTAuthentication
"""

import uuid
from decimal import Decimal

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.customer_hub.views import _issue_hub_token
from apps.loyalty.models import LoyaltyAccount
from apps.notifications.models import FCMDevice
from apps.order.models import Order
from apps.store.models import Store, StoreSettings, TenantType
from apps.store.tests.factories import StoreFactory
from apps.users.models import PlatformUser, User


@pytest.fixture
def platform_user():
    pu = PlatformUser(
        email="test@hub.com",
        full_name="Test Customer",
        phone="+254700000001",
        avatar_url="https://cdn.example.com/avatar.jpg",
    )
    pu.set_password("testpass123")
    pu.save()
    return pu


@pytest.fixture
def hub_token(platform_user):
    return _issue_hub_token(platform_user)


@pytest.fixture
def auth_client(hub_token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {hub_token['access']}")
    return client


@pytest.fixture
def store():
    return StoreFactory(tenant_type=TenantType.RETAIL, name="Test Retail Store")


@pytest.fixture
def customer_user(store, platform_user):
    return User.objects.create(
        email="test@hub.com",
        store=store,
        role="customer",
        platform_user=platform_user,
    )


@pytest.fixture
def client():
    return APIClient()


# ---------------------------------------------------------------------------
# _issue_hub_token
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestIssueHubToken:
    def test_contains_platform_user_id(self, platform_user):
        tokens = _issue_hub_token(platform_user)
        from rest_framework_simplejwt.tokens import AccessToken

        access = AccessToken(tokens["access"])
        assert str(platform_user.pk) == str(access["platform_user_id"])

    def test_role_is_customer(self, platform_user):
        tokens = _issue_hub_token(platform_user)
        from rest_framework_simplejwt.tokens import AccessToken

        access = AccessToken(tokens["access"])
        assert access["role"] == "customer"

    def test_store_id_is_none(self, platform_user):
        tokens = _issue_hub_token(platform_user)
        from rest_framework_simplejwt.tokens import AccessToken

        access = AccessToken(tokens["access"])
        assert access["store_id"] is None


# ---------------------------------------------------------------------------
# HubRegisterView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestHubRegisterView:
    def setup_method(self):
        self.client = APIClient()
        self.url = "/api/v1/hub/auth/register/"

    def test_register_success(self):
        resp = self.client.post(
            self.url,
            {
                "email": "new@hub.com",
                "password": "securepass123",
                "full_name": "New User",
            },
            format="json",
        )
        assert resp.status_code == 201
        assert PlatformUser.objects.filter(email="new@hub.com").exists()
        assert "access" in resp.data["data"]
        assert resp.data["data"]["user"]["email"] == "new@hub.com"

    def test_register_duplicate_email(self, platform_user):
        resp = self.client.post(
            self.url,
            {
                "email": "test@hub.com",
                "password": "securepass123",
            },
            format="json",
        )
        assert resp.status_code == 409
        assert resp.data["errors"][0]["code"] == "EMAIL_EXISTS"

    def test_register_short_password(self):
        resp = self.client.post(
            self.url,
            {
                "email": "short@hub.com",
                "password": "short",
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_register_with_phone(self):
        resp = self.client.post(
            self.url,
            {
                "email": "phone@hub.com",
                "password": "securepass123",
                "phone": "+254700000099",
            },
            format="json",
        )
        assert resp.status_code == 201
        pu = PlatformUser.objects.get(email="phone@hub.com")
        assert pu.phone == "+254700000099"


# ---------------------------------------------------------------------------
# HubLoginView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestHubLoginView:
    def setup_method(self):
        self.client = APIClient()
        self.url = "/api/v1/hub/auth/login/"

    def test_login_success(self, platform_user):
        resp = self.client.post(
            self.url,
            {"email": "test@hub.com", "password": "testpass123"},
            format="json",
        )
        assert resp.status_code == 200
        assert "access" in resp.data["data"]
        assert "refresh" in resp.data["data"]
        assert resp.data["data"]["user"]["email"] == "test@hub.com"

    def test_login_wrong_password(self, platform_user):
        resp = self.client.post(
            self.url,
            {"email": "test@hub.com", "password": "wrongpass"},
            format="json",
        )
        assert resp.status_code == 401
        assert resp.data["errors"][0]["code"] == "INVALID_CREDENTIALS"

    def test_login_nonexistent_user(self):
        resp = self.client.post(
            self.url,
            {"email": "nobody@hub.com", "password": "pass12345"},
            format="json",
        )
        assert resp.status_code == 401

    def test_login_missing_fields(self):
        resp = self.client.post(self.url, {}, format="json")
        assert resp.status_code == 400
        assert resp.data["errors"][0]["code"] == "EMAIL_AND_PASSWORD_REQUIRED"

    def test_login_inactive_user(self, platform_user):
        platform_user.is_active = False
        platform_user.save()
        resp = self.client.post(
            self.url,
            {"email": "test@hub.com", "password": "testpass123"},
            format="json",
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# HubMeView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestHubMeView:
    def setup_method(self):
        self.url = "/api/v1/hub/me/"

    def test_returns_profile(self, auth_client, platform_user):
        resp = auth_client.get(self.url)
        assert resp.status_code == 200
        assert resp.data["data"]["email"] == "test@hub.com"
        assert resp.data["data"]["full_name"] == "Test Customer"

    def test_unauthenticated_returns_403(self, client):
        resp = client.get(self.url)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# HubStoresView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestHubStoresView:
    def setup_method(self):
        self.url = "/api/v1/hub/stores/"

    def test_returns_linked_stores(self, auth_client, customer_user, store):
        StoreSettings.objects.create(store=store, tagline="Best shop ever")
        resp = auth_client.get(self.url)
        assert resp.status_code == 200
        assert len(resp.data["data"]) == 1
        assert resp.data["data"][0]["name"] == store.name

    def test_empty_when_no_store_users(self, auth_client, platform_user):
        resp = auth_client.get(self.url)
        assert resp.status_code == 200
        assert resp.data["data"] == []


# ---------------------------------------------------------------------------
# HubOrdersView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestHubOrdersView:
    def setup_method(self):
        self.url = "/api/v1/hub/orders/"

    def test_returns_orders_for_user(self, auth_client, customer_user, store):
        Order.objects.create(
            store=store,
            customer=customer_user,
            status="pending",
            total_amount=Decimal("250.00"),
            items_snapshot=[{"name": "Item", "quantity": 1, "price": "250.00"}],
        )
        resp = auth_client.get(self.url)
        assert resp.status_code == 200
        assert len(resp.data["data"]) == 1
        assert resp.data["data"][0]["status"] == "pending"

    def test_empty_when_no_orders(self, auth_client, platform_user):
        resp = auth_client.get(self.url)
        assert resp.status_code == 200
        assert resp.data["data"] == []


# ---------------------------------------------------------------------------
# HubLoyaltyView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestHubLoyaltyView:
    def setup_method(self):
        self.url = "/api/v1/hub/loyalty/"

    def test_returns_loyalty_accounts(self, auth_client, customer_user, store):
        LoyaltyAccount.objects.create(
            store=store,
            customer=customer_user,
            customer_phone="+254700000001",
            points_balance=150,
            lifetime_earned=300,
        )
        resp = auth_client.get(self.url)
        assert resp.status_code == 200
        assert len(resp.data["data"]) == 1
        assert resp.data["data"][0]["points_balance"] == 150

    def test_empty_when_no_phone(self, auth_client, platform_user):
        platform_user.phone = None
        platform_user.save()
        resp = auth_client.get(self.url)
        assert resp.status_code == 200
        assert resp.data["data"] == []


# ---------------------------------------------------------------------------
# FCMRegisterView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFCMRegisterView:
    def setup_method(self):
        self.url = "/api/v1/hub/fcm/register/"

    def test_register_device(self, auth_client, platform_user):
        resp = auth_client.post(
            self.url,
            {"registration_id": "fcm_abc123", "platform": "android"},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["data"]["created"] is True
        assert FCMDevice.objects.filter(
            platform_user=platform_user,
            registration_id="fcm_abc123",
        ).exists()

    def test_register_same_device_twice(self, auth_client, platform_user):
        auth_client.post(
            self.url,
            {"registration_id": "fcm_abc123", "platform": "android"},
            format="json",
        )
        resp = auth_client.post(
            self.url,
            {"registration_id": "fcm_abc123", "platform": "ios"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["data"]["created"] is False
        device = FCMDevice.objects.get(
            platform_user=platform_user,
            registration_id="fcm_abc123",
        )
        assert device.platform == "ios"
        assert device.is_active is True

    def test_register_missing_registration_id(self, auth_client):
        resp = auth_client.post(self.url, {}, format="json")
        assert resp.status_code == 400
        assert resp.data["errors"][0]["code"] == "REGISTRATION_ID_REQUIRED"


# ---------------------------------------------------------------------------
# FCMUnregisterView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFCMUnregisterView:
    def setup_method(self):
        self.url = "/api/v1/hub/fcm/unregister/"

    def test_unregister_device(self, auth_client, platform_user):
        FCMDevice.objects.create(
            platform_user=platform_user,
            registration_id="fcm_abc123",
        )
        resp = auth_client.post(
            self.url,
            {"registration_id": "fcm_abc123"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["data"]["deactivated"] is True
        device = FCMDevice.objects.get(
            platform_user=platform_user,
            registration_id="fcm_abc123",
        )
        assert device.is_active is False

    def test_unregister_nonexistent(self, auth_client):
        resp = auth_client.post(
            self.url,
            {"registration_id": "nonexistent"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["data"]["deactivated"] is False

    def test_unregister_missing_id(self, auth_client):
        resp = auth_client.post(self.url, {}, format="json")
        assert resp.status_code == 400
        assert resp.data["errors"][0]["code"] == "REGISTRATION_ID_REQUIRED"


# ---------------------------------------------------------------------------
# HubJWTAuthentication
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestHubJWTAuthentication:
    def test_valid_token(self, auth_client, platform_user):
        resp = auth_client.get("/api/v1/hub/me/")
        assert resp.status_code == 200

    def test_invalid_token(self, client):
        client.credentials(HTTP_AUTHORIZATION="Bearer invalid.token.here")
        resp = client.get("/api/v1/hub/me/")
        assert resp.status_code in (401, 403)

    def test_missing_bearer_prefix(self, client, hub_token):
        client.credentials(HTTP_AUTHORIZATION=hub_token["access"])
        resp = client.get("/api/v1/hub/me/")
        assert resp.status_code in (401, 403)

    def test_store_token_not_hub_token(self, client):
        from apps.users.tests.factories import UserFactory

        user = UserFactory()
        refresh = RefreshToken()
        refresh["user_id"] = str(user.pk)
        refresh["role"] = "customer"
        refresh["store_id"] = str(uuid.uuid4())
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        resp = client.get("/api/v1/hub/me/")
        assert resp.status_code in (401, 403)

    def test_inactive_user_rejected(self, platform_user):
        platform_user.is_active = False
        platform_user.save()
        client = APIClient()
        tokens = _issue_hub_token(platform_user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        resp = client.get("/api/v1/hub/me/")
        assert resp.status_code in (401, 403)
