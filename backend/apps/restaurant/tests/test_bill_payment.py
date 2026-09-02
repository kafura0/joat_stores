"""
Tests for Story 3.11 — Restaurant Bill Payment + Split Bill.

Covers:
- AC1: GET /sessions/{id}/bill/ returns itemized orders + total + shares
- AC2: POST /sessions/{id}/pay-bill/ → BillShare created + STK Push initiated
- AC3: POST /sessions/{id}/split-bill/ → one BillShare per payer + STK Push per share
- AC4: payment_confirmed signal → BillShare→PAID; all paid → session auto-closes
- AC5: 400 when session is CLOSED
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.restaurant.models import BillShare, DineInOrder, TableSession
from apps.restaurant.tests.factories import (
    BillShareFactory,
    DineInOrderFactory,
    KitchenTicketFactory,
    TableFactory,
    TableSessionFactory,
)
from apps.restaurant.views import TableSessionViewSet
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


def _session_action(action_name, session_id, method="get", data=None, user=None, store=None):
    url = f"/api/v1/restaurant/sessions/{session_id}/{action_name}/"
    req = _view_request(method, url, data=data, user=user, store=store)
    view = TableSessionViewSet.as_view({"get": action_name, "post": action_name, "patch": action_name})
    return view(req, pk=str(session_id))


@pytest.fixture
def store():
    return StoreFactory()


@pytest.fixture
def waiter(store):
    u = UserFactory()
    u.store = store
    return u


@pytest.fixture
def session(store):
    table = TableFactory(store=store)
    return TableSessionFactory(table=table, status=TableSession.STATUS_BILL_REQUESTED)


@pytest.fixture
def orders(session):
    o1 = DineInOrderFactory(
        session=session, store=session.store, total_amount=Decimal("500.00"),
        status=DineInOrder.STATUS_PENDING,
    )
    KitchenTicketFactory(order=o1, store=session.store)
    o2 = DineInOrderFactory(
        session=session, store=session.store, total_amount=Decimal("350.00"),
        status=DineInOrder.STATUS_CONFIRMED,
    )
    KitchenTicketFactory(order=o2, store=session.store)
    return [o1, o2]


# ---------------------------------------------------------------------------
# AC1 — GET bill endpoint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_bill_returns_orders_and_total(store, waiter, session, orders):
    resp = _session_action("bill", session.id, method="get", user=waiter, store=store)
    assert resp.status_code == 200
    data = resp.data
    assert data["session_id"] == str(session.id)
    assert data["table_number"] == session.table.number
    assert len(data["orders"]) == 2
    assert Decimal(data["total_amount"]) == Decimal("850.00")
    assert data["shares"] == []


@pytest.mark.django_db
def test_bill_includes_existing_shares(store, waiter, session, orders):
    BillShareFactory(session=session, store=store, amount=Decimal("850.00"))
    resp = _session_action("bill", session.id, method="get", user=waiter, store=store)
    assert resp.status_code == 200
    assert len(resp.data["shares"]) == 1


# ---------------------------------------------------------------------------
# AC2 — Single-payer pay-bill
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_pay_bill_creates_share_and_initiates_stk(store, waiter, session, orders):
    from apps.payment.tests.factories import MpesaTransactionFactory

    real_txn = MpesaTransactionFactory(store=store, reference="bill-share-init")

    with patch("apps.payment.services.initiate_payment", return_value=real_txn) as mock_pay:
        resp = _session_action(
            "pay_bill", session.id, method="post",
            data={"phone": "+254712345678"},
            user=waiter, store=store,
        )

    assert resp.status_code == 201
    share = BillShare.objects.filter(session=session).first()
    assert share is not None
    assert share.amount == Decimal("850.00")
    assert share.payer_phone == "+254712345678"
    mock_pay.assert_called_once()
    call_kwargs = mock_pay.call_args[1]
    assert call_kwargs["reference"].startswith("bill-share-")
    assert call_kwargs["amount"] == Decimal("850.00")


@pytest.mark.django_db
def test_pay_bill_missing_phone_returns_400(store, waiter, session, orders):
    resp = _session_action(
        "pay_bill", session.id, method="post",
        data={},
        user=waiter, store=store,
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_pay_bill_closed_session_returns_400(store, waiter):
    table = TableFactory(store=store)
    closed = TableSessionFactory(table=table, status=TableSession.STATUS_CLOSED)
    resp = _session_action(
        "pay_bill", closed.id, method="post",
        data={"phone": "+254712345678"},
        user=waiter, store=store,
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# AC3 — Split bill
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_split_bill_creates_one_share_per_payer(store, waiter, session, orders):
    from apps.payment.tests.factories import MpesaTransactionFactory

    real_txn = MpesaTransactionFactory(store=store, reference="bill-share-split")

    payload = {
        "shares": [
            {"payer_phone": "+254712000001", "amount": "500.00", "items_snapshot": []},
            {"payer_phone": "+254722000002", "amount": "350.00", "items_snapshot": []},
        ]
    }

    with patch("apps.payment.services.initiate_payment", return_value=real_txn):
        resp = _session_action(
            "split_bill", session.id, method="post",
            data=payload,
            user=waiter, store=store,
        )

    assert resp.status_code == 201
    assert len(resp.data["shares"]) == 2
    assert resp.data["errors"] == []
    assert BillShare.objects.filter(session=session).count() == 2


@pytest.mark.django_db
def test_split_bill_invalid_payload_returns_400(store, waiter, session):
    resp = _session_action(
        "split_bill", session.id, method="post",
        data={"shares": []},  # min_length=1 violated
        user=waiter, store=store,
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# AC4 — Signal handler: BillShare→PAID + auto-close when all paid
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_signal_marks_share_paid(store, session):
    from apps.payment.tests.factories import MpesaTransactionFactory

    share = BillShareFactory(session=session, store=store)
    txn = MpesaTransactionFactory(store=store, reference=f"bill-share-{share.id}")

    from apps.restaurant.apps import _handle_payment_confirmed
    _handle_payment_confirmed(sender=None, transaction=txn)

    share.refresh_from_db()
    assert share.status == BillShare.STATUS_PAID


@pytest.mark.django_db
def test_signal_auto_closes_session_when_all_shares_paid(store):
    from apps.payment.tests.factories import MpesaTransactionFactory

    table = TableFactory(store=store)
    session = TableSessionFactory(table=table, status=TableSession.STATUS_BILL_REQUESTED)
    share1 = BillShareFactory(session=session, store=store, amount=Decimal("500.00"))
    share2 = BillShareFactory(session=session, store=store, amount=Decimal("350.00"))

    txn1 = MpesaTransactionFactory(store=store, reference=f"bill-share-{share1.id}")

    from apps.restaurant.apps import _handle_payment_confirmed
    _handle_payment_confirmed(sender=None, transaction=txn1)

    # First share paid — session still open (share2 still PENDING)
    session.refresh_from_db()
    assert session.status == TableSession.STATUS_BILL_REQUESTED

    txn2 = MpesaTransactionFactory(store=store, reference=f"bill-share-{share2.id}")
    _handle_payment_confirmed(sender=None, transaction=txn2)

    # Both paid — session auto-closes
    session.refresh_from_db()
    assert session.status == TableSession.STATUS_CLOSED


@pytest.mark.django_db
def test_signal_handles_unknown_share_id_gracefully():
    """Signal handler must not raise — logs a warning only."""
    from apps.payment.tests.factories import MpesaTransactionFactory

    txn = MpesaTransactionFactory(reference="bill-share-00000000-0000-0000-0000-000000000099")

    from apps.restaurant.apps import _handle_payment_confirmed
    # Should not raise
    _handle_payment_confirmed(sender=None, transaction=txn)
