"""Payment models — MpesaTransaction + CardTransaction lifecycle tracking.

MpesaTransaction records every STK Push initiation through to final status.
CardTransaction records every card payment initiated via Stripe PaymentIntent.

Implementation: Story 2.2, Story 2.6
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


class CardTransactionStatus(models.TextChoices):
    PAYMENT_INTENT_CREATED = "PI_CREATED", _("Payment Intent Created")
    PROCESSING = "PROCESSING", _("Processing")
    SUCCEEDED = "SUCCEEDED", _("Succeeded")
    FAILED = "FAILED", _("Failed")
    REFUNDED = "REFUNDED", _("Refunded")


class CardTransaction(TenantModel):
    """
    Card payment transaction via Stripe PaymentIntent.

    Tracks the full lifecycle from intent creation through webhook confirmation.
    One record per PaymentIntent; idempotency enforced in services.py.
    """

    reference = models.CharField(max_length=100, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="kes")
    status = models.CharField(
        max_length=30,
        choices=CardTransactionStatus.choices,
        default=CardTransactionStatus.PAYMENT_INTENT_CREATED,
    )
    stripe_payment_intent_id = models.CharField(
        max_length=255, unique=True, null=True, blank=True
    )
    stripe_client_secret = models.TextField(blank=True, default="")
    provider = models.CharField(
        max_length=20, default="stripe",
        help_text="Card provider: 'stripe' or 'flutterwave'",
    )
    customer_email = models.EmailField(blank=True, default="")
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True, default="")

    class Meta:
        db_table = "payment_cardtransaction"
        indexes = [
            models.Index(
                fields=["store", "reference"],
                name="payment_card_store_ref_idx",
            ),
            models.Index(
                fields=["stripe_payment_intent_id"],
                name="payment_card_pi_idx",
            ),
        ]

    def __str__(self):
        return f"CardTransaction({self.reference}, {self.status}, {self.provider})"
