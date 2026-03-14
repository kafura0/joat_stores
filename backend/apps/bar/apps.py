"""
Bar app configuration.

Connects the payment_confirmed signal to auto-settle tabs when all TabShares are PAID.
"""

from django.apps import AppConfig


class BarConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bar"

    def ready(self):
        from apps.payment.signals import payment_confirmed

        payment_confirmed.connect(_handle_payment_confirmed)


def _handle_payment_confirmed(sender, transaction, **kwargs):
    """
    Story 5.5 — When a tab-share payment is confirmed:
      1. Mark the TabShare as PAID and link the transaction.
      2. If all TabShares for the tab are PAID → transition Tab to SETTLED.

    Partial failures (some shares FAILED or PENDING) leave the tab in BILL_REQUESTED.
    Confirmed payments from other payers are NOT reversed.
    """
    ref = getattr(transaction, "reference", "")
    if not ref.startswith("tab-share-"):
        return

    share_id = ref[len("tab-share-"):]

    try:
        from apps.bar.models import Tab, TabShare

        share = TabShare.objects.select_related("tab").get(id=share_id)
        share.status = TabShare.STATUS_PAID
        share.payment_transaction = transaction
        share.save(update_fields=["status", "payment_transaction"])

        tab = share.tab

        # Check if all shares are now PAID
        unpaid = TabShare.objects.filter(
            tab=tab,
            status=TabShare.STATUS_PENDING,
        ).exists()

        if not unpaid:
            tab.transition(Tab.STATUS_SETTLED)

    except Exception:
        # Never let signal handler crash the webhook response
        import logging
        logging.getLogger(__name__).exception(
            "bar._handle_payment_confirmed failed for share_id=%s", share_id
        )
