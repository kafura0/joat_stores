"""
Phone number normalization — canonical implementation in the core layer.

Placed in core/ (not apps/payment/) to avoid dependency inversion:
apps/ depends on core/, never the reverse.

normalize_phone(raw_phone, country_code='KE') -> str
  Converts phone numbers in any local format to E.164.
  Raises PhoneNormalizationError for unrecognizable formats.

Supported country codes: KE (Kenya), JM (Jamaica)

ARCHITECTURE RULE: Raw phone strings must NEVER reach Daraja, WhatsApp,
or SMS APIs directly. Always call normalize_phone() or
normalise_mpesa_phone() (from core/utils.py) first.

PII WARNING: PhoneNormalizationError.raw_phone contains the raw phone
string. Always mask it via mask_pii() before logging.

Implementation: Story 2.0
"""

import re


class PhoneNormalizationError(ValueError):
    """
    Raised when a phone number cannot be normalized to E.164.

    ValueError subclass so callers (e.g. initiate_payment in Story 2.2)
    can catch ValueError without importing this module directly.

    PII WARNING: raw_phone is the unmasked input. Mask before logging:
        logger.warning("bad phone", phone=mask_pii(exc.raw_phone))
    """

    def __init__(self, raw_phone: str, country_code: str, message: str) -> None:
        self.raw_phone = raw_phone
        self.country_code = country_code
        self.message = message
        super().__init__(message)


def _strip(raw: str) -> str:
    """Remove all non-digit characters."""
    return re.sub(r"\D", "", raw)


_KE_VALID_PREFIXES = (
    "7",
    "1",
)  # +2547XX (Safaricom/Airtel) and +2541XX (newer allocations)


def _ke_validate_significant(significant: str, raw: str) -> None:
    """
    Raise PhoneNormalizationError if the KE significant digits have an invalid prefix.

    Expects a non-empty string of exactly 9 digits. If significant is empty
    (should not happen with current callers), raises PhoneNormalizationError
    rather than allowing IndexError to propagate.
    """
    if not significant or not significant.startswith(_KE_VALID_PREFIXES):
        prefix_display = significant[0] if significant else "(empty)"
        raise PhoneNormalizationError(
            raw_phone=raw,
            country_code="KE",
            message=(
                f"Cannot normalize KE phone '{raw}': prefix '{prefix_display}' is not a valid "
                f"Kenyan mobile prefix. Expected 07XX (Safaricom) or 01XX (Airtel)."
            ),
        )


def _normalize_ke(raw: str) -> str:
    """
    Normalize a Kenyan phone number to E.164 (+254XXXXXXXXX).

    Valid input formats (after stripping non-digits):
      07XXXXXXXX   (10 digits, leading 0, prefix 07 or 01)
      254XXXXXXXX  (12 digits, leading 254, significant starts with 7 or 1)
      +254XXXXXXXX (already E.164, significant starts with 7 or 1)

    Raises PhoneNormalizationError for anything else, including invalid prefixes
    like 08XX, 09XX, 05XX which do not exist in Kenya's mobile allocation.
    """
    # Handle already-E.164 before stripping the +
    stripped_raw = raw.strip()
    if stripped_raw.startswith("+254"):
        digits = _strip(stripped_raw[1:])  # remove + by slicing, then strip non-digits
        if len(digits) == 12:  # 254 + 9 significant digits
            significant = digits[3:]
            _ke_validate_significant(significant, raw)
            return f"+{digits}"
        raise PhoneNormalizationError(
            raw_phone=raw,
            country_code="KE",
            message=f"Cannot normalize KE phone '{raw}': E.164 form has wrong length after +254",
        )

    digits = _strip(raw)

    if len(digits) == 10 and digits.startswith("0"):
        # 07XXXXXXXX or 01XXXXXXXX — strip leading 0, prepend +254
        significant = digits[1:]  # 9 significant digits
        _ke_validate_significant(significant, raw)
        return f"+254{significant}"

    if len(digits) == 12 and digits.startswith("254"):
        # 254XXXXXXXXX — prepend +
        significant = digits[3:]
        _ke_validate_significant(significant, raw)
        return f"+{digits}"

    raise PhoneNormalizationError(
        raw_phone=raw,
        country_code="KE",
        message=(
            f"Cannot normalize KE phone '{raw}': expected 07XXXXXXXX (10 digits), "
            f"254XXXXXXXXX (12 digits), or +254XXXXXXXXX (E.164). Got {len(digits)} digits."
        ),
    )


def _normalize_jm(raw: str) -> str:
    """
    Normalize a Jamaican phone number to E.164 (+1876XXXXXXX).

    Valid input formats (after stripping non-digits):
      876XXXXXXX   (10 digits, local with area code)
      1876XXXXXXX  (11 digits, with NANP country code)
      +1876XXXXXXX (already E.164)

    Raises PhoneNormalizationError for anything else.
    """
    stripped_raw = raw.strip()
    if stripped_raw.startswith("+1876"):
        digits = _strip(stripped_raw[1:])  # remove + by slicing, then strip non-digits
        if len(digits) == 11:  # 1876 + 7 subscriber digits
            return f"+{digits}"
        raise PhoneNormalizationError(
            raw_phone=raw,
            country_code="JM",
            message=f"Cannot normalize JM phone '{raw}': E.164 form has wrong length after +1876",
        )

    digits = _strip(raw)

    if len(digits) == 10 and digits.startswith("876"):
        return f"+1{digits}"

    if len(digits) == 11 and digits.startswith("1876"):
        return f"+{digits}"

    raise PhoneNormalizationError(
        raw_phone=raw,
        country_code="JM",
        message=(
            f"Cannot normalize JM phone '{raw}': expected 876XXXXXXX (10 digits), "
            f"1876XXXXXXX (11 digits), or +1876XXXXXXX (E.164). Got '{digits}'."
        ),
    )


_COUNTRY_HANDLERS = {
    "KE": _normalize_ke,
    "JM": _normalize_jm,
}


def normalize_phone(raw_phone: str, country_code: str = "KE") -> str:
    """
    Normalize a phone number to E.164 format.

    Args:
        raw_phone:    Phone number in any local format.
        country_code: ISO 3166-1 alpha-2 country code (default: 'KE').

    Returns:
        E.164 formatted phone string, e.g. '+254712345678'.

    Raises:
        PhoneNormalizationError: If the number cannot be normalized.
            This is a ValueError subclass — callers can catch ValueError
            without importing this module directly.

    Examples:
        >>> normalize_phone('0712345678', country_code='KE')
        '+254712345678'
        >>> normalize_phone('8761234567', country_code='JM')
        '+18761234567'
    """
    handler = _COUNTRY_HANDLERS.get(country_code)
    if handler is None:
        raise PhoneNormalizationError(
            raw_phone=raw_phone,
            country_code=country_code,
            message=(
                f"UNSUPPORTED_COUNTRY: country_code '{country_code}' is not supported. "
                f"Supported: {sorted(_COUNTRY_HANDLERS)}"
            ),
        )
    return handler(raw_phone)
