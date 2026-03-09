"""
Shared utility functions used across all apps.

normalise_mpesa_phone(phone: str) -> str
  Converts phone numbers to E.164 format for Daraja API.
  Examples: "0712345678" → "+254712345678", "254712345678" → "+254712345678"
  Raises ValueError if number is invalid.

format_currency(amount: Decimal) -> str
  Formats Decimal as KES string. Example: Decimal("1500.00") → "KES 1,500"

mask_pii(value: str) -> str
  Masks PII for logs. Example: "john@email.com" → "j***@email.com"
  Required by Kenya DPA 2019 — never log raw PII.

Implementation: Story 1.2 (normalise_mpesa_phone), Story 1.6 (mask_pii)
"""
# TODO: Story 1.2 — implement normalise_mpesa_phone
# TODO: Story 1.6 — implement mask_pii, format_currency
