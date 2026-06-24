"""
Notifications tasks — Epic 10.

Story 10.3: send_whatsapp_notification — log outbound WhatsApp message
            (Twilio/Meta API call stubbed — logs in dev, wire up in prod).
FCM: send_push_notification — Firebase Cloud Messaging push (stubbed).
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

        # --- Twilio WhatsApp API call ---
        from django.conf import settings

        account_sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        whatsapp_from = settings.TWILIO_WHATSAPP_FROM

        if account_sid and auth_token and whatsapp_from:
            from twilio.rest import Client

            client = Client(account_sid, auth_token)
            twilio_msg = client.messages.create(
                to=f"whatsapp:{recipient_phone}",
                from_=f"whatsapp:{whatsapp_from}",
                body=message_body,
            )
            msg.external_message_id = twilio_msg.sid
            logger.info(
                "whatsapp_message_sent",
                store_id=store_id,
                phone=recipient_phone,
                template=template,
                twilio_sid=twilio_msg.sid,
            )
        else:
            logger.info(
                "whatsapp_message_sent_stub",
                store_id=store_id,
                phone=recipient_phone,
                template=template,
                message_id=msg.id,
                detail="TWILIO_ACCOUNT_SID not configured — message logged only",
            )
        msg.status = WhatsAppMessage.STATUS_SENT
        msg.sent_at = timezone.now()
        msg.save(update_fields=["status", "sent_at", "external_message_id"])

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


@shared_task(
    bind=True,
    base=DLQTask,
    queue="order.notifications",
    max_retries=3,
)
def send_push_notification(
    self,
    platform_user_id: int,
    title: str,
    body: str,
    data: dict | None = None,
) -> None:
    """
    Send a push notification to all active FCM devices for a PlatformUser.

    Production: wire up Firebase Admin SDK here.
    Current: log + mark notification as sent (stub).
    """
    from apps.notifications.models import FCMDevice

    devices = FCMDevice.objects.filter(
        platform_user_id=platform_user_id,
        is_active=True,
    )

    if not devices.exists():
        logger.warning(
            "push_no_devices",
            platform_user_id=platform_user_id,
        )
        return

    sent_count = 0
    for device in devices:
        try:
            # --- Production: replace with Firebase Admin SDK ---
            # import firebase_admin
            # from firebase_admin import messaging
            # message = messaging.Message(
            #     notification=messaging.Notification(title=title, body=body),
            #     data=data or {},
            #     token=device.registration_id,
            # )
            # messaging.send(message)

            logger.info(
                "push_notification_stub",
                device_id=device.pk,
                platform=device.platform,
                token_prefix=device.registration_id[:16],
                title=title,
            )
            sent_count += 1

        except Exception as exc:
            logger.exception(
                "push_send_failed",
                device_id=device.pk,
                platform_user_id=platform_user_id,
            )

    logger.info(
        "push_notification_complete",
        platform_user_id=platform_user_id,
        sent_count=sent_count,
        total_devices=devices.count(),
    )
