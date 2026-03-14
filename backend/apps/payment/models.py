"""Payment models — MpesaTransaction lifecycle tracking.

MpesaTransaction records every STK Push initiation through to final status.
One record per reference per attempt; idempotency enforced in services.py.

Implementation: Story 2.2
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import TenantModel


class MpesaTransactionStatus(models.TextChoices):
    STK_PUSH_INITIATED = "STK_PUSH_INITIATED", _("STK Push Initiated")
    CONFIRMED = "CONFIRMED", _("Confirmed")
    EXPIRED = "EXPIRED", _("Expired")
    FAILED = "FAILED", _("Failed")
    REVERSED = "REVERSED", _("Reversed")


class MpesaTransaction(TenantModel):
    reference = models.CharField(max_length=100, db_index=True)
    phone = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=30,
        choices=MpesaTransactionStatus.choices,
        default=MpesaTransactionStatus.STK_PUSH_INITIATED,
    )
    checkout_request_id = models.CharField(max_length=100, blank=True, default="")
    mpesa_receipt_number = models.CharField(
        max_length=50, unique=True, null=True, blank=True
    )
    merchant_request_id = models.CharField(max_length=100, blank=True, default="")
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    reversal_reason = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "payment_mpesatransaction"
        indexes = [
            models.Index(
                fields=["store", "reference"],
                name="payment_mpesa_store_ref_idx",
            ),
        ]

    def __str__(self):
        return f"MpesaTransaction({self.reference}, {self.status})"
