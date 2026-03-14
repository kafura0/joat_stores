"""
Tests for Story 3.4 — Table + TableSession State Machine + Waiter Assignment.

Covers:
- AC1: Open session on valid QR scan; 409 on duplicate OPEN session
- AC2: Assign waiter via PATCH /sessions/{id}/assign-waiter/
- AC3: State machine OPEN→BILL_REQUESTED→CLOSED; invalid transitions → 422
"""

import pytest
from django.db import IntegrityError
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.restaurant.models import InvalidSessionTransition, TableSession
from apps.restaurant.tests.factories import TableFactory, TableSessionFactory
from apps.restaurant.views import TableSessionViewSet
from apps.store.tests.factories import StoreFactory
from apps.users.tests.factories import UserFactory


# ---------------------------------------------------------------------------
# Model / state machine unit tests (no DB required for transition logic)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_transition_open_to_bill_requested():
    session = TableSessionFactory(status=TableSession.STATUS_OPEN)
    session.transition(TableSession.STATUS_BILL_REQUESTED)
    session.refresh_from_db()
    assert session.status == TableSession.STATUS_BILL_REQUESTED
    assert session.closed_at is None


@pytest.mark.django_db
def test_transition_bill_requested_to_closed():
    session = TableSessionFactory(status=TableSession.STATUS_BILL_REQUESTED)
    session.transition(TableSession.STATUS_CLOSED)
    session.refresh_from_db()
    assert session.status == TableSession.STATUS_CLOSED
    assert session.closed_at is not None


@pytest.mark.django_db
def test_invalid_transition_open_to_closed_raises():
    session = TableSessionFactory(status=TableSession.STATUS_OPEN)
    with pytest.raises(InvalidSessionTransition):
        session.transition(TableSession.STATUS_CLOSED)


@pytest.mark.django_db
def test_invalid_transition_closed_to_open_raises():
    session = TableSessionFactory(status=TableSession.STATUS_CLOSED)
    with pytest.raises(InvalidSessionTransition):
        session.transition(TableSession.STATUS_OPEN)


@pytest.mark.django_db
def test_unique_constraint_one_open_session_per_table():
    """DB-level UniqueConstraint rejects a second OPEN session for the same table."""
    table = TableFactory()
    TableSessionFactory(table=table, store=table.store, status=TableSession.STATUS_OPEN)
    with pytest.raises(IntegrityError):
        # bypass factory to hit DB constraint directly
        TableSession.objects.create(
            table=table,
            store=table.store,
            status=TableSession.STATUS_OPEN,
        )


@pytest.mark.django_db
def test_second_open_session_allowed_after_first_closed():
    """Once a session is CLOSED, a new OPEN session can be created for the same table."""
    table = TableFactory()
    session1 = TableSessionFactory(table=table, store=table.store, status=TableSession.STATUS_OPEN)
    session1.transition(TableSession.STATUS_BILL_REQUESTED)
    session1.transition(TableSession.STATUS_CLOSED)
    # Should not raise
    session2 = TableSessionFactory(table=table, store=table.store, status=TableSession.STATUS_OPEN)
    assert session2.status == TableSession.STATUS_OPEN


# ---------------------------------------------------------------------------
# ViewSet tests
# ---------------------------------------------------------------------------


def _viewset_request(method, url, data=None, user=None, store=None):
    factory = APIRequestFactory()
    fn = getattr(factory, method)
    request = fn(url, data=data, format="json")
    if user:
        force_authenticate(request, user=user)
    if store:
        request.store = store
    return request


@pytest.mark.django_db
def test_create_session_opens_new_session():
    store = StoreFactory()
    table = TableFactory(store=store)
    user = UserFactory()

    request = _viewset_request("post", "/sessions/", data={"table": str(table.id)}, user=user, store=store)
    view = TableSessionViewSet.as_view({"post": "create"})
    response = view(request)

    assert response.status_code == 201
    assert TableSession.objects.filter(table=table, status=TableSession.STATUS_OPEN).exists()


@pytest.mark.django_db
def test_create_session_409_when_open_already_exists():
    store = StoreFactory()
    table = TableFactory(store=store)
    TableSessionFactory(table=table, store=store, status=TableSession.STATUS_OPEN)
    user = UserFactory()

    request = _viewset_request("post", "/sessions/", data={"table": str(table.id)}, user=user, store=store)
    view = TableSessionViewSet.as_view({"post": "create"})
    response = view(request)

    assert response.status_code == 400  # DRF ValidationError from perform_create
    errors = response.data.get("errors", [])
    assert any(e["code"] == "DUPLICATE_SESSION" for e in errors)


@pytest.mark.django_db
def test_assign_waiter_sets_assigned_waiter():
    store = StoreFactory()
    waiter = UserFactory()
    session = TableSessionFactory(status=TableSession.STATUS_OPEN, store=store)

    request = _viewset_request("patch", f"/sessions/{session.id}/assign-waiter/", user=waiter, store=store)
    view = TableSessionViewSet.as_view({"patch": "assign_waiter"})
    response = view(request, pk=str(session.id))

    assert response.status_code == 200
    session.refresh_from_db()
    assert session.assigned_waiter_id == waiter.id


@pytest.mark.django_db
def test_assign_waiter_on_closed_session_returns_422():
    store = StoreFactory()
    waiter = UserFactory()
    session = TableSessionFactory(status=TableSession.STATUS_CLOSED, store=store)

    request = _viewset_request("patch", f"/sessions/{session.id}/assign-waiter/", user=waiter, store=store)
    view = TableSessionViewSet.as_view({"patch": "assign_waiter"})
    response = view(request, pk=str(session.id))

    assert response.status_code == 422
    assert response.data["errors"][0]["code"] == "INVALID_SESSION_TRANSITION"


@pytest.mark.django_db
def test_request_bill_transitions_open_to_bill_requested():
    store = StoreFactory()
    user = UserFactory()
    session = TableSessionFactory(status=TableSession.STATUS_OPEN, store=store)

    request = _viewset_request("patch", f"/sessions/{session.id}/request-bill/", user=user, store=store)
    view = TableSessionViewSet.as_view({"patch": "request_bill"})
    response = view(request, pk=str(session.id))

    assert response.status_code == 200
    session.refresh_from_db()
    assert session.status == TableSession.STATUS_BILL_REQUESTED


@pytest.mark.django_db
def test_close_transitions_bill_requested_to_closed():
    store = StoreFactory()
    user = UserFactory()
    session = TableSessionFactory(status=TableSession.STATUS_BILL_REQUESTED, store=store)

    request = _viewset_request("patch", f"/sessions/{session.id}/close/", user=user, store=store)
    view = TableSessionViewSet.as_view({"patch": "close"})
    response = view(request, pk=str(session.id))

    assert response.status_code == 200
    session.refresh_from_db()
    assert session.status == TableSession.STATUS_CLOSED
    assert session.closed_at is not None


@pytest.mark.django_db
def test_close_from_open_returns_422():
    store = StoreFactory()
    user = UserFactory()
    session = TableSessionFactory(status=TableSession.STATUS_OPEN, store=store)

    request = _viewset_request("patch", f"/sessions/{session.id}/close/", user=user, store=store)
    view = TableSessionViewSet.as_view({"patch": "close"})
    response = view(request, pk=str(session.id))

    assert response.status_code == 422
    assert response.data["errors"][0]["code"] == "INVALID_SESSION_TRANSITION"


@pytest.mark.django_db
def test_request_bill_from_closed_returns_422():
    store = StoreFactory()
    user = UserFactory()
    session = TableSessionFactory(status=TableSession.STATUS_CLOSED, store=store)

    request = _viewset_request("patch", f"/sessions/{session.id}/request-bill/", user=user, store=store)
    view = TableSessionViewSet.as_view({"patch": "request_bill"})
    response = view(request, pk=str(session.id))

    assert response.status_code == 422
    assert response.data["errors"][0]["code"] == "INVALID_SESSION_TRANSITION"


@pytest.mark.django_db
def test_direct_patch_returns_405():
    """PATCH on the base viewset is blocked — must use transition actions."""
    store = StoreFactory()
    user = UserFactory()
    session = TableSessionFactory(status=TableSession.STATUS_OPEN, store=store)

    request = _viewset_request("patch", f"/sessions/{session.id}/", data={"status": "CLOSED"}, user=user, store=store)
    view = TableSessionViewSet.as_view({"patch": "update"})
    response = view(request, pk=str(session.id))

    assert response.status_code == 405
