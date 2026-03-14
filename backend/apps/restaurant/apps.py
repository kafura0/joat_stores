import structlog
from django.apps import AppConfig

log = structlog.get_logger(__name__)


class RestaurantConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.restaurant"

    def ready(self):
        """Connect payment_confirmed signal to update PendingOrder on M-Pesa confirmation."""
        from apps.payment.signals import payment_confirmed

        payment_confirmed.connect(_handle_payment_confirmed)


def _handle_payment_confirmed(sender, transaction, **kwargs):
    """
    Story 3.8 — When an M-Pesa transaction for a PendingOrder is confirmed,
    transition the PendingOrder status to PAID.

    Reference format: "pending-{order_id}" (set by the pay endpoint).
    """
    ref = getattr(transaction, "reference", "")
    if not ref.startswith("pending-"):
        return

    order_id = ref[len("pending-"):]
    try:
        from apps.restaurant.models import PendingOrder

        order = PendingOrder.objects.get(id=order_id, status=PendingOrder.STATUS_PENDING)
        order.status = PendingOrder.STATUS_PAID
        order.save(update_fields=["status"])
        log.info(
            "pending_order_paid",
            order_id=order_id,
            transaction_id=str(transaction.id),
        )
    except PendingOrder.DoesNotExist:
        # Already converted/expired — ignore
        log.warning("pending_order_payment_confirmed_order_not_found", order_id=order_id)
    except Exception as exc:
        log.error("pending_order_payment_signal_error", order_id=order_id, error=str(exc))
