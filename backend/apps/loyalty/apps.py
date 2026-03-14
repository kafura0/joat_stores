"""
Loyalty app config — Epic 10.

Connects payment_confirmed signal to award loyalty points and stamps
after each confirmed order payment.
"""

import structlog
from django.apps import AppConfig

log = structlog.get_logger(__name__)


class LoyaltyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.loyalty"

    def ready(self):
        from apps.payment.signals import payment_confirmed
        payment_confirmed.connect(_handle_loyalty_on_payment)


def _handle_loyalty_on_payment(sender, transaction, **kwargs):
    """
    Award loyalty points + stamps when a retail order is confirmed via M-Pesa.

    Only handles "order-{order_id}" references — all other prefixes ignored.
    """
    ref = getattr(transaction, "reference", "")
    if not ref.startswith("order-"):
        return

    order_id = ref[len("order-"):]
    try:
        from django.db import transaction as db_tx
        from apps.order.models import Order

        order = Order.objects.get(id=order_id)
        store_id = str(order.store_id)
        phone = order.customer_phone
        amount = str(order.total_amount)

        from apps.loyalty.tasks import award_loyalty_points, award_stamp, update_customer_profile

        db_tx.on_commit(lambda: award_loyalty_points.delay(store_id, phone, amount, order_id))
        db_tx.on_commit(lambda: award_stamp.delay(store_id, phone, order_id))
        db_tx.on_commit(lambda: update_customer_profile.delay(
            store_id, phone, amount,
            customer_name=order.customer_name,
            customer_email=order.customer_email,
        ))

    except Exception as exc:
        log.error("loyalty_signal_error", order_id=order_id, error=str(exc))
