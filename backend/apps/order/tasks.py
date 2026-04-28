"""
Order async tasks — Stories 4.3, 4.6.

Queue: order.notifications
DLQ: max_retries=5, countdown = 60 * (2 ** retries)
"""

import structlog
from celery import shared_task

log = structlog.get_logger(__name__)


@shared_task(
    bind=True,
    max_retries=5,
    queue="order.notifications",
    default_retry_delay=60,
)
def send_order_confirmation(self, order_id: str) -> None:
    """
    Story 4.3 / 4.6 — Send order confirmation email within 60s of order.confirmed.
    Dispatched via transaction.on_commit when order transitions to 'confirmed'.

    Email includes: order number, itemized variants, total paid, delivery/pickup details.
    Exponential backoff: countdown = 60 * (2 ** retries), max 5 retries → DLQ.
    """
    try:
        from django.conf import settings
        from django.core.mail import send_mail

        from apps.order.models import Order

        order = Order.objects.select_related("store").get(id=order_id)

        if not order.customer_email:
            log.info("order_confirmation_no_email", order_id=order_id, store_id=str(order.store_id))
            return

        order_ref = str(order.id).split("-")[0].upper()
        item_lines = "\n".join(
            f"  {item.get('product_name') or item.get('name') or 'Item'}"
            f" x{item.get('quantity', 1)}"
            f" — KES {item.get('unit_price') or item.get('price', 0)}"
            for item in order.items_snapshot
        ) or "  (no items)"

        message = (
            f"Hi {order.customer_name or 'there'},\n\n"
            f"Your order at {order.store.name} has been confirmed.\n\n"
            f"Order ref: #{order_ref}\n"
            f"Items:\n{item_lines}\n\n"
            f"Total: KES {order.total_amount}\n\n"
            f"Thank you for your purchase!\n"
            f"— The {order.store.name} team\n"
        )

        send_mail(
            subject=f"Order Confirmed — #{order_ref}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer_email],
            fail_silently=False,
        )
        log.info(
            "order_confirmation_email_sent",
            order_id=order_id,
            store_id=str(order.store_id),
            customer_email=order.customer_email,
        )

    except Exception as exc:
        log.error("order_confirmation_failed", order_id=order_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(
    bind=True,
    max_retries=5,
    queue="inventory.alerts",
    default_retry_delay=60,
)
def send_low_stock_alert_for_order(self, order_id: str) -> None:
    """
    Story 4.6 — After order confirmed, check if any ordered variants are now low-stock.
    Sends a consolidated email to the store owner if any items are below threshold.
    """
    try:
        from django.conf import settings
        from django.core.mail import send_mail

        from apps.order.models import Order
        from apps.product.models import Variant
        from apps.users.models import User

        order = Order.objects.select_related("store").get(id=order_id)
        low_stock = []

        for item in order.items_snapshot:
            vid = item.get("variant_id")
            if not vid:
                continue
            try:
                variant = Variant.objects.select_related("product").get(id=vid)
                threshold = variant._get_low_stock_threshold()
                if variant.inventory_count <= threshold:
                    low_stock.append((variant, threshold))
                    log.info(
                        "low_stock_after_order",
                        order_id=order_id,
                        variant_id=vid,
                        inventory_count=variant.inventory_count,
                    )
            except Variant.DoesNotExist:
                pass

        if not low_stock:
            return

        owner = User.objects.filter(store=order.store, role="store_owner").first()
        if not owner or not owner.email:
            log.warning(
                "low_stock_alert_no_owner_email",
                order_id=order_id,
                store_id=str(order.store_id),
            )
            return

        order_ref = str(order.id).split("-")[0].upper()
        lines = "\n".join(
            f"  - {v.product.name} – {v.name}: {v.inventory_count} left (threshold: {t})"
            for v, t in low_stock
        )
        send_mail(
            subject=f"Low Stock Alert — {order.store.name}",
            message=(
                f"After order #{order_ref}, the following items are running low:\n\n"
                f"{lines}\n\n"
                f"Please restock soon to avoid stockouts.\n"
                f"— joat_stores\n"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[owner.email],
            fail_silently=False,
        )
        log.info(
            "low_stock_alert_sent",
            order_id=order_id,
            store_id=str(order.store_id),
            item_count=len(low_stock),
        )

    except Exception as exc:
        log.error("low_stock_order_check_failed", order_id=order_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
