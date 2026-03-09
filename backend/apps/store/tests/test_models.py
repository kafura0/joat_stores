"""
Tests for apps.store.models — Store, StoreSettings, StoreTheme.

All tests use @pytest.mark.django_db (requires PostgreSQL — see ci.yml services).
"""

import uuid

from django.core.exceptions import ValidationError
from django.db import IntegrityError

import pytest

from apps.store.models import Store, StoreSettings, StoreStatus, StoreTheme, TenantType


def make_store(**kwargs):
    """Helper: create a Store with sensible defaults."""
    defaults = {
        "name": "Test Store",
        "slug": f"test-store-{uuid.uuid4().hex[:8]}",
        "domain": f"test-{uuid.uuid4().hex[:8]}.joat.com",
        "tenant_type": TenantType.RETAIL,
        "status": StoreStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Store.objects.create(**defaults)


@pytest.mark.django_db
class TestStoreCreation:
    def test_store_creation_with_defaults(self):
        """Store creates with sensible defaults."""
        store = make_store(name="My Shop", slug="my-shop", domain="myshop.joat.com")
        assert store.pk is not None
        assert store.currency == "KES"
        assert store.country == "KE"
        assert store.timezone == "Africa/Nairobi"
        assert store.payment_methods == []

    def test_store_uuid_primary_key(self):
        """Store PK is a UUID, not an integer."""
        store = make_store()
        assert isinstance(store.pk, uuid.UUID)

    def test_store_creation_with_all_fields(self):
        """Store stores all fields correctly."""
        store = Store.objects.create(
            name="Full Store",
            slug="full-store",
            domain="full.joat.com",
            tenant_type=TenantType.RESTAURANT,
            status=StoreStatus.PENDING,
            currency="USD",
            payment_methods=["mpesa", "card"],
            country="UG",
            timezone="Africa/Kampala",
        )
        store.refresh_from_db()
        assert store.name == "Full Store"
        assert store.tenant_type == TenantType.RESTAURANT
        assert store.status == StoreStatus.PENDING
        assert store.currency == "USD"
        assert store.payment_methods == ["mpesa", "card"]
        assert store.country == "UG"
        assert store.timezone == "Africa/Kampala"

    def test_store_str(self):
        """Store __str__ includes name and domain."""
        store = make_store(name="Nairobi Bites", domain="nairobibites.joat.com")
        assert "Nairobi Bites" in str(store)
        assert "nairobibites.joat.com" in str(store)


@pytest.mark.django_db
class TestStoreUniqueConstraints:
    def test_store_slug_unique(self):
        """Duplicate slug raises IntegrityError."""
        make_store(slug="unique-slug", domain="store1.joat.com")
        with pytest.raises(IntegrityError):
            make_store(slug="unique-slug", domain="store2.joat.com")

    def test_store_domain_unique(self):
        """Duplicate domain raises IntegrityError."""
        make_store(slug="store-a", domain="shared.joat.com")
        with pytest.raises(IntegrityError):
            make_store(slug="store-b", domain="shared.joat.com")


@pytest.mark.django_db
class TestStoreSoftDelete:
    def test_soft_delete_sets_deleted_timestamp(self):
        """Calling store.delete() sets deleted field, not hard-deletes."""
        store = make_store()
        store_id = store.pk
        store.delete()
        # Default manager excludes soft-deleted
        assert not Store.objects.filter(pk=store_id).exists()
        # all_objects includes soft-deleted
        assert Store.all_objects.filter(pk=store_id).exists()
        deleted_store = Store.all_objects.get(pk=store_id)
        assert deleted_store.deleted is not None

    def test_active_queryset_method(self):
        """StoreQuerySet.active() filters by status=active."""
        active = make_store(status=StoreStatus.ACTIVE)
        make_store(status=StoreStatus.SUSPENDED)
        active_stores = Store.objects.active()
        pks = list(active_stores.values_list("pk", flat=True))
        assert active.pk in pks


@pytest.mark.django_db
class TestTenantTypeGuard:
    def test_tenant_type_change_allowed_when_no_orders(self):
        """tenant_type can change freely when store has no orders."""
        store = make_store(tenant_type=TenantType.RETAIL)
        store.tenant_type = TenantType.RESTAURANT
        # Should not raise — no orders exist
        store.save()
        store.refresh_from_db()
        assert store.tenant_type == TenantType.RESTAURANT

    def test_tenant_type_change_blocked_when_orders_exist(self):
        """tenant_type raises ValidationError if orders exist (FR4 guard)."""
        store = make_store(tenant_type=TenantType.RETAIL)

        # Patch Order queryset to simulate existing orders
        from unittest.mock import MagicMock, patch

        mock_qs = MagicMock()
        mock_qs.exists.return_value = True

        with patch("apps.order.models.Order.objects") as mock_objects:
            mock_objects.filter.return_value = mock_qs
            store.tenant_type = TenantType.RESTAURANT
            with pytest.raises(ValidationError, match="tenant_type cannot be changed"):
                store.save()

    def test_tenant_type_unchanged_no_validation_error(self):
        """Saving with same tenant_type never triggers the guard."""
        store = make_store(tenant_type=TenantType.RETAIL)
        # Change name only, same tenant_type
        store.name = "Updated Name"
        store.save()  # Should not raise
        store.refresh_from_db()
        assert store.name == "Updated Name"


@pytest.mark.django_db
class TestStoreRelatedModels:
    def test_store_settings_creation(self):
        """StoreSettings can be created with a store FK."""
        store = make_store()
        settings = StoreSettings.objects.create(store=store)
        assert settings.store == store
        assert str(store.name) in str(settings)

    def test_store_theme_creation(self):
        """StoreTheme can be created with a store FK."""
        store = make_store()
        theme = StoreTheme.objects.create(store=store)
        assert theme.store == store
