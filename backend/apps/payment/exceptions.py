"""Payment exception hierarchy.

All exceptions are pure Python — no Django imports — so they are
testable without Django setup and importable from both daraja.py and
services.py without circular import risk.

Implementation: Story 2.2
"""


class PaymentError(Exception):
    """Base exception for all payment errors."""


class StkPushError(PaymentError):
    """Raised by DarajaClient when the STK Push API call fails."""


class StkPushInitiationError(PaymentError):
    """Raised by initiate_payment() when STK Push cannot be initiated."""


class InvalidPhoneNumberError(PaymentError):
    """Raised when phone normalization fails before a Daraja call."""


class UnsupportedPaymentMethodError(PaymentError):
    """Raised when an unsupported payment method is passed to initiate_payment()."""


class StkPushRateLimitedError(PaymentError):
    """Raised when a reference has exceeded 3 STK Push attempts per hour."""

    def __init__(self, retry_after):
        self.retry_after = retry_after  # datetime object
        super().__init__(f"Rate limited until {retry_after.isoformat()}")


class PaymentReversalError(PaymentError):
    """Raised when a reversal cannot proceed (wrong status or Daraja failure)."""


class ReversalError(PaymentError):
    """Raised by DarajaClient.initiate_reversal() on Daraja API failure."""


class TransactionStatusQueryError(PaymentError):
    """Raised by DarajaClient.query_transaction_status() on Daraja API failure."""
