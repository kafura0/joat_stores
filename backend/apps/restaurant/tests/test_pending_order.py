"""
Tests for Story 3.7 — PendingOrder + Waiter Convert Screen.

Covers:
- AC1: Create PendingOrder → 6-digit PIN + expires_at 24h
- AC2: Celery purge task soft-deletes expired PENDING orders
- AC3: Waiter lookup by PIN or phone
- AC4: Convert PendingOrder → DineInOrder + KitchenTicket; status→CONVERTED
"""

import datetime
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.restaurant.models import DineInOrder, KitchenTicket, PendingOrder, TableSession
from apps.restaurant.tasks import purge_expired_pending_orders
from apps.restaurant.tests.factories import (
    MenuItemFactory,
    MenuSectionFactory,
    PendingOrderFactory,
    TableSessionFactory,
)
from apps.restaurant.views import (
    PendingOrderConvertView,
    PendingOrderCreateView,
    PendingOrderLookupView,
)
from apps.store.tests.factories import StoreFactory
from apps.users.tests.factories import UserFactory


# ---------------------------------------------------------------------------
# AC1: Create PendingOrder
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_pending_order_returns_pin():
    store = StoreFactory()
    section = MenuSectionFactory(store=store)
    item = MenuItemFactory(store=store, section=section, name="Ugali Fish", price=Decimal("300.00"))

    request = APIRequestFactory().post(
        "/pending-orders/",
        data={
            "phone": "+254712345678",
            "items": [{"menu_item_id": str(item.id), "quantity": 2, "selected_modifier_ids": []}],
        },
        format="json",
    )
    request.store = store

    response = PendingOrderCreateView.as_view()(request)

    assert response.status_code == 201
    data = response.data
    assert len(str(data["pin"])) == 6
    assert data["status"] == PendingOrder.STATUS_PENDING
    assert data["total_amount"] == "600.00"


@pytest.mark.django_db
def test_create_pending_order_expires_at_24h():
    store = StoreFactory()
    section = MenuSectionFactory(store=store)
    item = MenuItemFactory(store=store, section=section)

    before = timezone.now()
    request = APIRequestFactory().post(
        "/pending-orders/",
        data={"phone": "+254712345678", "items": [{"menu_item_id": str(item.id), "quantity": 1, "selected_modifier_ids": []}]},
        format="json",
    )
    request.store = store

    response = PendingOrderCreateView.as_view()(request)
    assert response.status_code == 201

    order = PendingOrder.objects.get(id=response.data["id"])
    delta = order.expires_at - before
    assert datetime.timedelta(hours=23, minutes=59) < delta <= datetime.timedelta(hours=24, minutes=1)


@pytest.mark.django_db
def test_create_pending_order_unavailable_item_400():
    store = StoreFactory()
    section = MenuSectionFactory(store=store)
    item = MenuItemFactory(store=store, section=section, is_available=False)

    request = APIRequestFactory().post(
        "/pending-orders/",
        data={"phone": "+254712345678", "items": [{"menu_item_id": str(item.id), "quantity": 1, "selected_modifier_ids": []}]},
        format="json",
    )
    request.store = store

    response = PendingOrderCreateView.as_view()(request)
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# AC2: Celery purge task
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_purge_task_soft_deletes_expired_pending():
    store = StoreFactory()
    expired = PendingOrderFactory(
        store=store,
        status=PendingOrder.STATUS_PENDING,
        expires_at=timezone.now() - datetime.timedelta(hours=1),
    )
    active = PendingOrderFactory(store=store, status=PendingOrder.STATUS_PENDING)

    result = purge_expired_pending_orders.apply()

    assert result.result["purged"] == 1
    # Expired order is soft-deleted — not retrievable via default manager
    assert not PendingOrder.objects.filter(id=expired.id).exists()
    # Active order unchanged
    assert PendingOrder.objects.filter(id=active.id).exists()


@pytest.mark.django_db
def test_purge_task_does_not_delete_paid_expired():
    store = StoreFactory()
    paid_expired = PendingOrderFactory(
        store=store,
        status=PendingOrder.STATUS_PAID,
        expires_at=timezone.now() - datetime.timedelta(hours=1),
    )

    result = purge_expired_pending_orders.apply()

    # PAID orders not purged — flagged for review
    assert result.result["purged"] == 0
    assert PendingOrder.objects.filter(id=paid_expired.id).exists()
    assert result.result["paid_expired_flagged"] == 1


# ---------------------------------------------------------------------------
# AC3: Waiter lookup
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_lookup_by_pin_returns_order():
    store = StoreFactory()
    order = PendingOrderFactory(store=store, pin="123456")
    user = UserFactory()

    request = APIRequestFactory().get("/pending-orders/lookup/", {"pin": "123456"})
    request.store = store
    force_authenticate(request, user=user)

    response = PendingOrderLookupView.as_view()(request)

    assert response.status_code == 200
    assert str(response.data["id"]) == str(order.id)
    assert response.data["pin"] == "123456"


@pytest.mark.django_db
def test_lookup_by_phone_returns_order():
    store = StoreFactory()
    order = PendingOrderFactory(store=store, phone="+254712999888")
    user = UserFactory()

    request = APIRequestFactory().get("/pending-orders/lookup/", {"phone": "+254712999888"})
    request.store = store
    force_authenticate(request, user=user)

    response = PendingOrderLookupView.as_view()(request)

    assert response.status_code == 200
    assert str(response.data["id"]) == str(order.id)


@pytest.mark.django_db
def test_lookup_converted_order_not_found():
    store = StoreFactory()
    PendingOrderFactory(store=store, pin="999999", status=PendingOrder.STATUS_CONVERTED)
    user = UserFactory()

    request = APIRequestFactory().get("/pending-orders/lookup/", {"pin": "999999"})
    request.store = store
    force_authenticate(request, user=user)

    response = PendingOrderLookupView.as_view()(request)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# AC4: Convert PendingOrder → DineInOrder + KitchenTicket
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_convert_creates_dineinorder_and_ticket():
    store = StoreFactory()
    waiter = UserFactory(first_name="Bob", last_name="Waiter")
    session = TableSessionFactory(store=store, assigned_waiter=waiter)
    pending = PendingOrderFactory(store=store)
    user = UserFactory()

    request = APIRequestFactory().post(
        f"/pending-orders/{pending.id}/convert/",
        data={"session_id": str(session.id)},
        format="json",
    )
    request.store = store
    force_authenticate(request, user=user)

    response = PendingOrderConvertView.as_view()(request, order_id=str(pending.id))

    assert response.status_code == 201
    pending.refresh_from_db()
    assert pending.status == PendingOrder.STATUS_CONVERTED
    assert pending.converted_order is not None

    order = DineInOrder.objects.get(id=pending.converted_order_id)
    assert order.session == session
    assert order.total_amount == pending.total_amount

    ticket = KitchenTicket.objects.get(order=order)
    assert ticket.waiter_name == "Bob Waiter"
    assert ticket.table_number == session.table.number


@pytest.mark.django_db
def test_convert_with_closed_session_returns_404():
    store = StoreFactory()
    session = TableSessionFactory(store=store, status=TableSession.STATUS_CLOSED)
    pending = PendingOrderFactory(store=store)
    user = UserFactory()

    request = APIRequestFactory().post(
        f"/pending-orders/{pending.id}/convert/",
        data={"session_id": str(session.id)},
        format="json",
    )
    request.store = store
    force_authenticate(request, user=user)

    response = PendingOrderConvertView.as_view()(request, order_id=str(pending.id))
    assert response.status_code == 404


@pytest.mark.django_db
def test_convert_already_converted_order_returns_404():
    store = StoreFactory()
    session = TableSessionFactory(store=store)
    pending = PendingOrderFactory(store=store, status=PendingOrder.STATUS_CONVERTED)
    user = UserFactory()

    request = APIRequestFactory().post(
        f"/pending-orders/{pending.id}/convert/",
        data={"session_id": str(session.id)},
        format="json",
    )
    request.store = store
    force_authenticate(request, user=user)

    response = PendingOrderConvertView.as_view()(request, order_id=str(pending.id))
    assert response.status_code == 404
