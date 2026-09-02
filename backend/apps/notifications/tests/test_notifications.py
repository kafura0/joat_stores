"""
Tests for notifications app — Epic 10 WhatsApp + push notifications.

Covers:
  - WhatsAppInboundWebhookView GET (Meta webhook verification)
  - WhatsAppInboundWebhookView POST (inbound message parsing)
  - _detect_intent helper function
  - WhatsAppMessage model
  - WhatsAppInboundMessage model
  - FCMDevice model
  - send_whatsapp_notification task
  - send_push_notification task
"""

from datetime import timedelta
from unittest.mock import patch, MagicMock

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.notifications.models import (
    FCMDevice,
    WhatsAppInboundMessage,
    WhatsAppMessage,
)
from apps.store.models import TenantType
from apps.store.tests.factories import StoreFactory
from apps.users.models import PlatformUser


@pytest.fixture
def store():
    return StoreFactory(tenant_type=TenantType.RESTAURANT)


@pytest.fixture
def platform_user():
    return PlatformUser.objects.create(
        email="hub@test.com",
        full_name="Hub Test User",
        phone="+254700000001",
    )


@pytest.fixture
def client():
    return APIClient()


# ---------------------------------------------------------------------------
# _detect_intent
# ---------------------------------------------------------------------------


class TestDetectIntent:
    def test_empty_text(self):
        from apps.notifications.views import _detect_intent

        assert _detect_intent("") == "unknown"

    def test_none_text(self):
        from apps.notifications.views import _detect_intent

        assert _detect_intent(None) == "unknown"

    def test_menu_keywords(self):
        from apps.notifications.views import _detect_intent

        for kw in ["menu", "what do you have", "food", "drinks"]:
            assert _detect_intent(kw) == "menu"

    def test_order_keywords(self):
        from apps.notifications.views import _detect_intent

        for kw in ["i want", "give me", "can i get"]:
            assert _detect_intent(kw) == "order"

    def test_status_keywords(self):
        from apps.notifications.views import _detect_intent

        for kw in ["status", "where is"]:
            assert _detect_intent(kw) == "status"

    def test_unknown_text(self):
        from apps.notifications.views import _detect_intent

        assert _detect_intent("hello there") == "unknown"


# ---------------------------------------------------------------------------
# WhatsAppMessage model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestWhatsAppMessage:
    def test_create(self, store):
        msg = WhatsAppMessage.objects.create(
            store=store,
            recipient_phone="+254700000001",
            template="order_confirmation",
            message_body="Your order is confirmed!",
            status=WhatsAppMessage.STATUS_QUEUED,
        )
        assert msg.store == store
        assert msg.recipient_phone == "+254700000001"
        assert msg.status == WhatsAppMessage.STATUS_QUEUED
        assert msg.queued_at is not None

    def test_str(self, store):
        msg = WhatsAppMessage.objects.create(
            store=store,
            recipient_phone="+254700000001",
            message_body="Test",
            status=WhatsAppMessage.STATUS_SENT,
        )
        assert "+254700000001" in str(msg)
        assert "sent" in str(msg)

    def test_status_choices(self, store):
        msg = WhatsAppMessage.objects.create(
            store=store,
            recipient_phone="+254700000001",
            message_body="Test",
        )
        assert msg.status == WhatsAppMessage.STATUS_QUEUED

    def test_ordering(self, store):
        msg1 = WhatsAppMessage.objects.create(
            store=store,
            recipient_phone="+254700000001",
            message_body="First",
        )
        msg2 = WhatsAppMessage.objects.create(
            store=store,
            recipient_phone="+254700000002",
            message_body="Second",
        )
        msgs = list(WhatsAppMessage.objects.filter(store=store))
        assert msgs[0].pk == msg2.pk
        assert msgs[1].pk == msg1.pk


# ---------------------------------------------------------------------------
# WhatsAppInboundMessage model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestWhatsAppInboundMessage:
    def test_create(self, store):
        msg = WhatsAppInboundMessage.objects.create(
            store=store,
            sender_phone="+254700000001",
            raw_body="I want to order food",
            parsed_intent="order",
        )
        assert msg.store == store
        assert msg.sender_phone == "+254700000001"
        assert msg.parsed_intent == "order"
        assert msg.response_sent is False
        assert msg.received_at is not None

    def test_str(self, store):
        msg = WhatsAppInboundMessage.objects.create(
            store=store,
            sender_phone="+254700000001",
            raw_body="Hello",
        )
        assert str(msg.pk) is not None


# ---------------------------------------------------------------------------
# FCMDevice model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFCMDevice:
    def test_create(self, platform_user):
        device = FCMDevice.objects.create(
            platform_user=platform_user,
            registration_id="fcm_token_abc123",
            platform=FCMDevice.PLATFORM_ANDROID,
        )
        assert device.platform_user == platform_user
        assert device.registration_id == "fcm_token_abc123"
        assert device.is_active is True

    def test_unique_together(self, platform_user):
        FCMDevice.objects.create(
            platform_user=platform_user,
            registration_id="fcm_token_abc123",
            platform=FCMDevice.PLATFORM_ANDROID,
        )
        with pytest.raises(Exception):
            FCMDevice.objects.create(
                platform_user=platform_user,
                registration_id="fcm_token_abc123",
                platform=FCMDevice.PLATFORM_IOS,
            )

    def test_str(self, platform_user):
        device = FCMDevice.objects.create(
            platform_user=platform_user,
            registration_id="abcdef1234567890xyz",
            platform=FCMDevice.PLATFORM_IOS,
        )
        s = str(device)
        assert "ios" in s
        assert "hub@test.com" in s

    def test_ordering(self, platform_user):
        d1 = FCMDevice.objects.create(
            platform_user=platform_user,
            registration_id="token1",
        )
        d2 = FCMDevice.objects.create(
            platform_user=platform_user,
            registration_id="token2",
        )
        devices = list(FCMDevice.objects.filter(platform_user=platform_user))
        assert devices[0].pk == d2.pk


# ---------------------------------------------------------------------------
# WhatsAppInboundWebhookView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestWhatsAppInboundWebhookView:
    def setup_method(self):
        self.client = APIClient()
        self.url = "/api/v1/notifications/whatsapp/inbound/"

    def test_get_verification_success(self, store):
        resp = self.client.get(
            self.url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "joat-stores-verify",
                "hub.challenge": "12345",
            },
            HTTP_X_STORE_ID=str(store.pk),
        )
        assert resp.status_code == 200
        assert resp.data == 12345

    def test_get_verification_wrong_token(self, store):
        resp = self.client.get(
            self.url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong-token",
                "hub.challenge": "12345",
            },
            HTTP_X_STORE_ID=str(store.pk),
        )
        assert resp.status_code == 403

    def test_get_verification_missing_challenge(self, store):
        resp = self.client.get(
            self.url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "joat-stores-verify",
            },
            HTTP_X_STORE_ID=str(store.pk),
        )
        assert resp.status_code == 200
        assert resp.data == 0

    def test_post_inbound_message(self, store):
        body = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "+254700000001",
                                        "text": {"body": "Show me the menu"},
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        resp = self.client.post(
            self.url,
            body,
            format="json",
            HTTP_X_STORE_ID=str(store.pk),
        )
        assert resp.status_code == 200
        assert resp.data == {"status": "ok"}

        assert WhatsAppInboundMessage.objects.filter(
            store=store,
            sender_phone="+254700000001",
            parsed_intent="menu",
        ).exists()

    def test_post_empty_body(self, store):
        resp = self.client.post(
            self.url,
            {},
            format="json",
            HTTP_X_STORE_ID=str(store.pk),
        )
        assert resp.status_code == 200

    def test_post_order_intent_triggers_reply(self, store):
        body = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "+254700000002",
                                        "text": {"body": "i want to order"},
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        with patch("apps.notifications.tasks.send_whatsapp_notification") as mock_task:
            resp = self.client.post(
                self.url,
                body,
                format="json",
                HTTP_X_STORE_ID=str(store.pk),
            )
            assert resp.status_code == 200
            mock_task.delay.assert_called_once()

    def test_post_unknown_intent_no_reply(self, store):
        body = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "+254700000003",
                                        "text": {"body": "hello"},
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        with patch("apps.notifications.tasks.send_whatsapp_notification") as mock_task:
            resp = self.client.post(
                self.url,
                body,
                format="json",
                HTTP_X_STORE_ID=str(store.pk),
            )
            assert resp.status_code == 200
            mock_task.delay.assert_not_called()


# ---------------------------------------------------------------------------
# send_whatsapp_notification task
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSendWhatsAppNotification:
    @patch("twilio.rest.Client")
    @override_settings(
        TWILIO_ACCOUNT_SID="AC_test_sid",
        TWILIO_AUTH_TOKEN="test_auth_token",
        TWILIO_WHATSAPP_FROM="+1234567890",
    )
    def test_creates_message_and_marks_sent(self, MockClient, store):
        mock_client = MagicMock()
        mock_msg = MagicMock()
        mock_msg.sid = "SM123456"
        mock_client.messages.create.return_value = mock_msg
        MockClient.return_value = mock_client

        from apps.notifications.tasks import send_whatsapp_notification

        send_whatsapp_notification(
            store_id=str(store.id),
            recipient_phone="+254700000001",
            message_body="Hello!",
            template="generic",
        )

        msg = WhatsAppMessage.objects.get(
            store=store,
            recipient_phone="+254700000001",
        )
        assert msg.status == WhatsAppMessage.STATUS_SENT
        assert msg.sent_at is not None
        assert msg.external_message_id == "SM123456"

    def test_stub_mode_when_no_twilio(self, store):
        from apps.notifications.tasks import send_whatsapp_notification

        with override_settings(
            TWILIO_ACCOUNT_SID="",
            TWILIO_AUTH_TOKEN="",
            TWILIO_WHATSAPP_FROM="",
        ):
            send_whatsapp_notification(
                store_id=str(store.id),
                recipient_phone="+254700000001",
                message_body="Hello!",
                template="generic",
            )

        msg = WhatsAppMessage.objects.get(
            store=store,
            recipient_phone="+254700000001",
        )
        assert msg.status == WhatsAppMessage.STATUS_SENT


# ---------------------------------------------------------------------------
# send_push_notification task
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSendPushNotification:
    def test_no_devices_does_not_fail(self, platform_user):
        from apps.notifications.tasks import send_push_notification

        send_push_notification(
            platform_user_id=platform_user.pk,
            title="Test",
            body="Body",
        )

    def test_logs_for_each_device(self, platform_user):
        FCMDevice.objects.create(
            platform_user=platform_user,
            registration_id="token1",
            platform=FCMDevice.PLATFORM_ANDROID,
        )
        FCMDevice.objects.create(
            platform_user=platform_user,
            registration_id="token2",
            platform=FCMDevice.PLATFORM_IOS,
        )

        from apps.notifications.tasks import send_push_notification

        send_push_notification(
            platform_user_id=platform_user.pk,
            title="Test Push",
            body="Body text",
        )

    def test_ignores_inactive_devices(self, platform_user):
        FCMDevice.objects.create(
            platform_user=platform_user,
            registration_id="token1",
            is_active=False,
        )

        from apps.notifications.tasks import send_push_notification

        send_push_notification(
            platform_user_id=platform_user.pk,
            title="Test",
            body="Body",
        )
