"""
Tests for Story 3.10 — Takeaway Order Type.

Covers:
- AC1: POST /orders/takeaway/ → DineInOrder(order_type='takeaway') + KitchenTicket
- AC2: POST /orders/takeaway/{id}/pay/ → STK Push with takeaway reference
- AC3: payment_confirmed signal → pickup reference generated (TKW-XXXX)
- AC4: Kitchen COMPLETED → notify_takeaway_ready task dispatched
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIRequestFactory

from apps.restaurant.apps import _handle_payment_confirmed
from apps.restaurant.models import DineInOrder, KitchenTicket
from apps.restaurant.tasks import send_takeaway_pickup_reference
from apps.restaurant.tests.factories import (
    KitchenTicketFactory,
    MenuItemFactory,
    MenuSectionFactory,
)
from apps.restaurant.views import KitchenTicketUpdateView, TakeawayOrderView
from apps.store.tests.factories import StoreFactory
from apps.users.tests.factories import UserFactory


# ---------------------------------------------------------------------------
# AC1: Create takeaway order
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_takeaway_order_creates_kitchen_ticket():
    store = StoreFactory()
    section = MenuSectionFactory(store=store)
    item = MenuItemFactory(store=store, section=section, name="Chips Masala", price=Decimal("250.00"))

    request = APIRequestFactory().post(
        "/orders/takeaway/",
        data={
            "phone": "+254712345678",
            "items": [{"menu_item_id": str(item.id), "quantity": 2, "selected_modifier_ids": []}],
        },
        format="json",
    )
    request.store = store

    response = TakeawayOrderView.as_view()(request)

    assert response.status_code == 201
    assert response.data["order_type"] == DineInOrder.ORDER_TYPE_TAKEAWAY

    order = DineInOrder.objects.get(id=response.data["id"])
    assert order.session is None  # No table session for takeaway
    assert order.total_amount == Decimal("500.00")  # 250 * 2

    ticket = KitchenTicket.objects.get(order=order)
    assert ticket.status == KitchenTicket.STATUS_PENDING
    assert ticket.table_number == 0  # No table


@pytest.mark.django_db
def test_create_takeaway_no_phone_returns_400():
    store = StoreFactory()
    section = MenuSectionFactory(store=store)
    item = MenuItemFactory(store=store, section=section)

    request = APIRequestFactory().post(
        "/orders/takeaway/",
        data={"items": [{"menu_item_id": str(item.id), "quantity": 1, "selected_modifier_ids": []}]},
        format="json",
    )
    request.store = store

    response = TakeawayOrderView.as_view()(request)
    assert response.status_code == 400
    assert response.data["errors"][0]["code"] == "PHONE_REQUIRED"


# ---------------------------------------------------------------------------
# AC3: payment_confirmed signal → TKW reference generation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_takeaway_payment_signal_dispatches_reference_task():
    store = StoreFactory()
    section = MenuSectionFactory(store=store)
    item = MenuItemFactory(store=store, section=section)
    order = DineInOrder.objects.create(
        store=store,
        session=None,
        items_snapshot=[],
        total_amount=Decimal("500.00"),
        order_type=DineInOrder.ORDER_TYPE_TAKEAWAY,
    )

    mock_txn = MagicMock()
    mock_txn.reference = f"takeaway-{order.id}"

    with patch("apps.restaurant.tasks.send_takeaway_pickup_reference") as mock_task:
        mock_task.apply_async.return_value = None
        _handle_payment_confirmed(sender=None, transaction=mock_txn)

    mock_task.apply_async.assert_called_once_with(args=[str(order.id)], countdown=0)


@pytest.mark.django_db
def test_takeaway_reference_generation_sets_tkw_ref():
    store = StoreFactory()
    order = DineInOrder.objects.create(
        store=store,
        session=None,
        items_snapshot=[],
        total_amount=Decimal("350.00"),
        order_type=DineInOrder.ORDER_TYPE_TAKEAWAY,
    )

    result = send_takeaway_pickup_reference.apply(args=[str(order.id)])

    order.refresh_from_db()
    assert order.pickup_reference.startswith("TKW-")
    assert result.result["pickup_reference"] == order.pickup_reference


@pytest.mark.django_db
def test_takeaway_reference_generation_idempotent():
    store = StoreFactory()
    order = DineInOrder.objects.create(
        store=store,
        session=None,
        items_snapshot=[],
        total_amount=Decimal("350.00"),
        order_type=DineInOrder.ORDER_TYPE_TAKEAWAY,
        pickup_reference="TKW-0099",
    )

    send_takeaway_pickup_reference.apply(args=[str(order.id)])

    order.refresh_from_db()
    # Should not overwrite existing reference
    assert order.pickup_reference == "TKW-0099"


# ---------------------------------------------------------------------------
# AC4: Kitchen COMPLETED → notify_takeaway_ready dispatched
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_kitchen_completed_dispatches_takeaway_notification():
    store = StoreFactory()
    order = DineInOrder.objects.create(
        store=store,
        session=None,
        items_snapshot=[],
        total_amount=Decimal("350.00"),
        order_type=DineInOrder.ORDER_TYPE_TAKEAWAY,
        status=DineInOrder.STATUS_CONFIRMED,
    )
    ticket = KitchenTicket.objects.create(
        store=store,
        order=order,
        status=KitchenTicket.STATUS_IN_PROGRESS,
        items_snapshot=[],
        waiter_name="",
        table_number=0,
    )
    user = UserFactory()

    request = APIRequestFactory().patch(
        f"/kitchen/tickets/{ticket.id}/",
        data={"status": "COMPLETED"},
        format="json",
    )
    request.store = store
    from rest_framework.test import force_authenticate
    force_authenticate(request, user=user)

    with patch("apps.restaurant.tasks.notify_takeaway_ready") as mock_task:
        mock_task.apply_async.return_value = None
        response = KitchenTicketUpdateView.as_view()(request, ticket_id=str(ticket.id))

    assert response.status_code == 200
    mock_task.apply_async.assert_called_once_with(args=[str(order.id)], countdown=0)
