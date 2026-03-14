"""
Tests for apps/payment/phone.py — normalize_phone + PhoneNormalizationError.

Pure unit tests: no Django DB, no fixtures, no factory-boy.
All tests should pass without Django setup.

Implementation: Story 2.0
"""

import pytest

from apps.payment.phone import PhoneNormalizationError, normalize_phone

# ── AC1, AC2, AC3 — KE happy path ────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        # AC1: local 07XX format
        ("0712345678", "+254712345678"),
        ("0700000000", "+254700000000"),
        ("0799999999", "+254799999999"),
        # AC2: 254XX without leading +
        ("254712345678", "+254712345678"),
        ("254100000000", "+254100000000"),
        # AC3: already E.164
        ("+254712345678", "+254712345678"),
        ("+254100000000", "+254100000000"),
        # Whitespace/formatting stripped
        (" 0712345678 ", "+254712345678"),
        ("0712-345-678", "+254712345678"),
        ("+254 712 345 678", "+254712345678"),
    ],
)
def test_ke_normalization_happy_path(raw, expected):
    """AC1/AC2/AC3: All three KE formats normalize to E.164 +254XXXXXXXXX."""
    assert normalize_phone(raw, country_code="KE") == expected


def test_ke_default_country_code():
    """country_code defaults to 'KE'."""
    assert normalize_phone("0712345678") == "+254712345678"


# ── AC4 — KE invalid formats raise PhoneNormalizationError ───────────────────


@pytest.mark.parametrize(
    "raw",
    [
        "0812345678",  # 08 prefix — not a valid KE mobile prefix
        "0912345678",  # 09 prefix — not valid
        "0512345678",  # 05 prefix — not valid
        "12345",  # too short
        "071234567",  # 9 digits — one short
        "07123456789",  # 11 digits — one long
        "",  # empty
        "abcdefghij",  # non-numeric
        "00712345678",  # double leading zero
    ],
)
def test_ke_invalid_raises(raw):
    """AC4: Invalid KE numbers raise PhoneNormalizationError."""
    with pytest.raises(PhoneNormalizationError) as exc_info:
        normalize_phone(raw, country_code="KE")
    err = exc_info.value
    assert err.raw_phone == raw
    assert err.country_code == "KE"
    assert err.message  # descriptive, non-empty


# ── AC5 — JM format ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        # 10-digit local (876XXXXXXX)
        ("8761234567", "+18761234567"),
        ("8769999999", "+18769999999"),
        # 11-digit with country code (1876XXXXXXX)
        ("18761234567", "+18761234567"),
        # Already E.164
        ("+18761234567", "+18761234567"),
        # With formatting
        ("876-123-4567", "+18761234567"),
        ("+1 876 123 4567", "+18761234567"),
    ],
)
def test_jm_normalization_happy_path(raw, expected):
    """AC5: JM numbers normalize to E.164 +1876XXXXXXX."""
    assert normalize_phone(raw, country_code="JM") == expected


@pytest.mark.parametrize(
    "raw",
    [
        "7761234567",  # wrong area code for JM
        "123456",  # too short
        "",  # empty
    ],
)
def test_jm_invalid_raises(raw):
    """JM invalid numbers raise PhoneNormalizationError with correct attributes."""
    with pytest.raises(PhoneNormalizationError) as exc_info:
        normalize_phone(raw, country_code="JM")
    err = exc_info.value
    assert err.raw_phone == raw
    assert err.country_code == "JM"
    assert err.message  # descriptive, non-empty


# ── Unsupported country code ──────────────────────────────────────────────────


def test_unsupported_country_code_raises():
    """Unsupported country codes raise PhoneNormalizationError with correct attributes."""
    raw = "0712345678"
    with pytest.raises(PhoneNormalizationError) as exc_info:
        normalize_phone(raw, country_code="US")
    err = exc_info.value
    assert err.raw_phone == raw
    assert err.country_code == "US"
    assert "UNSUPPORTED_COUNTRY" in err.message or "unsupported" in err.message.lower()
    assert err.message  # descriptive, non-empty


# ── PhoneNormalizationError is ValueError subclass ───────────────────────────


def test_phone_normalization_error_is_value_error():
    """PhoneNormalizationError must be a ValueError subclass (Story 2.2 will catch it for HTTP 422)."""
    with pytest.raises(ValueError):
        normalize_phone("0812345678", country_code="KE")


# ── Pure function — no Django dependency ─────────────────────────────────────


def test_importable_without_django_setup():
    """normalize_phone is importable and callable without any Django setup."""
    # If this test runs at all, the import succeeded without Django
    result = normalize_phone("0712345678", country_code="KE")
    assert result == "+254712345678"


# ── normalise_mpesa_phone shim (core/utils.py integration) ───────────────────


def test_normalise_mpesa_phone_delegates():
    """AC7: normalise_mpesa_phone in core/utils.py delegates to normalize_phone(KE)."""
    from core.utils import normalise_mpesa_phone

    assert normalise_mpesa_phone("0712345678") == "+254712345678"
    assert normalise_mpesa_phone("254712345678") == "+254712345678"
    assert normalise_mpesa_phone("+254712345678") == "+254712345678"


def test_normalise_mpesa_phone_raises_on_invalid():
    """normalise_mpesa_phone raises PhoneNormalizationError for invalid KE numbers."""
    from core.utils import normalise_mpesa_phone

    with pytest.raises(PhoneNormalizationError):
        normalise_mpesa_phone("0812345678")
