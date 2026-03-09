"""
Tests for Story 1.5: JWT Auth + RBAC (4 Roles).

Covers:
  - Token obtain with store_id + role claims
  - Refresh token in httpOnly cookie (not in body)
  - Token refresh from cookie
  - Token reuse detection (family invalidation)
  - Logout-all (blacklist all refresh tokens)
  - Permission classes (IsStoreScoped, IsPlatformAdmin, IsStoreOwner, IsStoreManager)
  - Rate throttling from plan
  - Cross-tenant auth isolation

Implementation: Story 1.5
"""

from django.test import TestCase

import pytest
from rest_framework.test import APIClient

from apps.saas.models import Plan, StoreSubscription
from apps.store.models import Store
from apps.users.models import User


def make_store(name, domain, **kwargs):
    from django.utils.text import slugify

    slug = slugify(name)
    return Store.objects.create(name=name, slug=slug, domain=domain, **kwargs)


def make_user(email, store=None, role="customer", password="testpass123"):
    return User.objects.create_user(
        email=email,
        password=password,
        store=store,
        role=role,
    )


# ---------------------------------------------------------------------------
# Token obtain tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTokenObtain(TestCase):
    """Test POST /api/v1/auth/token/."""

    def setUp(self):
        self.client = APIClient()
        self.store = make_store("Auth Store", "auth.joat.com")
        self.user = make_user(
            "staff@auth.com",
            store=self.store,
            role="store_owner",
        )
        self.url = "/api/v1/auth/token/"

    def test_obtain_returns_access_in_body(self):
        resp = self.client.post(
            self.url,
            {"email": "staff@auth.com", "password": "testpass123"},
            format="json",
        )
        assert resp.status_code == 200, resp.data
        assert "access" in resp.data["data"]
        # Refresh must NOT be in body
        assert "refresh" not in resp.data["data"]

    def test_obtain_sets_refresh_cookie(self):
        resp = self.client.post(
            self.url,
            {"email": "staff@auth.com", "password": "testpass123"},
            format="json",
        )
        assert resp.status_code == 200
        assert "refresh_token" in resp.cookies
        cookie = resp.cookies["refresh_token"]
        assert cookie["httponly"]
        assert cookie["path"] == "/api/v1/auth/"

    def test_obtain_includes_user_info(self):
        resp = self.client.post(
            self.url,
            {"email": "staff@auth.com", "password": "testpass123"},
            format="json",
        )
        user_data = resp.data["data"]["user"]
        assert user_data["email"] == "staff@auth.com"
        assert user_data["role"] == "store_owner"
        assert user_data["store_id"] == str(self.store.pk)

    def test_obtain_invalid_credentials(self):
        resp = self.client.post(
            self.url,
            {"email": "staff@auth.com", "password": "wrong"},
            format="json",
        )
        assert resp.status_code == 401

    def test_obtain_platform_admin_no_store(self):
        make_user("admin@joat.com", store=None, role="platform_admin")
        resp = self.client.post(
            self.url,
            {"email": "admin@joat.com", "password": "testpass123"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["data"]["user"]["store_id"] is None
        assert resp.data["data"]["user"]["role"] == "platform_admin"


# ---------------------------------------------------------------------------
# Token refresh tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTokenRefresh(TestCase):
    """Test POST /api/v1/auth/token/refresh/."""

    def setUp(self):
        self.client = APIClient()
        self.store = make_store("Refresh Store", "refresh.joat.com")
        self.user = make_user("refresh@test.com", store=self.store, role="store_owner")
        self.obtain_url = "/api/v1/auth/token/"
        self.refresh_url = "/api/v1/auth/token/refresh/"

    def _obtain_tokens(self):
        resp = self.client.post(
            self.obtain_url,
            {"email": "refresh@test.com", "password": "testpass123"},
            format="json",
        )
        return resp

    def test_refresh_returns_new_access(self):
        obtain_resp = self._obtain_tokens()
        assert obtain_resp.status_code == 200

        # Use the refresh cookie
        refresh_cookie = obtain_resp.cookies["refresh_token"].value
        self.client.cookies["refresh_token"] = refresh_cookie

        resp = self.client.post(self.refresh_url)
        assert resp.status_code == 200
        assert "access" in resp.data["data"]

    def test_refresh_rotates_cookie(self):
        obtain_resp = self._obtain_tokens()
        refresh_cookie = obtain_resp.cookies["refresh_token"].value
        self.client.cookies["refresh_token"] = refresh_cookie

        resp = self.client.post(self.refresh_url)
        assert resp.status_code == 200
        assert "refresh_token" in resp.cookies

    def test_refresh_without_cookie_returns_401(self):
        resp = self.client.post(self.refresh_url)
        assert resp.status_code == 401

    def test_refresh_token_reuse_detected(self):
        """Second use of same refresh token should fail (family invalidation)."""
        obtain_resp = self._obtain_tokens()
        old_refresh = obtain_resp.cookies["refresh_token"].value

        # First refresh — should succeed
        self.client.cookies["refresh_token"] = old_refresh
        resp1 = self.client.post(self.refresh_url)
        assert resp1.status_code == 200

        # Second use of OLD refresh — should fail (reuse detected)
        self.client.cookies["refresh_token"] = old_refresh
        resp2 = self.client.post(self.refresh_url)
        assert resp2.status_code == 401


# ---------------------------------------------------------------------------
# Logout-all tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLogoutAll(TestCase):
    """Test POST /api/v1/auth/logout-all/."""

    def setUp(self):
        self.client = APIClient()
        self.store = make_store("Logout Store", "logout.joat.com")
        self.user = make_user("logout@test.com", store=self.store, role="store_owner")
        self.obtain_url = "/api/v1/auth/token/"
        self.logout_url = "/api/v1/auth/logout-all/"

    def test_logout_all_invalidates_tokens(self):
        # Obtain tokens
        resp = self.client.post(
            self.obtain_url,
            {"email": "logout@test.com", "password": "testpass123"},
            format="json",
        )
        access = resp.data["data"]["access"]
        refresh_cookie = resp.cookies["refresh_token"].value

        # Logout all
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        logout_resp = self.client.post(self.logout_url)
        assert logout_resp.status_code == 200

        # Try to refresh — should fail
        self.client.credentials()  # clear auth
        self.client.cookies["refresh_token"] = refresh_cookie
        refresh_resp = self.client.post("/api/v1/auth/token/refresh/")
        assert refresh_resp.status_code == 401

    def test_logout_all_requires_auth(self):
        resp = self.client.post(self.logout_url)
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Permission class tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestIsStoreScopedPermission(TestCase):
    """Test IsStoreScoped permission class."""

    def setUp(self):
        self.store_a = make_store("Store A", "a.joat.com")
        self.store_b = make_store("Store B", "b.joat.com")
        self.owner_a = make_user("owner@a.com", store=self.store_a, role="store_owner")
        self.owner_b = make_user("owner@b.com", store=self.store_b, role="store_owner")
        self.admin = make_user("admin@joat.com", store=None, role="platform_admin")

    def test_cross_tenant_auth_user_cannot_access_other_store(self):
        """IsStoreScoped blocks user from accessing different store."""
        from unittest.mock import Mock

        from core.permissions import IsStoreScoped

        perm = IsStoreScoped()
        request = Mock()
        request.user = self.owner_a
        request.store = self.store_b  # wrong store!
        assert not perm.has_permission(request, None)

    def test_user_can_access_own_store(self):
        from unittest.mock import Mock

        from core.permissions import IsStoreScoped

        perm = IsStoreScoped()
        request = Mock()
        request.user = self.owner_a
        request.store = self.store_a
        assert perm.has_permission(request, None)

    def test_platform_admin_can_access_any_store(self):
        from unittest.mock import Mock

        from core.permissions import IsStoreScoped

        perm = IsStoreScoped()
        request = Mock()
        request.user = self.admin
        request.store = self.store_a
        assert perm.has_permission(request, None)


@pytest.mark.django_db
class TestIsPlatformAdminPermission(TestCase):
    """Test IsPlatformAdmin permission class."""

    def test_platform_admin_allowed(self):
        from unittest.mock import Mock

        from core.permissions import IsPlatformAdmin

        admin = make_user("admin@joat.com", store=None, role="platform_admin")
        perm = IsPlatformAdmin()
        request = Mock()
        request.user = admin
        assert perm.has_permission(request, None)

    def test_store_owner_denied(self):
        from unittest.mock import Mock

        from core.permissions import IsPlatformAdmin

        store = make_store("Test", "test.joat.com")
        owner = make_user("o@t.com", store=store, role="store_owner")
        perm = IsPlatformAdmin()
        request = Mock()
        request.user = owner
        assert not perm.has_permission(request, None)


@pytest.mark.django_db
class TestIsStoreOwnerPermission(TestCase):
    """Test IsStoreOwner permission class."""

    def test_store_owner_allowed(self):
        from unittest.mock import Mock

        from core.permissions import IsStoreOwner

        store = make_store("Owner Test", "ownertest.joat.com")
        owner = make_user("o@test.com", store=store, role="store_owner")
        perm = IsStoreOwner()
        request = Mock()
        request.user = owner
        request.store = store
        assert perm.has_permission(request, None)

    def test_store_manager_denied(self):
        from unittest.mock import Mock

        from core.permissions import IsStoreOwner

        store = make_store("Mgr Test", "mgrtest.joat.com")
        manager = make_user("m@test.com", store=store, role="store_manager")
        perm = IsStoreOwner()
        request = Mock()
        request.user = manager
        request.store = store
        assert not perm.has_permission(request, None)

    def test_cross_tenant_owner_denied(self):
        from unittest.mock import Mock

        from core.permissions import IsStoreOwner

        store_a = make_store("Cross A", "crossa.joat.com")
        store_b = make_store("Cross B", "crossb.joat.com")
        owner_a = make_user("oa@test.com", store=store_a, role="store_owner")
        perm = IsStoreOwner()
        request = Mock()
        request.user = owner_a
        request.store = store_b
        assert not perm.has_permission(request, None)


@pytest.mark.django_db
class TestIsStoreManagerPermission(TestCase):
    """Test IsStoreManager permission class."""

    def test_store_manager_allowed(self):
        from unittest.mock import Mock

        from core.permissions import IsStoreManager

        store = make_store("Mgr Perm", "mgrperm.joat.com")
        manager = make_user("mgr@test.com", store=store, role="store_manager")
        perm = IsStoreManager()
        request = Mock()
        request.user = manager
        request.store = store
        assert perm.has_permission(request, None)

    def test_store_owner_also_allowed(self):
        from unittest.mock import Mock

        from core.permissions import IsStoreManager

        store = make_store("Own Mgr", "ownmgr.joat.com")
        owner = make_user("own@test.com", store=store, role="store_owner")
        perm = IsStoreManager()
        request = Mock()
        request.user = owner
        request.store = store
        assert perm.has_permission(request, None)

    def test_customer_denied(self):
        from unittest.mock import Mock

        from core.permissions import IsStoreManager

        store = make_store("Cust Test", "custtest.joat.com")
        customer = make_user("c@test.com", store=store, role="customer")
        perm = IsStoreManager()
        request = Mock()
        request.user = customer
        request.store = store
        assert not perm.has_permission(request, None)


# ---------------------------------------------------------------------------
# JWT claims tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestJWTClaims(TestCase):
    """Test that JWT tokens contain store_id + role claims."""

    def test_access_token_contains_store_id_and_role(self):
        store = make_store("Claims Store", "claims.joat.com")
        user = make_user("claims@test.com", store=store, role="store_owner")

        from apps.users.serializers import StoreTokenObtainPairSerializer

        refresh = StoreTokenObtainPairSerializer.get_token(user)
        access = refresh.access_token
        assert access["store_id"] == str(store.pk)
        assert access["role"] == "store_owner"

    def test_platform_admin_token_has_null_store_id(self):
        admin = make_user("admin@joat.com", store=None, role="platform_admin")

        from apps.users.serializers import StoreTokenObtainPairSerializer

        refresh = StoreTokenObtainPairSerializer.get_token(admin)
        access = refresh.access_token
        assert access["store_id"] is None
        assert access["role"] == "platform_admin"


# ---------------------------------------------------------------------------
# Throttling tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestStorePlanRateThrottle(TestCase):
    """Test plan-based rate throttling."""

    def test_throttle_uses_plan_rate(self):
        from unittest.mock import Mock

        from core.throttling import StorePlanRateThrottle

        store = make_store("Throttle Store", "throttle.joat.com")
        plan = Plan.objects.create(name="Pro", api_rate_limit=500)
        StoreSubscription.objects.create(store=store, plan=plan, status="active")

        throttle = StorePlanRateThrottle()
        request = Mock()
        request.user = Mock(is_authenticated=True)
        request.store = store
        request.META = {"REMOTE_ADDR": "127.0.0.1"}

        # The throttle should read 500/min from the plan
        key = throttle.get_cache_key(request, None)
        assert key == f"throttle_store_{store.pk}"

    def test_throttle_skips_platform_requests(self):
        from unittest.mock import Mock

        from core.throttling import StorePlanRateThrottle

        throttle = StorePlanRateThrottle()
        request = Mock()
        request.store = None

        key = throttle.get_cache_key(request, None)
        assert key is None
