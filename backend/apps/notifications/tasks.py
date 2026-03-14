"""
Notifications tasks — Epic 10.

Story 10.3: send_whatsapp_notification — log outbound WhatsApp message
            (Twilio/Meta API call stubbed — logs in dev, wire up in prod).
"""

import structlog
from celery import shared_task

from core.tasks import DLQTask

logger = structlog.get_logger(__name__)


@shared_task(
    bind=True,
    base=DLQTask,
    queue="order.notifications",
    max_retries=3,
)
def send_whatsapp_notification(
    self,
    store_id: str,
    recipient_phone: str,
    message_body: str,
    template: str = "generic",
) -> None:
    """
    Story 10.3 — Send a WhatsApp message to a customer.

    Production: wire up Twilio API or Meta Cloud API here.
    Current: log + update WhatsAppMessage record status.

    The WhatsAppMessage is created here (not before enqueueing) to avoid
    creating orphaned records if task dispatch fails.
    """
    try:
        from apps.store.models import Store
        from apps.notifications.models import WhatsAppMessage
        from django.utils import timezone

        store = Store.objects.get(id=store_id)

        msg = WhatsAppMessage.objects.create(
            store=store,
            recipient_phone=recipient_phone,
            template=template,
            message_body=message_body,
            status=WhatsAppMessage.STATUS_QUEUED,
        )

        # --- Production: replace this block with real API call ---
        # e.g. twilio_client.messages.create(to=recipient_phone, from_=TWILIO_WA_NUMBER, body=message_body)
        # For now: simulate success
        logger.info(
            "whatsapp_message_sent_stub",
            store_id=store_id,
            phone=recipient_phone,
            template=template,
            message_id=msg.id,
        )
        msg.status = WhatsAppMessage.STATUS_SENT
        msg.sent_at = timezone.now()
        msg.save(update_fields=["status", "sent_at"])

    except Exception as exc:
        logger.exception(
            "whatsapp_send_failed",
            store_id=store_id,
            phone=recipient_phone,
        )
        # Mark as failed if we have a msg record
        try:
            msg.status = WhatsAppMessage.STATUS_FAILED
            msg.error_detail = str(exc)
            msg.save(update_fields=["status", "error_detail"])
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
