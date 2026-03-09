"""
Tests for core.querysets.TenantQuerySet.

Uses StoreSettings (a concrete TenantModel subclass) to exercise the queryset
without creating a dedicated test model.

Cross-tenant tests named with 'cross_tenant' — picked up by:
    pytest -k cross_tenant   (CI enforcement gate)
"""

import uuid

import pytest

from apps.store.models import Store, StoreSettings, StoreStatus, TenantType


def make_store(**kwargs):
    defaults = {
        "name": "Test Store",
        "slug": f"qs-{uuid.uuid4().hex[:8]}",
        "domain": f"qs-{uuid.uuid4().hex[:8]}.joat.com",
        "tenant_type": TenantType.RETAIL,
        "status": StoreStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Store.objects.create(**defaults)


@pytest.mark.django_db
class TestTenantQuerySet:
    def test_for_store_returns_own_records(self):
        """for_store() returns only records belonging to the given store."""
        store_a = make_store()
        store_b = make_store()
        settings_a = StoreSettings.objects.create(store=store_a)
        StoreSettings.objects.create(store=store_b)

        qs = StoreSettings.objects.for_store(store_a)
        pks = list(qs.values_list("pk", flat=True))
        assert settings_a.pk in pks
        assert len(pks) == 1

    def test_for_store_empty_when_no_records(self):
        """for_store() returns empty queryset when store has no records."""
        store = make_store()
        qs = StoreSettings.objects.for_store(store)
        assert qs.count() == 0

    def test_for_store_filters_by_store_pk(self):
        """for_store() uses store.pk — UUID comparison works correctly."""
        store = make_store()
        settings = StoreSettings.objects.create(store=store)
        qs = StoreSettings.objects.for_store(store)
        assert qs.filter(pk=settings.pk).exists()

    def test_cross_tenant_isolation_queryset_never_leaks_records(self):
        """
        TenantQuerySet scoped to store_a never returns store_b records.
        CI gate: pytest -k cross_tenant
        """
        store_a = make_store()
        store_b = make_store()
        StoreSettings.objects.create(store=store_b)

        qs = StoreSettings.objects.for_store(store_a)
        assert qs.count() == 0
        assert not qs.filter(store=store_b).exists()

    def test_cross_tenant_queryset_get_raises_does_not_exist(self):
        """
        .for_store(store_a).get(pk=store_b_record) raises DoesNotExist.
        CI gate: pytest -k cross_tenant
        """
        store_a = make_store()
        store_b = make_store()
        settings_b = StoreSettings.objects.create(store=store_b)

        with pytest.raises(StoreSettings.DoesNotExist):
            StoreSettings.objects.for_store(store_a).get(pk=settings_b.pk)

    def test_cross_tenant_isolation_multiple_stores_isolated(self):
        """
        Each store's queryset is fully isolated from every other store.
        CI gate: pytest -k cross_tenant
        """
        stores = [make_store() for _ in range(3)]
        settings_list = [StoreSettings.objects.create(store=s) for s in stores]

        for i, store in enumerate(stores):
            qs = StoreSettings.objects.for_store(store)
            pks = list(qs.values_list("pk", flat=True))
            assert settings_list[i].pk in pks
            for j, other_settings in enumerate(settings_list):
                if i != j:
                    assert other_settings.pk not in pks

    def test_tenant_model_has_uuid_primary_key(self):
        """TenantModel subclasses use UUID PK — not integer."""
        store = make_store()
        settings = StoreSettings.objects.create(store=store)
        assert isinstance(settings.pk, uuid.UUID)
