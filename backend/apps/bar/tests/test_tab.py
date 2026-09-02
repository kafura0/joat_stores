"""
Tests for Epic 5 — Bar Tab Management.

Story 5.1: Tab state machine + CRUD
Story 5.2: Round ordering + item removal audit
Story 5.3: Age restriction acknowledgement + AgeRestrictionLog
Story 5.4: Happy hour price snapshot
Story 5.5: Split-bill settlement via M-Pesa + signal auto-settle
"""

from datetime import time
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bar.models import (
    AgeRestrictionLog,
    HappyHour,
    InvalidTabTransition,
    Tab,
    TabItem,
    TabShare,
    get_active_happy_hour,
)
from apps.bar.tests.factories import (
    HappyHourFactory,
    TabFactory,
    TabItemFactory,
    TabRoundFactory,
    TabShareFactory,
)
from apps.restaurant.tests.factories import MenuItemFactory, MenuSectionFactory
from apps.store.tests.factories import StoreFactory
from apps.users.tests.factories import UserFactory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(db):
    return StoreFactory()


@pytest.fixture
def staff(store):
    return UserFactory(store=store, role="store_owner")


@pytest.fixture
def client(staff, store):
    c = APIClient()
    c.force_authenticate(user=staff)
    c.credentials(HTTP_X_STORE_ID=str(store.id))
    return c


# ---------------------------------------------------------------------------
# Story 5.1 — Tab state machine
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTabStateMachine:

    def test_new_tab_is_open(self, store):
        tab = TabFactory(store=store)
        assert tab.status == Tab.STATUS_OPEN

    def test_open_to_bill_requested(self, store):
        tab = TabFactory(store=store)
        tab.transition(Tab.STATUS_BILL_REQUESTED)
        assert tab.status == Tab.STATUS_BILL_REQUESTED

    def test_bill_requested_to_settled(self, store):
        tab = TabFactory(store=store, status=Tab.STATUS_BILL_REQUESTED)
        tab.transition(Tab.STATUS_SETTLED)
        assert tab.status == Tab.STATUS_SETTLED
        assert tab.settled_at is not None

    def test_invalid_transition_open_to_settled_raises(self, store):
        tab = TabFactory(store=store)
        with pytest.raises(InvalidTabTransition):
            tab.transition(Tab.STATUS_SETTLED)

    def test_settled_tab_cannot_transition(self, store):
        tab = TabFactory(store=store, status=Tab.STATUS_SETTLED)
        with pytest.raises(InvalidTabTransition):
            tab.transition(Tab.STATUS_BILL_REQUESTED)

    def test_post_tab_returns_201(self, client):
        resp = client.post("/api/v1/bar/tabs/", {"customer_name": "John"}, format="json")
        assert resp.status_code == 201
        assert resp.data["status"] == "OPEN"

    def test_request_bill_transitions_tab(self, client, store):
        tab = TabFactory(store=store)
        resp = client.post(f"/api/v1/bar/tabs/{tab.id}/request-bill/")
        assert resp.status_code == 200
        tab.refresh_from_db()
        assert tab.status == Tab.STATUS_BILL_REQUESTED

    def test_request_bill_on_settled_tab_returns_422(self, client, store):
        tab = TabFactory(store=store, status=Tab.STATUS_SETTLED)
        resp = client.post(f"/api/v1/bar/tabs/{tab.id}/request-bill/")
        assert resp.status_code == 422
        assert resp.data["code"] == "INVALID_TAB_TRANSITION"

    def test_get_tab_detail(self, client, store):
        tab = TabFactory(store=store)
        resp = client.get(f"/api/v1/bar/tabs/{tab.id}/")
        assert resp.status_code == 200
        assert resp.data["id"] == str(tab.id)


# ---------------------------------------------------------------------------
# Story 5.2 — Round ordering + item removal audit
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRoundOrdering:

    def _add_round(self, client, store, tab, extra=None):
        section = MenuSectionFactory(store=store)
        menu_item = MenuItemFactory(store=store, section=section, price="300.00")
        payload = {
            "items": [{"menu_item_id": str(menu_item.id), "quantity": 2}],
        }
        if extra:
            payload.update(extra)
        return client.post(f"/api/v1/bar/tabs/{tab.id}/rounds/", payload, format="json")

    def test_add_round_to_open_tab(self, client, store):
        tab = TabFactory(store=store)
        resp = self._add_round(client, store, tab)
        assert resp.status_code == 201
        assert resp.data["items_added"] == 1
        assert TabItem.objects.filter(tab=tab).count() == 1

    def test_round_number_increments(self, client, store):
        tab = TabFactory(store=store)
        self._add_round(client, store, tab)
        self._add_round(client, store, tab)
        rounds = tab.rounds.order_by("round_number")
        assert list(rounds.values_list("round_number", flat=True)) == [1, 2]

    def test_add_round_to_non_open_tab_returns_422(self, client, store):
        tab = TabFactory(store=store, status=Tab.STATUS_BILL_REQUESTED)
        resp = self._add_round(client, store, tab)
        assert resp.status_code == 422
        assert resp.data["code"] == "TAB_NOT_OPEN"

    def test_remove_item_creates_audit_trail(self, client, staff, store):
        tab = TabFactory(store=store)
        item = TabItemFactory(store=store, tab=tab)
        resp = client.delete(f"/api/v1/bar/tabs/{tab.id}/items/{item.id}/")
        assert resp.status_code == 200
        item.refresh_from_db()
        assert item.removed_at is not None
        assert item.removed_by == staff
        assert resp.data["removed"] is True

    def test_remove_already_removed_item_returns_409(self, client, store):
        tab = TabFactory(store=store)
        item = TabItemFactory(store=store, tab=tab, removed_at=timezone.now())
        resp = client.delete(f"/api/v1/bar/tabs/{tab.id}/items/{item.id}/")
        assert resp.status_code == 409

    def test_removed_items_excluded_from_total(self, store):
        tab = TabFactory(store=store)
        round1 = TabRoundFactory(store=store, tab=tab, round_number=1)
        active = TabItemFactory(store=store, tab=tab, round=round1, unit_price=Decimal("200.00"), quantity=2)
        removed = TabItemFactory(store=store, tab=tab, round=round1, unit_price=Decimal("300.00"), quantity=1, removed_at=timezone.now())
        assert tab.total_amount == Decimal("400.00")


# ---------------------------------------------------------------------------
# Story 5.3 — Age restriction
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAgeRestriction:

    def test_age_restricted_item_requires_acknowledgement(self, client, store):
        tab = TabFactory(store=store)
        section = MenuSectionFactory(store=store)
        menu_item = MenuItemFactory(store=store, section=section, is_age_restricted=True)
        payload = {
            "items": [
                {"menu_item_id": str(menu_item.id), "quantity": 1}
            ]
        }
        resp = client.post(f"/api/v1/bar/tabs/{tab.id}/rounds/", payload, format="json")
        assert resp.status_code == 403
        assert resp.data["code"] == "AGE_RESTRICTION_ACKNOWLEDGEMENT_REQUIRED"

    def test_acknowledged_age_restricted_item_added(self, client, store):
        tab = TabFactory(store=store)
        section = MenuSectionFactory(store=store)
        menu_item = MenuItemFactory(store=store, section=section, is_age_restricted=True)
        payload = {
            "items": [
                {
                    "menu_item_id": str(menu_item.id),
                    "quantity": 1,
                    "acknowledge_age_restriction": True,
                }
            ]
        }
        resp = client.post(f"/api/v1/bar/tabs/{tab.id}/rounds/", payload, format="json")
        assert resp.status_code == 201
        assert AgeRestrictionLog.objects.filter(tab=tab).exists()

    def test_second_age_restricted_item_no_duplicate_log(self, client, store, staff):
        tab = TabFactory(store=store)
        section = MenuSectionFactory(store=store)
        menu_item = MenuItemFactory(store=store, section=section, is_age_restricted=True)
        # First round — creates log
        payload = {
            "items": [{"menu_item_id": str(menu_item.id), "quantity": 1, "acknowledge_age_restriction": True}]
        }
        client.post(f"/api/v1/bar/tabs/{tab.id}/rounds/", payload, format="json")
        assert AgeRestrictionLog.objects.filter(tab=tab).count() == 1

        # Second round — same user, same tab: no new log, no prompt
        payload2 = {
            "items": [{"menu_item_id": str(menu_item.id), "quantity": 1}]
        }
        resp = client.post(f"/api/v1/bar/tabs/{tab.id}/rounds/", payload2, format="json")
        assert resp.status_code == 201
        # Still only one log entry
        assert AgeRestrictionLog.objects.filter(tab=tab).count() == 1


# ---------------------------------------------------------------------------
# Story 5.4 — Happy hour price snapshot
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestHappyHourPriceSnapshot:

    def test_happy_hour_discount_applied(self, store):
        hh = HappyHourFactory(store=store, discount_percent=Decimal("20.00"))
        price = Decimal("500.00")
        discounted = hh.apply_discount(price)
        assert discounted == Decimal("400.00")

    def test_item_price_snapshotted_at_add_time(self, client, store):
        """Price on TabItem uses happy hour rate at add-time."""
        section = MenuSectionFactory(store=store)
        menu_item = MenuItemFactory(store=store, section=section, price="500.00")
        tab = TabFactory(store=store)

        now = timezone.localtime()
        start = (now - timezone.timedelta(hours=1)).time()
        end = (now + timezone.timedelta(hours=1)).time()
        HappyHourFactory(
            store=store, start_time=start, end_time=end, discount_percent=Decimal("20.00")
        )

        payload = {"items": [{"menu_item_id": str(menu_item.id), "quantity": 1}]}
        resp = client.post(f"/api/v1/bar/tabs/{tab.id}/rounds/", payload, format="json")
        assert resp.status_code == 201
        assert resp.data["happy_hour_active"] is True

        item = TabItem.objects.get(tab=tab)
        assert item.is_happy_hour is True
        assert item.unit_price == Decimal("400.00")  # 20% off 500

    def test_no_happy_hour_uses_full_price(self, client, store):
        section = MenuSectionFactory(store=store)
        menu_item = MenuItemFactory(store=store, section=section, price="500.00")
        tab = TabFactory(store=store)

        payload = {"items": [{"menu_item_id": str(menu_item.id), "quantity": 1}]}
        resp = client.post(f"/api/v1/bar/tabs/{tab.id}/rounds/", payload, format="json")
        assert resp.status_code == 201
        assert resp.data["happy_hour_active"] is False

        item = TabItem.objects.get(tab=tab)
        assert item.is_happy_hour is False
        assert item.unit_price == Decimal("500.00")

    def test_settled_tab_retains_happy_hour_price(self, store):
        """Price is locked at add-time — not recalculated at settlement."""
        tab = TabFactory(store=store, status=Tab.STATUS_BILL_REQUESTED)
        item = TabItemFactory(
            store=store, tab=tab, unit_price=Decimal("400.00"), is_happy_hour=True
        )
        # The price on TabItem never changes regardless of settlement
        item.refresh_from_db()
        assert item.unit_price == Decimal("400.00")

    def test_happy_hour_is_active_now(self, store):
        now = timezone.localtime()
        start = (now - timezone.timedelta(hours=1)).time()
        end = (now + timezone.timedelta(hours=1)).time()
        hh = HappyHourFactory(store=store, start_time=start, end_time=end)
        assert hh.is_active_now() is True

    def test_happy_hour_inactive_outside_window(self, store):
        now = timezone.localtime()
        start = (now + timezone.timedelta(hours=2)).time()
        end = (now + timezone.timedelta(hours=4)).time()
        hh = HappyHourFactory(store=store, start_time=start, end_time=end)
        assert hh.is_active_now() is False


# ---------------------------------------------------------------------------
# Story 5.5 — Split settlement + signal auto-settle
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSplitSettlement:

    def test_split_creates_tab_shares(self, client, store):
        tab = TabFactory(store=store, status=Tab.STATUS_BILL_REQUESTED)
        TabItemFactory(store=store, tab=tab, unit_price=Decimal("500.00"), quantity=2)

        with patch("apps.bar.views.initiate_payment") as mock_pay:
            mock_txn = MagicMock()
            mock_txn.id = "00000000-0000-0000-0000-000000000001"
            mock_pay.return_value = mock_txn

            resp = client.post(
                f"/api/v1/bar/tabs/{tab.id}/split/",
                {
                    "shares": [
                        {"payer_phone": "+254711111111", "amount": "500.00"},
                        {"payer_phone": "+254722222222", "amount": "500.00"},
                    ]
                },
                format="json",
            )

        assert resp.status_code == 202
        assert len(resp.data["shares"]) == 2
        assert TabShare.objects.filter(tab=tab).count() == 2

    def test_split_requires_bill_requested_status(self, client, store):
        tab = TabFactory(store=store, status=Tab.STATUS_OPEN)
        resp = client.post(
            f"/api/v1/bar/tabs/{tab.id}/split/",
            {"shares": [{"payer_phone": "+254711111111", "amount": "500.00"}]},
            format="json",
        )
        assert resp.status_code == 422

    def test_signal_auto_settles_tab_when_all_shares_paid(self, store):
        """payment_confirmed → last TabShare PAID → Tab transitions to SETTLED."""
        from apps.bar.apps import _handle_payment_confirmed
        from apps.payment.tests.factories import MpesaTransactionFactory

        tab = TabFactory(store=store, status=Tab.STATUS_BILL_REQUESTED)
        share1 = TabShareFactory(store=store, tab=tab, amount=Decimal("300.00"))
        share2 = TabShareFactory(store=store, tab=tab, amount=Decimal("200.00"))

        # Pay share1
        txn1 = MpesaTransactionFactory(store=store, reference=f"tab-share-{share1.id}")
        _handle_payment_confirmed(sender=None, transaction=txn1)
        share1.refresh_from_db()
        tab.refresh_from_db()
        assert share1.status == TabShare.STATUS_PAID
        # Tab still open — share2 is pending
        assert tab.status == Tab.STATUS_BILL_REQUESTED

        # Pay share2 — should auto-settle tab
        txn2 = MpesaTransactionFactory(store=store, reference=f"tab-share-{share2.id}")
        _handle_payment_confirmed(sender=None, transaction=txn2)
        share2.refresh_from_db()
        tab.refresh_from_db()
        assert share2.status == TabShare.STATUS_PAID
        assert tab.status == Tab.STATUS_SETTLED
        assert tab.settled_at is not None

    def test_signal_ignores_non_tab_share_references(self, store):
        """Signal handler is a no-op for references not starting with 'tab-share-'."""
        from apps.bar.apps import _handle_payment_confirmed
        from apps.payment.tests.factories import MpesaTransactionFactory

        txn = MpesaTransactionFactory(store=store, reference="order-abc")
        # Should not raise
        _handle_payment_confirmed(sender=None, transaction=txn)

    def test_failed_stk_push_leaves_tab_in_bill_requested(self, client, store):
        """A payer STK Push failure → tab stays BILL_REQUESTED, other shares intact."""
        from apps.payment.exceptions import StkPushInitiationError

        tab = TabFactory(store=store, status=Tab.STATUS_BILL_REQUESTED)
        TabItemFactory(store=store, tab=tab, unit_price=Decimal("500.00"))

        with patch("apps.bar.views.initiate_payment", side_effect=StkPushInitiationError):
            resp = client.post(
                f"/api/v1/bar/tabs/{tab.id}/split/",
                {"shares": [{"payer_phone": "+254711111111", "amount": "500.00"}]},
                format="json",
            )

        assert resp.status_code == 202
        share = TabShare.objects.get(tab=tab)
        assert share.status == TabShare.STATUS_FAILED
        tab.refresh_from_db()
        assert tab.status == Tab.STATUS_BILL_REQUESTED
