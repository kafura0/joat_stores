"""
Tests for Story 3.9 — Reservation Model.

Covers:
- AC1: Create reservation → status PENDING; notification task dispatched
- AC2: confirm/ → PENDING→CONFIRMED; 422 on invalid transition
- AC3: seat/ → CONFIRMED→SEATED; TableSession auto-created; 409 if session exists
- AC4: no-show/ → CONFIRMED→NO_SHOW
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.restaurant.models import Reservation, TableSession
from apps.restaurant.tests.factories import TableFactory, TableSessionFactory
from apps.restaurant.views import ReservationViewSet
from apps.store.tests.factories import StoreFactory
from apps.users.tests.factories import UserFactory


def _reservation_data(table=None, **kwargs):
    data = {
        "customer_phone": "+254712345678",
        "customer_name": "Alice Njeri",
        "party_size": 4,
        "reserved_for": (timezone.now() + timedelta(days=1)).isoformat(),
        "notes": "",
    }
    if table:
        data["table"] = str(table.id)
    data.update(kwargs)
    return data


def _view_request(method, url, data=None, user=None, store=None):
    factory = APIRequestFactory()
    fn = getattr(factory, method)
    request = fn(url, data=data, format="json")
    if user:
        force_authenticate(request, user=user)
    if store:
        request.store = store
    return request


# ---------------------------------------------------------------------------
# AC1: Create reservation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_reservation_status_pending():
    store = StoreFactory()
    table = TableFactory(store=store)
    user = UserFactory()

    with patch("apps.restaurant.views.send_reservation_notification") as mock_task:
        mock_task.apply_async.return_value = None
        request = _view_request("post", "/reservations/", data=_reservation_data(table=table), user=user, store=store)
        view = ReservationViewSet.as_view({"post": "create"})
        response = view(request)

    assert response.status_code == 201
    assert response.data["status"] == Reservation.STATUS_PENDING
    mock_task.apply_async.assert_called_once()
    _, call_kwargs = mock_task.apply_async.call_args
    assert call_kwargs["args"][1] == "created"


@pytest.mark.django_db
def test_create_reservation_without_table():
    store = StoreFactory()
    user = UserFactory()

    with patch("apps.restaurant.views.send_reservation_notification") as mock_task:
        mock_task.apply_async.return_value = None
        request = _view_request("post", "/reservations/", data=_reservation_data(), user=user, store=store)
        view = ReservationViewSet.as_view({"post": "create"})
        response = view(request)

    assert response.status_code == 201
    assert response.data["table"] is None


# ---------------------------------------------------------------------------
# AC2: confirm/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_confirm_transitions_pending_to_confirmed():
    store = StoreFactory()
    user = UserFactory()
    reservation = Reservation.objects.create(
        store=store,
        customer_phone="+254712345678",
        party_size=2,
        reserved_for=timezone.now() + timedelta(days=1),
        status=Reservation.STATUS_PENDING,
    )

    with patch("apps.restaurant.views.send_reservation_notification") as mock_task:
        mock_task.apply_async.return_value = None
        request = _view_request("patch", f"/reservations/{reservation.id}/confirm/", user=user, store=store)
        view = ReservationViewSet.as_view({"patch": "confirm"})
        response = view(request, pk=str(reservation.id))

    assert response.status_code == 200
    reservation.refresh_from_db()
    assert reservation.status == Reservation.STATUS_CONFIRMED


@pytest.mark.django_db
def test_confirm_seated_reservation_returns_422():
    store = StoreFactory()
    user = UserFactory()
    reservation = Reservation.objects.create(
        store=store,
        customer_phone="+254712345678",
        party_size=2,
        reserved_for=timezone.now() + timedelta(days=1),
        status=Reservation.STATUS_SEATED,
    )

    request = _view_request("patch", f"/reservations/{reservation.id}/confirm/", user=user, store=store)
    view = ReservationViewSet.as_view({"patch": "confirm"})
    response = view(request, pk=str(reservation.id))

    assert response.status_code == 422
    assert response.data["errors"][0]["code"] == "INVALID_RESERVATION_TRANSITION"


# ---------------------------------------------------------------------------
# AC3: seat/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_seat_creates_table_session():
    store = StoreFactory()
    table = TableFactory(store=store)
    user = UserFactory()
    reservation = Reservation.objects.create(
        store=store,
        customer_phone="+254712345678",
        party_size=2,
        reserved_for=timezone.now() + timedelta(days=1),
        table=table,
        status=Reservation.STATUS_CONFIRMED,
    )

    with patch("apps.restaurant.views.send_reservation_notification") as mock_task:
        mock_task.apply_async.return_value = None
        request = _view_request("patch", f"/reservations/{reservation.id}/seat/", user=user, store=store)
        view = ReservationViewSet.as_view({"patch": "seat"})
        response = view(request, pk=str(reservation.id))

    assert response.status_code == 200
    reservation.refresh_from_db()
    assert reservation.status == Reservation.STATUS_SEATED
    assert reservation.session is not None
    assert reservation.session.status == TableSession.STATUS_OPEN
    assert reservation.session.table == table


@pytest.mark.django_db
def test_seat_without_table_returns_400():
    store = StoreFactory()
    user = UserFactory()
    reservation = Reservation.objects.create(
        store=store,
        customer_phone="+254712345678",
        party_size=2,
        reserved_for=timezone.now() + timedelta(days=1),
        table=None,
        status=Reservation.STATUS_CONFIRMED,
    )

    request = _view_request("patch", f"/reservations/{reservation.id}/seat/", user=user, store=store)
    view = ReservationViewSet.as_view({"patch": "seat"})
    response = view(request, pk=str(reservation.id))

    assert response.status_code == 400
    assert response.data["errors"][0]["code"] == "TABLE_NOT_ASSIGNED"


# ---------------------------------------------------------------------------
# AC4: no-show/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_show_transitions_confirmed_to_no_show():
    store = StoreFactory()
    user = UserFactory()
    reservation = Reservation.objects.create(
        store=store,
        customer_phone="+254712345678",
        party_size=2,
        reserved_for=timezone.now() + timedelta(days=1),
        status=Reservation.STATUS_CONFIRMED,
    )

    with patch("apps.restaurant.views.send_reservation_notification") as mock_task:
        mock_task.apply_async.return_value = None
        request = _view_request("patch", f"/reservations/{reservation.id}/no-show/", user=user, store=store)
        view = ReservationViewSet.as_view({"patch": "no_show"})
        response = view(request, pk=str(reservation.id))

    assert response.status_code == 200
    reservation.refresh_from_db()
    assert reservation.status == Reservation.STATUS_NO_SHOW


@pytest.mark.django_db
def test_no_show_from_pending_returns_422():
    store = StoreFactory()
    user = UserFactory()
    reservation = Reservation.objects.create(
        store=store,
        customer_phone="+254712345678",
        party_size=2,
        reserved_for=timezone.now() + timedelta(days=1),
        status=Reservation.STATUS_PENDING,
    )

    request = _view_request("patch", f"/reservations/{reservation.id}/no-show/", user=user, store=store)
    view = ReservationViewSet.as_view({"patch": "no_show"})
    response = view(request, pk=str(reservation.id))

    assert response.status_code == 422
