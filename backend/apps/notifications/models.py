"""
Notifications models — Epic 10.

Story 10.3: WhatsAppMessage — outbound message log (append-only)
Story 10.5: WhatsApp ordering bridge — inbound message parsing log
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import TenantModel


class WhatsAppMessage(TenantModel):
    """
    Log of every outbound WhatsApp message sent to a customer.

    Direction is always OUTBOUND here — inbound messages are logged
    in WhatsAppInboundMessage. Stored for audit + reply threading.
    """

    STATUS_QUEUED = "queued"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_QUEUED, _("Queued")),
        (STATUS_SENT, _("Sent")),
        (STATUS_FAILED, _("Failed")),
    ]

    TEMPLATE_ORDER_CONFIRMATION = "order_confirmation"
    TEMPLATE_LOYALTY_REWARD = "loyalty_reward"
    TEMPLATE_STAMP_THRESHOLD = "stamp_threshold"
    TEMPLATE_SUBSCRIPTION_RENEWAL = "subscription_renewal"
    TEMPLATE_GENERIC = "generic"

    TEMPLATE_CHOICES = [
        (TEMPLATE_ORDER_CONFIRMATION, _("Order Confirmation")),
        (TEMPLATE_LOYALTY_REWARD, _("Loyalty Reward")),
        (TEMPLATE_STAMP_THRESHOLD, _("Stamp Card Reward")),
        (TEMPLATE_SUBSCRIPTION_RENEWAL, _("Subscription Renewal")),
        (TEMPLATE_GENERIC, _("Generic")),
    ]

    recipient_phone = models.CharField(max_length=30, db_index=True)
    template = models.CharField(max_length=50, choices=TEMPLATE_CHOICES, default=TEMPLATE_GENERIC)
    message_body = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True)
    external_message_id = models.CharField(max_length=255, blank=True, default="")
    error_detail = models.TextField(blank=True, default="")
    queued_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-queued_at"]

    def __str__(self):
        return f"WA→{self.recipient_phone} [{self.status}]"


class WhatsAppInboundMessage(TenantModel):
    """
    Log of every inbound WhatsApp message from a customer.
    Story 10.5 — parsed by the ordering bridge webhook.
    """

    sender_phone = models.CharField(max_length=30, db_index=True)
    raw_body = models.TextField()
    parsed_intent = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Detected intent: 'order', 'menu', 'status', 'unknown'.",
    )
    response_sent = models.BooleanField(default=False)
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-received_at"]
