"""
Contracting app configuration.

Connects payment_confirmed signal to mark Invoice PAID and settle Job.
"""

from django.apps import AppConfig


class ContractingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.contracting"

    def ready(self):
        from apps.payment.signals import payment_confirmed

        payment_confirmed.connect(_handle_payment_confirmed)


def _handle_payment_confirmed(sender, transaction, **kwargs):
    """
    Story 6.6 — When an invoice payment is confirmed:
      1. Mark Invoice.payment_status = PAID and link the transaction.
      2. Transition Job to SETTLED.

    Reference format: "invoice-{invoice_id}"
    """
    ref = getattr(transaction, "reference", "")
    if not ref.startswith("invoice-"):
        return

    invoice_id = ref[len("invoice-"):]

    try:
        from django.utils import timezone

        from apps.contracting.models import Invoice, Job

        invoice = Invoice.objects.select_related("job").get(id=invoice_id)
        invoice.payment_status = Invoice.PAYMENT_STATUS_PAID
        invoice.payment_transaction = transaction
        invoice.paid_at = timezone.now()
        invoice.save(update_fields=["payment_status", "payment_transaction", "paid_at"])

        job = invoice.job
        if job.status == Job.STATUS_COMPLETED:
            job.transition(Job.STATUS_SETTLED)

    except Exception:
        import logging

        logging.getLogger(__name__).exception(
            "contracting._handle_payment_confirmed failed for invoice_id=%s", invoice_id
        )
