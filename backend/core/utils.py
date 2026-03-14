"""
Shared utility functions used across all apps.

normalise_mpesa_phone(phone: str) -> str
  Converts Kenyan phone numbers to E.164 format for Daraja API.
  Examples: "0712345678" → "+254712345678", "254712345678" → "+254712345678"
  Raises PhoneNormalizationError (ValueError subclass) if number is invalid.

  ARCHITECTURE RULE: All callers MUST use this function — never inline
  phone normalisation in a view, serializer, or task.

format_currency(amount: Decimal) -> str
  Formats Decimal as KES string. Example: Decimal("1500.00") → "KES 1,500"

mask_pii(value: str) -> str
  Masks PII for logs. Example: "john@email.com" → "j***@email.com"
  Required by Kenya DPA 2019 — never log raw PII.

Implementation: Story 2.0 (normalise_mpesa_phone), Story 1.6 (mask_pii, format_currency)
"""

from core.phone import PhoneNormalizationError, normalize_phone

# Re-export so callers don't need to know the implementation module.
# mask_pii and format_currency are defined here once Story 1.6 TODO is resolved.
__all__ = [
    "normalise_mpesa_phone",
    "PhoneNormalizationError",
]


def normalise_mpesa_phone(raw: str) -> str:
    """
    Canonical KE phone normalisation entry point for all callers.

    Delegates to normalize_phone(raw, country_code='KE') in apps.payment.phone.
    Raises PhoneNormalizationError (ValueError subclass) for invalid numbers.

    Examples:
        >>> normalise_mpesa_phone('0712345678')
        '+254712345678'
        >>> normalise_mpesa_phone('+254712345678')
        '+254712345678'
    """
    return normalize_phone(raw, country_code="KE")


# TODO: Story 1.6 — implement mask_pii, format_currency
