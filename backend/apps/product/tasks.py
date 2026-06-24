"""
Celery tasks for product catalog — Story 4.1.
"""

import structlog
from celery import shared_task

log = structlog.get_logger(__name__)


@shared_task(
    bind=True,
    max_retries=5,
    queue="inventory.alerts",
    default_retry_delay=60,
)
def send_low_stock_alert(self, variant_id: str) -> None:
    """
    Story 4.1 — Notify store owner when a variant's inventory_count is at or
    below the configured low-stock threshold.

    Dispatched via transaction.on_commit from Variant.save() → inventory.alerts queue.
    Exponential backoff: countdown = 60 * (2 ** retries), max 5 retries.
    """
    try:
        from apps.product.models import Variant

        variant = Variant.objects.select_related("product", "store").get(id=variant_id)
        store = variant.store

        log.info(
            "low_stock_alert",
            variant_id=variant_id,
            product_name=variant.product.name,
            inventory_count=variant.inventory_count,
            store_id=str(store.id),
        )

        # Notify store owner via WhatsApp + email
        from django.contrib.auth import get_user_model
        from apps.notifications.tasks import send_whatsapp_notification

        User = get_user_model()
        owners = User.objects.filter(store=store, role="store_owner").only("phone", "email")[:2]

        msg = (
            f"Low stock alert for {variant.product.name} at {store.name}. "
            f"Current inventory: {variant.inventory_count}. "
            "Please reorder soon."
        )

        for owner in owners:
            if owner.phone:
                send_whatsapp_notification.delay(
                    store_id=str(store.id),
                    recipient_phone=owner.phone,
                    message_body=msg,
                    template="generic",
                )
            if owner.email:
                try:
                    from django.conf import settings
                    from django.core.mail import send_mail

                    if settings.EMAIL_HOST:
                        send_mail(
                            subject=f"Low Stock Alert: {variant.product.name}",
                            message=msg,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[owner.email],
                            fail_silently=True,
                        )
                except Exception:
                    log.exception("low_stock_email_failed", variant_id=variant_id)

    except Exception as exc:
        log.error("low_stock_alert_failed", variant_id=variant_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
