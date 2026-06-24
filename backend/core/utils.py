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
    "format_currency",
    "mask_pii",
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


def format_currency(amount, currency="KES") -> str:
    """Format a Decimal as a currency string.

    Examples:
        >>> format_currency(Decimal("1500.00"))
        'KES 1,500'
        >>> format_currency(Decimal("0.50"))
        'KES 0.50'
    """
    from decimal import Decimal, ROUND_DOWN

    if amount is None:
        amount = Decimal("0")
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    amount = amount.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    # Remove trailing zeros for whole numbers
    if amount == amount.to_integral_value():
        amount = amount.quantize(Decimal("1"), rounding=ROUND_DOWN)
    formatted = f"{amount:,.2f}" if amount % 1 else f"{amount:,.0f}"
    return f"{currency} {formatted}"


def mask_pii(value: str) -> str:
    """Mask personally identifiable information for logging.

    Masks email addresses and phone numbers. Required by Kenya DPA 2019 —
    never log raw PII.

    Examples:
        >>> mask_pii("john@email.com")
        'j***@email.com'
        >>> mask_pii("+254712345678")
        '+254*****678'
        >>> mask_pii("short")
        '*****'
    """
    if not value:
        return value

    # Email masking: j***@email.com
    if "@" in value:
        local, domain = value.split("@", 1)
        if len(local) <= 1:
            return f"{local}***@{domain}"
        return f"{local[0]}***@{domain}"

    # Phone masking: +254*****678
    stripped = value.strip()
    if len(stripped) >= 8:
        return stripped[:4] + "*****" + stripped[-3:]

    # Short value: full mask
    return "*****"
