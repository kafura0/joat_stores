"""
Tests for core.serializers.TenantSerializer.

Uses StoreSettings as a concrete TenantModel + TenantSerializer subclass.
"""

import uuid

import pytest
from rest_framework.test import APIRequestFactory

from apps.store.models import Store, StoreSettings, StoreStatus, TenantType
from core.serializers import TenantSerializer


def make_store(**kwargs):
    defaults = {
        "name": "Test Store",
        "slug": f"ser-{uuid.uuid4().hex[:8]}",
        "domain": f"ser-{uuid.uuid4().hex[:8]}.joat.com",
        "tenant_type": TenantType.RETAIL,
        "status": StoreStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Store.objects.create(**defaults)


class StoreSettingsSerializer(TenantSerializer):
    """Concrete serializer for testing TenantSerializer base class."""

    class Meta:
        model = StoreSettings
        fields = ["id"]


def make_request_with_store(store):
    """Create a mock request with request.store set."""
    factory = APIRequestFactory()
    request = factory.post("/")
    request.store = store
    return request


@pytest.mark.django_db
class TestTenantSerializer:
    def test_create_injects_store_from_context(self):
        """TenantSerializer.create() sets store from request context."""
        store = make_store()
        request = make_request_with_store(store)
        serializer = StoreSettingsSerializer(data={}, context={"request": request})
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()
        assert instance.store == store

    def test_create_without_request_context_uses_kwarg(self):
        """Without request context, save(store=...) kwarg still works."""
        store = make_store()
        serializer = StoreSettingsSerializer(data={}, context={})
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save(store=store)
        assert instance.store == store

    def test_store_field_stripped_from_input(self):
        """Client-supplied store field is stripped — cannot override."""
        store_a = make_store()
        store_b = make_store()
        request = make_request_with_store(store_a)

        # Try to supply store_b's ID in the request payload
        serializer = StoreSettingsSerializer(
            data={"store": str(store_b.pk)},
            context={"request": request},
        )
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()
        # Must be store_a (from request context), not store_b (from payload)
        assert instance.store == store_a

    def test_store_id_field_stripped_from_input(self):
        """Client-supplied store_id field is stripped — cannot override."""
        store_a = make_store()
        store_b = make_store()
        request = make_request_with_store(store_a)

        serializer = StoreSettingsSerializer(
            data={"store_id": str(store_b.pk)},
            context={"request": request},
        )
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()
        assert instance.store == store_a

    def test_cross_tenant_isolation_serializer_cannot_set_foreign_store(self):
        """
        Serializer cannot be used to assign a record to a different store.
        CI gate: pytest -k cross_tenant
        """
        store_a = make_store()
        store_b = make_store()
        request = make_request_with_store(store_a)

        # Attempt to create a record for store_b by supplying its ID
        serializer = StoreSettingsSerializer(
            data={"store": str(store_b.pk), "store_id": str(store_b.pk)},
            context={"request": request},
        )
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()

        # Record must belong to store_a — the request store
        assert instance.store_id == store_a.pk
        assert instance.store_id != store_b.pk
