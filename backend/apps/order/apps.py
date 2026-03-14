import structlog
from django.apps import AppConfig

log = structlog.get_logger(__name__)


class OrderConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.order"

    def ready(self):
        """Connect payment_confirmed signal for retail order confirmation."""
        from apps.payment.signals import payment_confirmed

        payment_confirmed.connect(_handle_order_payment_confirmed)


def _handle_order_payment_confirmed(sender, transaction, **kwargs):
    """
    Story 4.4 — When M-Pesa confirms an order payment, transition order
    to 'confirmed' and dispatch confirmation email task.

    Reference format: "order-{order_id}"
    """
    ref = getattr(transaction, "reference", "")
    if not ref.startswith("order-"):
        return

    order_id = ref[len("order-"):]
    try:
        from django.db import transaction as db_tx

        from apps.order.models import Order, OrderStatus
        from apps.order.tasks import send_order_confirmation

        order = Order.objects.get(id=order_id, status=OrderStatus.PENDING)
        order.payment_transaction = transaction
        order.save(update_fields=["payment_transaction"])
        order.transition_status(OrderStatus.CONFIRMED)

        db_tx.on_commit(
            lambda: send_order_confirmation.apply_async(args=[str(order.id)])
        )
        # Story 8.7 — first order milestone (idempotent, via on_commit)
        _store_id = str(order.store_id)
        _order_id = str(order.id)
        db_tx.on_commit(
            lambda: _dispatch_first_order_check(_store_id, _order_id)
        )

        log.info("order_payment_confirmed", order_id=order_id)
    except Order.DoesNotExist:
        log.warning("order_payment_confirmed_order_not_found", order_id=order_id)
    except Exception as exc:
        log.error("order_payment_confirmed_error", order_id=order_id, error=str(exc))


def _dispatch_first_order_check(store_id: str, order_id: str) -> None:
    """Dispatch first-order milestone check (non-fatal)."""
    try:
        from apps.analytics.tasks import record_first_order_event
        record_first_order_event.delay(store_id, order_id)
    except Exception:
        pass
