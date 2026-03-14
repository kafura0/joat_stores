"""
Notifications views — Epic 10.

Story 10.5: POST /api/v1/notifications/whatsapp/inbound/
  WhatsApp ordering bridge webhook — receives inbound messages from customers,
  parses intent, and responds with menu link or order status.
  Currently a stub: logs + returns 200 for Meta webhook verification.
"""

import structlog
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

log = structlog.get_logger(__name__)


class WhatsAppInboundWebhookView(APIView):
    """
    POST /api/v1/notifications/whatsapp/inbound/
    GET  /api/v1/notifications/whatsapp/inbound/  — Meta webhook verification

    Story 10.5 — WhatsApp ordering bridge.

    Meta sends GET with hub.challenge to verify the webhook endpoint.
    Inbound messages arrive via POST with JSON body.

    Full intent parsing + auto-reply deferred to Epic 11 (AI integration).
    Currently: log inbound message + return 200.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """Meta webhook verification challenge."""
        challenge = request.query_params.get("hub.challenge")
        mode = request.query_params.get("hub.mode")
        verify_token = request.query_params.get("hub.verify_token")

        from django.conf import settings
        expected_token = getattr(settings, "WHATSAPP_WEBHOOK_VERIFY_TOKEN", "joat-stores-verify")

        if mode == "subscribe" and verify_token == expected_token:
            log.info("whatsapp_webhook_verified")
            return Response(int(challenge) if challenge else 0)

        return Response({"error": "Forbidden"}, status=403)

    def post(self, request):
        """Receive inbound WhatsApp message from Meta."""
        try:
            store = getattr(request, "store", None)
            body = request.data

            # Extract sender + message text from Meta's WhatsApp Cloud API format
            sender_phone = ""
            raw_body = ""
            try:
                entry = body.get("entry", [{}])[0]
                changes = entry.get("changes", [{}])[0]
                value = changes.get("value", {})
                messages = value.get("messages", [])
                if messages:
                    msg = messages[0]
                    sender_phone = msg.get("from", "")
                    raw_body = msg.get("text", {}).get("body", "")
            except (IndexError, AttributeError, KeyError):
                pass

            # Detect intent (stub — Epic 11 will use NLP)
            intent = _detect_intent(raw_body)

            if store and sender_phone:
                from apps.notifications.models import WhatsAppInboundMessage
                WhatsAppInboundMessage.objects.create(
                    store=store,
                    sender_phone=sender_phone,
                    raw_body=raw_body,
                    parsed_intent=intent,
                )
                log.info(
                    "whatsapp_inbound_received",
                    store_id=str(store.id) if store else None,
                    phone=sender_phone,
                    intent=intent,
                )

                # Auto-reply with menu link if intent is "menu" or "order"
                if intent in ("menu", "order") and store:
                    from apps.notifications.tasks import send_whatsapp_notification
                    menu_url = f"https://{store.domain}/menu"
                    reply = f"Hi! Here's our menu: {menu_url}\nReply with your order or visit the link."
                    send_whatsapp_notification.delay(
                        store_id=str(store.id),
                        recipient_phone=sender_phone,
                        message_body=reply,
                        template="generic",
                    )

        except Exception as exc:
            log.error("whatsapp_inbound_error", error=str(exc))

        # Always return 200 to Meta (otherwise they retry)
        return Response({"status": "ok"})


def _detect_intent(text: str) -> str:
    """Very simple keyword-based intent detection. Epic 11 replaces with NLP."""
    if not text:
        return "unknown"
    lower = text.lower()
    if any(kw in lower for kw in ["menu", "what do you have", "food", "drinks"]):
        return "menu"
    if any(kw in lower for kw in ["order", "i want", "give me", "can i get"]):
        return "order"
    if any(kw in lower for kw in ["status", "where is", "my order"]):
        return "status"
    return "unknown"
