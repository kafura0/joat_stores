"""
Tests for core.views.TenantViewSet.

Uses StoreSettings (a real TenantModel subclass) via a concrete viewset
to verify scoping, perform_create, and cross-tenant isolation.
"""

import uuid

import pytest
from rest_framework import routers
from rest_framework.test import APIRequestFactory

from apps.store.models import Store, StoreSettings, StoreStatus, TenantType
from core.serializers import TenantSerializer
from core.views import TenantViewSet

# ---------------------------------------------------------------------------
# Concrete test viewset wired to StoreSettings
# ---------------------------------------------------------------------------


class StoreSettingsSerializer(TenantSerializer):
    class Meta:
        model = StoreSettings
        fields = ["id"]


class StoreSettingsViewSet(TenantViewSet):
    serializer_class = StoreSettingsSerializer
    queryset = StoreSettings.objects.all()


# ---------------------------------------------------------------------------
# URL configuration for the test viewset
# ---------------------------------------------------------------------------

router = routers.SimpleRouter()
router.register(r"settings", StoreSettingsViewSet, basename="settings")
urlpatterns = router.urls


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_store(**kwargs):
    defaults = {
        "name": "Test Store",
        "slug": f"vw-{uuid.uuid4().hex[:8]}",
        "domain": f"vw-{uuid.uuid4().hex[:8]}.joat.com",
        "tenant_type": TenantType.RETAIL,
        "status": StoreStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Store.objects.create(**defaults)


def make_request_with_store(store, path="/settings/", method="get"):
    factory = APIRequestFactory()
    fn = getattr(factory, method)
    request = fn(path)
    request.store = store
    return request


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTenantViewSetQueryScope:
    def test_get_queryset_scopes_to_request_store(self):
        """get_queryset() filters to request.store only."""
        store_a = make_store()
        store_b = make_store()
        settings_a = StoreSettings.objects.create(store=store_a)
        StoreSettings.objects.create(store=store_b)

        request = make_request_with_store(store_a)
        viewset = StoreSettingsViewSet()
        viewset.request = request
        viewset.kwargs = {}
        viewset.format_kwarg = None
        viewset.action = "list"

        qs = viewset.get_queryset()
        pks = list(qs.values_list("pk", flat=True))
        assert settings_a.pk in pks
        assert len(pks) == 1

    def test_cross_tenant_isolation_viewset_cannot_read_other_store_record(
        self,
    ):
        """
        get_queryset() for store_a never returns store_b records.
        CI gate: pytest -k cross_tenant
        """
        store_a = make_store()
        store_b = make_store()
        StoreSettings.objects.create(store=store_b)

        request = make_request_with_store(store_a)
        viewset = StoreSettingsViewSet()
        viewset.request = request
        viewset.kwargs = {}
        viewset.format_kwarg = None
        viewset.action = "list"

        qs = viewset.get_queryset()
        assert qs.count() == 0


@pytest.mark.django_db
class TestTenantViewSetPerformCreate:
    def test_perform_create_injects_store(self):
        """perform_create() saves with store=request.store."""
        store = make_store()
        request = make_request_with_store(store, method="post")

        viewset = StoreSettingsViewSet()
        viewset.request = request
        viewset.kwargs = {}
        viewset.format_kwarg = None
        viewset.action = "create"

        serializer = StoreSettingsSerializer(data={}, context={"request": request})
        assert serializer.is_valid(), serializer.errors
        viewset.perform_create(serializer)

        created = StoreSettings.objects.for_store(store).first()
        assert created is not None
        assert created.store == store

    def test_cross_tenant_isolation_perform_create_uses_request_store(self):
        """
        perform_create always uses request.store regardless of payload.
        CI gate: pytest -k cross_tenant
        """
        store_a = make_store()
        store_b = make_store()
        request = make_request_with_store(store_a, method="post")

        # Serializer receives data trying to set store_b
        serializer = StoreSettingsSerializer(
            data={"store": str(store_b.pk)},
            context={"request": request},
        )
        assert serializer.is_valid(), serializer.errors

        viewset = StoreSettingsViewSet()
        viewset.request = request
        viewset.kwargs = {}
        viewset.format_kwarg = None
        viewset.action = "create"
        viewset.perform_create(serializer)

        # Object must belong to store_a, not store_b
        assert StoreSettings.objects.for_store(store_a).count() == 1
        assert StoreSettings.objects.for_store(store_b).count() == 0


@pytest.mark.django_db
class TestTenantViewSetSerializerContext:
    def test_get_serializer_context_includes_request(self):
        """get_serializer_context() always includes 'request' key."""
        store = make_store()
        request = make_request_with_store(store)

        viewset = StoreSettingsViewSet()
        viewset.request = request
        viewset.kwargs = {}
        viewset.format_kwarg = None
        viewset.action = "list"

        # Provide minimal args required by super().get_serializer_context()
        viewset.format_kwarg = None
        context = viewset.get_serializer_context()
        assert "request" in context
        assert context["request"] is request
