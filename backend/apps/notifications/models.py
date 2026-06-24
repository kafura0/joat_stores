"""
Notifications models — Epic 10.

Story 10.3: WhatsAppMessage — outbound message log (append-only)
Story 10.5: WhatsApp ordering bridge — inbound message parsing log
FCM (cross-tenant): FCMDevice — push notification device registration
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


# ---------------------------------------------------------------------------
# FCM push notifications (cross-tenant customer hub)
# ---------------------------------------------------------------------------


class FCMDevice(models.Model):
    """
    A mobile device registered for push notifications.

    NOT a tenant model — devices are cross-tenant, linked to PlatformUser.
    One PlatformUser can have multiple devices (phone + tablet, Android + iOS).
    """

    PLATFORM_ANDROID = "android"
    PLATFORM_IOS = "ios"
    PLATFORM_WEB = "web"

    PLATFORM_CHOICES = [
        (PLATFORM_ANDROID, _("Android")),
        (PLATFORM_IOS, _("iOS")),
        (PLATFORM_WEB, _("Web")),
    ]

    platform_user = models.ForeignKey(
        "users.PlatformUser",
        on_delete=models.CASCADE,
        related_name="fcm_devices",
    )
    registration_id = models.TextField(
        help_text="FCM device token from the mobile app.",
    )
    platform = models.CharField(
        max_length=10,
        choices=PLATFORM_CHOICES,
        default=PLATFORM_ANDROID,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("FCM Device")
        verbose_name_plural = _("FCM Devices")
        ordering = ["-created_at"]
        unique_together = [("platform_user", "registration_id")]

    def __str__(self):
        return f"{self.platform}:{self.registration_id[:16]}... @ {self.platform_user.email}"
