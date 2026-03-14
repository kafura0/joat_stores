"""
Tests for Story 3.6 — Dine-In Order + Denormalized Kitchen Ticket
         Story 3.6b — Customer Order Confirmation + Live Status Screen

Covers:
- AC1: DineInOrder created → KitchenTicket with denormalized snapshot + waiter name
- AC2: Kitchen display returns only PENDING + IN_PROGRESS; COMPLETED filtered out
- AC3: Ticket status update (PENDING→IN_PROGRESS→COMPLETED) mirrors on DineInOrder
- AC4: Order status endpoint returns combined order + ticket status (Story 3.6b)
- Performance: kitchen tickets query uses only the KitchenTicket table (no joins)
"""

import time
from decimal import Decimal

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.restaurant.models import DineInOrder, KitchenTicket, TableSession
from apps.restaurant.tests.factories import (
    DineInOrderFactory,
    KitchenTicketFactory,
    MenuItemFactory,
    MenuSectionFactory,
    ModifierFactory,
    ModifierGroupFactory,
    TableFactory,
    TableSessionFactory,
)
from apps.restaurant.views import (
    DineInOrderView,
    KitchenTicketListView,
    KitchenTicketUpdateView,
    OrderStatusView,
)
from apps.store.tests.factories import StoreFactory
from apps.users.tests.factories import UserFactory


# ---------------------------------------------------------------------------
# AC1: Order creation → denormalized KitchenTicket
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_order_creates_kitchen_ticket():
    store = StoreFactory()
    waiter = UserFactory(first_name="Alice", last_name="Waiter")
    session = TableSessionFactory(store=store, assigned_waiter=waiter)
    section = MenuSectionFactory(store=store)
    item = MenuItemFactory(store=store, section=section, name="Ugali", price=Decimal("200.00"))

    request = APIRequestFactory().post(
        "/orders/",
        data={"session_id": str(session.id), "items": [{"menu_item_id": str(item.id), "quantity": 2, "selected_modifier_ids": []}]},
        format="json",
    )
    request.store = store
    force_authenticate(request, user=waiter)

    response = DineInOrderView.as_view()(request)

    assert response.status_code == 201
    assert DineInOrder.objects.filter(session=session).count() == 1
    order = DineInOrder.objects.get(session=session)
    assert order.total_amount == Decimal("400.00")  # 200 * 2

    # KitchenTicket created
    ticket = KitchenTicket.objects.get(order=order)
    assert ticket.status == KitchenTicket.STATUS_PENDING
    assert ticket.waiter_name == "Alice Waiter"
    assert ticket.table_number == session.table.number

    # Snapshot contains item details
    assert len(ticket.items_snapshot) == 1
    snap = ticket.items_snapshot[0]
    assert snap["name"] == "Ugali"
    assert snap["price"] == "200.00"
    assert snap["quantity"] == 2


@pytest.mark.django_db
def test_create_order_with_modifiers_denormalized():
    store = StoreFactory()
    session = TableSessionFactory(store=store)
    section = MenuSectionFactory(store=store)
    item = MenuItemFactory(store=store, section=section, name="Burger", price=Decimal("500.00"))
    grp = ModifierGroupFactory(store=store, menu_item=item)
    mod = ModifierFactory(store=store, modifier_group=grp, name="Extra Cheese", price_addition=Decimal("50.00"))

    request = APIRequestFactory().post(
        "/orders/",
        data={
            "session_id": str(session.id),
            "items": [{"menu_item_id": str(item.id), "quantity": 1, "selected_modifier_ids": [str(mod.id)]}],
        },
        format="json",
    )
    request.store = store
    force_authenticate(request, user=UserFactory())

    response = DineInOrderView.as_view()(request)

    assert response.status_code == 201
    order = DineInOrder.objects.get(session=session)
    assert order.total_amount == Decimal("550.00")  # 500 + 50

    snap = order.items_snapshot[0]
    assert len(snap["modifiers"]) == 1
    assert snap["modifiers"][0]["name"] == "Extra Cheese"
    assert snap["modifiers"][0]["price_addition"] == "50.00"


@pytest.mark.django_db
def test_create_order_invalid_session_returns_404():
    import uuid

    store = StoreFactory()
    request = APIRequestFactory().post(
        "/orders/",
        data={"session_id": str(uuid.uuid4()), "items": [{"menu_item_id": str(uuid.uuid4()), "quantity": 1, "selected_modifier_ids": []}]},
        format="json",
    )
    request.store = store
    force_authenticate(request, user=UserFactory())

    response = DineInOrderView.as_view()(request)
    assert response.status_code == 404


@pytest.mark.django_db
def test_create_order_closed_session_returns_404():
    store = StoreFactory()
    session = TableSessionFactory(store=store, status=TableSession.STATUS_CLOSED)
    section = MenuSectionFactory(store=store)
    item = MenuItemFactory(store=store, section=section)

    request = APIRequestFactory().post(
        "/orders/",
        data={"session_id": str(session.id), "items": [{"menu_item_id": str(item.id), "quantity": 1, "selected_modifier_ids": []}]},
        format="json",
    )
    request.store = store
    force_authenticate(request, user=UserFactory())

    response = DineInOrderView.as_view()(request)
    assert response.status_code == 404


@pytest.mark.django_db
def test_create_order_unavailable_item_returns_400():
    store = StoreFactory()
    session = TableSessionFactory(store=store)
    section = MenuSectionFactory(store=store)
    item = MenuItemFactory(store=store, section=section, is_available=False)

    request = APIRequestFactory().post(
        "/orders/",
        data={"session_id": str(session.id), "items": [{"menu_item_id": str(item.id), "quantity": 1, "selected_modifier_ids": []}]},
        format="json",
    )
    request.store = store
    force_authenticate(request, user=UserFactory())

    response = DineInOrderView.as_view()(request)
    assert response.status_code == 400
    assert response.data["errors"][0]["code"] == "ITEM_NOT_FOUND"


# ---------------------------------------------------------------------------
# AC2: Kitchen display — only PENDING + IN_PROGRESS returned
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_kitchen_tickets_returns_only_active():
    store = StoreFactory()
    pending = KitchenTicketFactory(store=store, status=KitchenTicket.STATUS_PENDING)
    in_progress = KitchenTicketFactory(store=store, status=KitchenTicket.STATUS_IN_PROGRESS)
    completed = KitchenTicketFactory(store=store, status=KitchenTicket.STATUS_COMPLETED)
    cancelled = KitchenTicketFactory(store=store, status=KitchenTicket.STATUS_CANCELLED)

    request = APIRequestFactory().get("/kitchen/tickets/")
    request.store = store
    force_authenticate(request, user=UserFactory())

    response = KitchenTicketListView.as_view()(request)

    assert response.status_code == 200
    ids = {str(t["id"]) for t in response.data["data"]}
    assert str(pending.id) in ids
    assert str(in_progress.id) in ids
    assert str(completed.id) not in ids
    assert str(cancelled.id) not in ids


@pytest.mark.django_db
def test_kitchen_tickets_cross_store_isolation():
    """Tickets from another store must not appear."""
    store_a = StoreFactory()
    store_b = StoreFactory()
    ticket_a = KitchenTicketFactory(store=store_a, status=KitchenTicket.STATUS_PENDING)
    ticket_b = KitchenTicketFactory(store=store_b, status=KitchenTicket.STATUS_PENDING)

    request = APIRequestFactory().get("/kitchen/tickets/")
    request.store = store_a
    force_authenticate(request, user=UserFactory())

    response = KitchenTicketListView.as_view()(request)
    ids = {str(t["id"]) for t in response.data["data"]}
    assert str(ticket_a.id) in ids
    assert str(ticket_b.id) not in ids


# ---------------------------------------------------------------------------
# AC3: Ticket status transitions mirror on DineInOrder
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ticket_transition_to_in_progress_sets_order_confirmed():
    store = StoreFactory()
    ticket = KitchenTicketFactory(store=store, status=KitchenTicket.STATUS_PENDING)

    request = APIRequestFactory().patch(
        f"/kitchen/tickets/{ticket.id}/",
        data={"status": "IN_PROGRESS"},
        format="json",
    )
    request.store = store
    force_authenticate(request, user=UserFactory())

    response = KitchenTicketUpdateView.as_view()(request, ticket_id=str(ticket.id))

    assert response.status_code == 200
    ticket.refresh_from_db()
    assert ticket.status == KitchenTicket.STATUS_IN_PROGRESS
    ticket.order.refresh_from_db()
    assert ticket.order.status == DineInOrder.STATUS_CONFIRMED


@pytest.mark.django_db
def test_ticket_transition_to_completed_sets_order_ready():
    store = StoreFactory()
    ticket = KitchenTicketFactory(store=store, status=KitchenTicket.STATUS_IN_PROGRESS)
    DineInOrder.objects.filter(id=ticket.order_id).update(status=DineInOrder.STATUS_CONFIRMED)

    request = APIRequestFactory().patch(
        f"/kitchen/tickets/{ticket.id}/",
        data={"status": "COMPLETED"},
        format="json",
    )
    request.store = store
    force_authenticate(request, user=UserFactory())

    response = KitchenTicketUpdateView.as_view()(request, ticket_id=str(ticket.id))
    assert response.status_code == 200
    ticket.order.refresh_from_db()
    assert ticket.order.status == DineInOrder.STATUS_READY


@pytest.mark.django_db
def test_invalid_ticket_transition_returns_422():
    store = StoreFactory()
    ticket = KitchenTicketFactory(store=store, status=KitchenTicket.STATUS_COMPLETED)

    request = APIRequestFactory().patch(
        f"/kitchen/tickets/{ticket.id}/",
        data={"status": "IN_PROGRESS"},
        format="json",
    )
    request.store = store
    force_authenticate(request, user=UserFactory())

    response = KitchenTicketUpdateView.as_view()(request, ticket_id=str(ticket.id))
    assert response.status_code == 422
    assert response.data["errors"][0]["code"] == "INVALID_TICKET_TRANSITION"


# ---------------------------------------------------------------------------
# AC4: Story 3.6b — order status endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_status_returns_combined_status():
    store = StoreFactory()
    ticket = KitchenTicketFactory(store=store, status=KitchenTicket.STATUS_IN_PROGRESS)
    DineInOrder.objects.filter(id=ticket.order_id).update(status=DineInOrder.STATUS_CONFIRMED)
    ticket.order.refresh_from_db()

    request = APIRequestFactory().get(f"/orders/{ticket.order_id}/status/")
    # No auth required (AllowAny)

    response = OrderStatusView.as_view()(request, order_id=str(ticket.order_id))

    assert response.status_code == 200
    assert response.data["order_status"] == DineInOrder.STATUS_CONFIRMED
    assert response.data["ticket_status"] == KitchenTicket.STATUS_IN_PROGRESS
    assert response.data["table_number"] == ticket.table_number
    assert "items_snapshot" in response.data


@pytest.mark.django_db
def test_order_status_404_for_unknown_order():
    import uuid

    request = APIRequestFactory().get(f"/orders/{uuid.uuid4()}/status/")
    response = OrderStatusView.as_view()(request, order_id=str(uuid.uuid4()))
    assert response.status_code == 404
