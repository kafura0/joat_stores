"""
Tests for Epic 10 — Customer Loyalty + Engagement.

Story 10.1: LoyaltyAccount + points earn/redeem
Story 10.2: StampCard auto-reward on threshold
Story 10.3: WhatsApp notification dispatch (stub)
Story 10.4: CustomerProfile RFM tracking
Story 10.5: WhatsApp ordering bridge webhook
Story 10.6: Viral footer in branding response
"""

from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from rest_framework.test import APIClient

from apps.loyalty.models import (
    CustomerProfile,
    CustomerStampCard,
    LoyaltyAccount,
    PointsTransaction,
    StampCard,
)
from apps.store.tests.factories import StoreFactory
from apps.users.tests.factories import UserFactory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(db):
    return StoreFactory()


@pytest.fixture
def owner(store):
    return UserFactory(store=store, role="store_owner")


@pytest.fixture
def owner_client(owner, store):
    c = APIClient()
    c.force_authenticate(user=owner)
    c.credentials(HTTP_X_STORE_ID=str(store.id))
    return c


@pytest.fixture
def loyalty_account(store):
    return LoyaltyAccount.objects.create(
        store=store,
        customer_phone="+254700000001",
        points_balance=100,
        lifetime_earned=100,
    )


@pytest.fixture
def stamp_card(store):
    return StampCard.objects.create(
        store=store,
        name="Coffee Card",
        stamps_required=5,
        reward_description="Free coffee",
    )


# ---------------------------------------------------------------------------
# Story 10.1 — Loyalty points
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLoyaltyPoints:

    def test_earn_points_increases_balance(self, loyalty_account):
        loyalty_account.earn(50, source="order", reference="order-1")
        assert loyalty_account.points_balance == 150
        assert loyalty_account.lifetime_earned == 150

    def test_earn_creates_transaction(self, loyalty_account):
        loyalty_account.earn(50, source="order", reference="order-1")
        tx = PointsTransaction.objects.get(account=loyalty_account)
        assert tx.delta == 50
        assert tx.source == "order"

    def test_redeem_points_decreases_balance(self, loyalty_account):
        loyalty_account.redeem(30, reference="checkout-1")
        assert loyalty_account.points_balance == 70

    def test_redeem_insufficient_points_raises(self, loyalty_account):
        with pytest.raises(ValueError, match="Insufficient"):
            loyalty_account.redeem(200)

    def test_redeem_creates_negative_transaction(self, loyalty_account):
        loyalty_account.redeem(30)
        tx = PointsTransaction.objects.get(account=loyalty_account, source="redemption")
        assert tx.delta == -30

    def test_points_transaction_is_append_only(self, loyalty_account):
        tx = loyalty_account.earn(10, source="order")
        with pytest.raises(ValueError, match="append-only"):
            tx.delta = 99
            tx.save()

    def test_account_api_returns_balance(self, owner_client, loyalty_account):
        resp = owner_client.get("/api/v1/loyalty/account/?phone=%2B254700000001")
        assert resp.status_code == 200
        assert resp.data["points_balance"] == 100

    def test_history_api_returns_transactions(self, owner_client, loyalty_account):
        loyalty_account.earn(20, source="order", reference="order-x")
        resp = owner_client.get("/api/v1/loyalty/history/?phone=%2B254700000001")
        assert resp.status_code == 200
        assert len(resp.data) >= 1

    def test_redeem_api_deducts_points(self, owner_client, loyalty_account):
        resp = owner_client.post("/api/v1/loyalty/redeem/", {
            "phone": "+254700000001",
            "points": 50,
            "reference": "order-test",
        }, format="json")
        assert resp.status_code == 200
        assert resp.data["redeemed_points"] == 50
        assert resp.data["new_balance"] == 50

    def test_redeem_api_returns_422_on_insufficient(self, owner_client, loyalty_account):
        resp = owner_client.post("/api/v1/loyalty/redeem/", {
            "phone": "+254700000001",
            "points": 500,
        }, format="json")
        assert resp.status_code == 422
        assert resp.data["errors"][0]["code"] == "INSUFFICIENT_POINTS"

    def test_award_loyalty_points_task(self, store):
        from apps.loyalty.tasks import award_loyalty_points
        award_loyalty_points(str(store.id), "+254700000001", "1000.00", "order-123")
        account = LoyaltyAccount.objects.get(store=store, customer_phone="+254700000001")
        assert account.points_balance == 10  # 1000/100 * 1


# ---------------------------------------------------------------------------
# Story 10.2 — Stamp cards
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestStampCards:

    def test_stamp_card_created(self, stamp_card):
        assert stamp_card.stamps_required == 5

    def test_add_stamp_increments_count(self, store, stamp_card):
        csc = CustomerStampCard.objects.create(
            store=store, stamp_card=stamp_card,
            customer_phone="+254700000002",
        )
        for i in range(4):
            reached = csc.add_stamp(f"order-{i}")
            assert reached is False
        assert csc.stamps_count == 4

    def test_threshold_reached_resets_count(self, store, stamp_card):
        csc = CustomerStampCard.objects.create(
            store=store, stamp_card=stamp_card,
            customer_phone="+254700000003",
        )
        for i in range(5):
            reached = csc.add_stamp(f"order-{i}")
        assert reached is True
        assert csc.stamps_count == 0
        assert csc.redeemed_count == 1

    def test_stamp_card_list_api(self, owner_client, stamp_card):
        resp = owner_client.get("/api/v1/loyalty/stamp-cards/")
        assert resp.status_code == 200
        assert len(resp.data) >= 1
        assert resp.data[0]["name"] == "Coffee Card"

    def test_create_stamp_card_api(self, owner_client):
        resp = owner_client.post("/api/v1/loyalty/stamp-cards/", {
            "name": "Burger Card",
            "stamps_required": 8,
            "reward_description": "Free burger",
        }, format="json")
        assert resp.status_code == 201

    def test_my_stamp_cards_api(self, owner_client, store, stamp_card):
        CustomerStampCard.objects.create(
            store=store, stamp_card=stamp_card,
            customer_phone="+254700000002",
            stamps_count=3,
        )
        resp = owner_client.get("/api/v1/loyalty/my-stamp-cards/?phone=%2B254700000002")
        assert resp.status_code == 200
        assert resp.data[0]["stamps_count"] == 3
        assert resp.data[0]["progress_percent"] == 60  # 3/5 * 100

    def test_award_stamp_task_triggers_reward_on_threshold(self, store, stamp_card):
        from apps.loyalty.tasks import award_stamp
        with patch("apps.loyalty.tasks.send_stamp_reward_notification.delay") as mock_notify:
            # 5 stamps to hit threshold
            for i in range(5):
                award_stamp(str(store.id), "+254700000004", f"order-{i}")
        mock_notify.assert_called_once()


# ---------------------------------------------------------------------------
# Story 10.3 — WhatsApp notification
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestWhatsAppNotification:

    def test_send_whatsapp_creates_message_log(self, store):
        from apps.notifications.tasks import send_whatsapp_notification
        from apps.notifications.models import WhatsAppMessage

        send_whatsapp_notification(
            store_id=str(store.id),
            recipient_phone="+254700000005",
            message_body="Test message",
            template="generic",
        )
        msg = WhatsAppMessage.objects.get(store=store, recipient_phone="+254700000005")
        assert msg.status == "sent"

    def test_send_whatsapp_marks_sent_at(self, store):
        from apps.notifications.tasks import send_whatsapp_notification
        from apps.notifications.models import WhatsAppMessage

        send_whatsapp_notification(
            store_id=str(store.id),
            recipient_phone="+254700000006",
            message_body="Hi",
        )
        msg = WhatsAppMessage.objects.get(store=store, recipient_phone="+254700000006")
        assert msg.sent_at is not None


# ---------------------------------------------------------------------------
# Story 10.4 — Unified customer profile
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCustomerProfile:

    def test_record_order_updates_rfm(self, store):
        profile = CustomerProfile.objects.create(
            store=store, customer_phone="+254700000007"
        )
        profile.record_order(Decimal("500.00"))
        assert profile.order_count == 1
        assert profile.total_spent == Decimal("500.00")
        assert profile.first_order_at is not None

    def test_record_order_twice(self, store):
        profile = CustomerProfile.objects.create(
            store=store, customer_phone="+254700000008"
        )
        profile.record_order(Decimal("200.00"))
        profile.record_order(Decimal("300.00"))
        assert profile.order_count == 2
        assert profile.total_spent == Decimal("500.00")

    def test_customer_profiles_api(self, owner_client, store):
        CustomerProfile.objects.create(store=store, customer_phone="+254700000009")
        resp = owner_client.get("/api/v1/loyalty/customers/")
        assert resp.status_code == 200
        assert len(resp.data) >= 1

    def test_customer_profile_detail_api(self, owner_client, store):
        CustomerProfile.objects.create(
            store=store,
            customer_phone="+254700000010",
            order_count=3,
            total_spent=Decimal("1500.00"),
        )
        resp = owner_client.get("/api/v1/loyalty/customers/%2B254700000010/")
        assert resp.status_code == 200
        assert resp.data["order_count"] == 3

    def test_update_customer_profile_task(self, store):
        from apps.loyalty.tasks import update_customer_profile
        update_customer_profile(str(store.id), "+254700000011", "750.00", "Alice", "alice@test.com")
        profile = CustomerProfile.objects.get(store=store, customer_phone="+254700000011")
        assert profile.order_count == 1
        assert profile.total_spent == Decimal("750.00")


# ---------------------------------------------------------------------------
# Story 10.5 — WhatsApp ordering bridge
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestWhatsAppOrderingBridge:

    def test_webhook_verification_challenge(self, owner_client):
        resp = owner_client.get(
            "/api/v1/notifications/whatsapp/inbound/"
            "?hub.mode=subscribe&hub.verify_token=joat-stores-verify&hub.challenge=12345"
        )
        assert resp.status_code == 200

    def test_inbound_message_logged(self, owner_client, store):
        from apps.notifications.models import WhatsAppInboundMessage
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "+254700000012",
                            "text": {"body": "Show me your menu"},
                        }]
                    }
                }]
            }]
        }
        resp = owner_client.post("/api/v1/notifications/whatsapp/inbound/", payload, format="json")
        assert resp.status_code == 200
        msg = WhatsAppInboundMessage.objects.get(sender_phone="+254700000012")
        assert msg.parsed_intent == "menu"


# ---------------------------------------------------------------------------
# Story 10.6 — Viral footer in branding
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestViralFooter:

    def test_branding_includes_powered_by(self, owner_client):
        resp = owner_client.get("/api/v1/store/branding/")
        assert resp.status_code == 200
        assert "powered_by" in resp.data["data"]
        assert resp.data["data"]["powered_by"]["text"] == "Powered by joat stores"
        assert "url" in resp.data["data"]["powered_by"]
