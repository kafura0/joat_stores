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

    Story 3.10 — When an M-Pesa transaction for a takeaway DineInOrder is confirmed,
    generate a pickup reference and dispatch notification.

    Story 3.11 — When an M-Pesa transaction for a BillShare is confirmed,
    mark the share PAID and auto-close the session when all shares are settled.

    Reference formats:
        "pending-{order_id}"    → PendingOrder payment
        "takeaway-{order_id}"   → Takeaway DineInOrder payment
        "bill-share-{share_id}" → BillShare payment
    """
    ref = getattr(transaction, "reference", "")

    if ref.startswith("pending-"):
        order_id = ref[len("pending-"):]
        try:
            from apps.restaurant.models import PendingOrder

            order = PendingOrder.objects.get(id=order_id, status=PendingOrder.STATUS_PENDING)
            order.status = PendingOrder.STATUS_PAID
            order.save(update_fields=["status"])
            log.info("pending_order_paid", order_id=order_id, transaction_id=str(transaction.id))
        except PendingOrder.DoesNotExist:
            log.warning("pending_order_payment_confirmed_order_not_found", order_id=order_id)
        except Exception as exc:
            log.error("pending_order_payment_signal_error", order_id=order_id, error=str(exc))

    elif ref.startswith("takeaway-"):
        order_id = ref[len("takeaway-"):]
        try:
            from apps.restaurant.tasks import send_takeaway_pickup_reference

            send_takeaway_pickup_reference.apply_async(args=[order_id], countdown=0)
            log.info("takeaway_payment_confirmed", order_id=order_id)
        except Exception as exc:
            log.error("takeaway_payment_signal_error", order_id=order_id, error=str(exc))

    elif ref.startswith("bill-share-"):
        share_id = ref[len("bill-share-"):]
        try:
            from apps.restaurant.models import BillShare, TableSession

            share = BillShare.objects.select_related("session").get(id=share_id)
            share.status = BillShare.STATUS_PAID
            share.payment_transaction = transaction
            share.save(update_fields=["status", "payment_transaction"])
            log.info("bill_share_paid", share_id=share_id, session_id=str(share.session_id))

            # Auto-close session when all shares are PAID (Story 3.11 AC3)
            session = share.session
            unpaid = BillShare.objects.filter(
                session=session,
                status=BillShare.STATUS_PENDING,
            ).exists()
            if not unpaid:
                try:
                    session.transition(TableSession.STATUS_CLOSED)
                    log.info("session_auto_closed_all_shares_paid", session_id=str(session.id))
                except Exception as close_exc:
                    log.warning("session_auto_close_failed", session_id=str(session.id), error=str(close_exc))
        except BillShare.DoesNotExist:
            log.warning("bill_share_payment_confirmed_share_not_found", share_id=share_id)
        except Exception as exc:
            log.error("bill_share_payment_signal_error", share_id=share_id, error=str(exc))
