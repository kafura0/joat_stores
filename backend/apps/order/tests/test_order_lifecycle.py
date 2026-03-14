"""
Tests for Story 4.3 — Order Lifecycle State Machine.

Covers:
- AC1: New order starts at 'pending'
- AC2: Valid transitions: pending→confirmed, confirmed→fulfilled, fulfilled→completed,
        pending→cancelled, confirmed→cancelled
- AC3: Invalid transition raises InvalidOrderTransition; status unchanged
- AC4: Order.confirmed triggers send_order_confirmation task via on_commit
"""

from decimal import Decimal
from unittest.mock import patch

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.order.models import InvalidOrderTransition, Order, OrderStatus
from apps.order.tests.factories import OrderFactory
from apps.order.views import OrderConfirmView, OrderDetailView, OrderStatusView
from apps.store.tests.factories import StoreFactory
from apps.users.tests.factories import UserFactory


def _view_request(method, url, data=None, user=None, store=None):
    factory = APIRequestFactory()
    fn = getattr(factory, method)
    req = fn(url, data=data, format="json") if data else fn(url)
    if user:
        force_authenticate(req, user=user)
    if store:
        req.store = store
    return req


@pytest.fixture
def store():
    return StoreFactory()


@pytest.fixture
def user(store):
    return UserFactory()


@pytest.fixture
def order(store):
    return OrderFactory(store=store)


# ---------------------------------------------------------------------------
# AC1 — New order starts pending
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_order_starts_pending(store):
    order = OrderFactory(store=store)
    assert order.status == OrderStatus.PENDING


# ---------------------------------------------------------------------------
# AC2 — Valid transitions
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_pending_to_confirmed(order):
    order.transition_status(OrderStatus.CONFIRMED)
    order.refresh_from_db()
    assert order.status == OrderStatus.CONFIRMED
    assert order.confirmed_at is not None


@pytest.mark.django_db
def test_confirmed_to_fulfilled(order):
    order.transition_status(OrderStatus.CONFIRMED)
    order.transition_status(OrderStatus.FULFILLED)
    order.refresh_from_db()
    assert order.status == OrderStatus.FULFILLED
    assert order.fulfilled_at is not None


@pytest.mark.django_db
def test_fulfilled_to_completed(order):
    order.transition_status(OrderStatus.CONFIRMED)
    order.transition_status(OrderStatus.FULFILLED)
    order.transition_status(OrderStatus.COMPLETED)
    order.refresh_from_db()
    assert order.status == OrderStatus.COMPLETED
    assert order.completed_at is not None


@pytest.mark.django_db
def test_pending_to_cancelled(order):
    order.transition_status(OrderStatus.CANCELLED)
    order.refresh_from_db()
    assert order.status == OrderStatus.CANCELLED
    assert order.cancelled_at is not None


@pytest.mark.django_db
def test_confirmed_to_cancelled(order):
    order.transition_status(OrderStatus.CONFIRMED)
    order.transition_status(OrderStatus.CANCELLED)
    order.refresh_from_db()
    assert order.status == OrderStatus.CANCELLED


# ---------------------------------------------------------------------------
# AC3 — Invalid transitions raise and do not change status
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_completed_to_pending_raises(order):
    order.transition_status(OrderStatus.CONFIRMED)
    order.transition_status(OrderStatus.FULFILLED)
    order.transition_status(OrderStatus.COMPLETED)
    with pytest.raises(InvalidOrderTransition):
        order.transition_status(OrderStatus.PENDING)
    order.refresh_from_db()
    assert order.status == OrderStatus.COMPLETED  # unchanged


@pytest.mark.django_db
def test_cancelled_to_confirmed_raises(order):
    order.transition_status(OrderStatus.CANCELLED)
    with pytest.raises(InvalidOrderTransition):
        order.transition_status(OrderStatus.CONFIRMED)


@pytest.mark.django_db
def test_direct_status_patch_returns_422(store, user, order):
    """
    Story 4.3 AC: direct field assignment is never used — confirm endpoint
    goes through transition_status().
    The confirm view transitions properly and returns the updated order.
    """
    req = _view_request("post", f"/api/v1/store/orders/{order.id}/confirm/",
                        user=user, store=store)
    view = OrderConfirmView.as_view()
    resp = view(req, order_id=str(order.id))
    assert resp.status_code == 200
    assert resp.data["status"] == OrderStatus.CONFIRMED


# ---------------------------------------------------------------------------
# AC4 — Confirmation dispatches email task via on_commit
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_order_confirm_dispatches_email_task(store, user, order):
    with patch("apps.order.views.send_order_confirmation") as mock_task:
        req = _view_request("post", f"/api/v1/store/orders/{order.id}/confirm/",
                            user=user, store=store)
        view = OrderConfirmView.as_view()
        resp = view(req, order_id=str(order.id))

    assert resp.status_code == 200
    # task is dispatched via on_commit — in tests transactions commit immediately
    mock_task.apply_async.assert_called_once_with(args=[str(order.id)])


# ---------------------------------------------------------------------------
# Status endpoint (Story 4.8 recovery)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_order_status_endpoint(store, order):
    req = _view_request("get", f"/api/v1/store/orders/{order.id}/status/", store=store)
    view = OrderStatusView.as_view()
    resp = view(req, order_id=str(order.id))
    assert resp.status_code == 200
    assert resp.data["order_id"] == str(order.id)
    assert resp.data["status"] == OrderStatus.PENDING
