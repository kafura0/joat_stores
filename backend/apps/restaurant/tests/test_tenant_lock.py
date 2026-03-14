"""
Story 3.12 — FR4 Cross-Epic Tenant Type Lock Test.

FR4: tenant_type is locked after the first order is placed.
Store.save() raises ValidationError when tenant_type changes on a store with
existing DineInOrders (or any other order type in future epics).

Tests are tagged with 'cross_tenant' per NFR3 — must pass on every PR
touching models or views.
"""

import pytest
from django.core.exceptions import ValidationError

from apps.restaurant.models import DineInOrder
from apps.restaurant.tests.factories import DineInOrderFactory, TableSessionFactory, TableFactory
from apps.store.models import Store, TenantType
from apps.store.tests.factories import StoreFactory


@pytest.mark.django_db
@pytest.mark.cross_tenant
def test_tenant_type_locked_after_first_dine_in_order():
    """
    FR4 cross-epic AC: changing tenant_type after a DineInOrder exists raises
    ValidationError.
    """
    store = StoreFactory(tenant_type=TenantType.RESTAURANT)
    table = TableFactory(store=store)
    session = TableSessionFactory(table=table)
    DineInOrderFactory(session=session, store=store)

    store.tenant_type = TenantType.RETAIL

    with pytest.raises(ValidationError, match="tenant_type cannot be changed after orders exist"):
        store.save()


@pytest.mark.django_db
@pytest.mark.cross_tenant
def test_tenant_type_can_change_before_any_orders():
    """
    FR4: tenant_type CAN be changed before any orders exist — no lock yet.
    """
    store = StoreFactory(tenant_type=TenantType.RETAIL)
    store.tenant_type = TenantType.RESTAURANT
    store.save()  # Should not raise

    store.refresh_from_db()
    assert store.tenant_type == TenantType.RESTAURANT


@pytest.mark.django_db
@pytest.mark.cross_tenant
def test_tenant_type_not_locked_when_saving_same_type():
    """
    FR4: saving the same tenant_type on a store with orders must not raise.
    """
    store = StoreFactory(tenant_type=TenantType.RESTAURANT)
    table = TableFactory(store=store)
    session = TableSessionFactory(table=table)
    DineInOrderFactory(session=session, store=store)

    # No type change — should succeed
    store.name = "Updated Restaurant Name"
    store.save()  # Should not raise


@pytest.mark.django_db
@pytest.mark.cross_tenant
def test_tenant_type_lock_is_per_store():
    """
    FR4: lock is per-store — another store's DineInOrder does not affect
    this store's ability to change tenant_type.
    """
    store_a = StoreFactory(tenant_type=TenantType.RESTAURANT)
    table_a = TableFactory(store=store_a)
    session_a = TableSessionFactory(table=table_a)
    DineInOrderFactory(session=session_a, store=store_a)

    store_b = StoreFactory(tenant_type=TenantType.RETAIL)
    # store_b has no orders
    store_b.tenant_type = TenantType.RESTAURANT
    store_b.save()  # Should not raise — store_a's orders don't affect store_b

    store_b.refresh_from_db()
    assert store_b.tenant_type == TenantType.RESTAURANT


@pytest.mark.django_db
@pytest.mark.cross_tenant
def test_fr4_guard_covers_all_dine_in_order_types():
    """
    FR4 must fire for takeaway DineInOrders (session=None) too.
    """
    store = StoreFactory(tenant_type=TenantType.RESTAURANT)
    # Takeaway order: no session
    DineInOrder.objects.create(
        store=store,
        session=None,
        items_snapshot=[],
        total_amount="100.00",
        order_type=DineInOrder.ORDER_TYPE_TAKEAWAY,
    )

    store.tenant_type = TenantType.RETAIL
    with pytest.raises(ValidationError, match="tenant_type cannot be changed after orders exist"):
        store.save()
