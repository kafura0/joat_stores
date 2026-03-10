"""
PII audit logging utilities for Kenya DPA 2019 compliance.

log_pii_access() — creates an AdminPIIAccessLog entry
scrub_pii()      — structlog processor that masks phone/email in logs

The AdminPIIAccessLog model lives in apps.analytics.models.

Implementation: Story 1.6
"""

import hashlib
import re


def log_pii_access(user, store, record_type, record_id, path="", method=""):
    """
    Create a PII access log entry.

    Use this in views/signals when admin users access customer PII.
    Lazy import to avoid circular dependency at module load.
    """
    from apps.analytics.models import AdminPIIAccessLog

    AdminPIIAccessLog.objects.create(
        user=user,
        store=store,
        record_type=record_type,
        record_id=str(record_id),
        path=path,
        method=method,
    )


# ---------------------------------------------------------------------------
# structlog PII scrubber processor
# ---------------------------------------------------------------------------

_PHONE_PATTERN = re.compile(r"(\+?254|0)\d{9}")  # Kenyan phone numbers
_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def _mask_phone(match):
    """Mask phone number, keeping last 4 digits."""
    phone = match.group(0)
    return f"****{phone[-4:]}"


def _mask_email(match):
    """Hash email prefix, keep domain."""
    email = match.group(0)
    local, domain = email.rsplit("@", 1)
    hashed = hashlib.sha256(local.encode()).hexdigest()[:8]
    return f"{hashed}...@{domain}"


def scrub_pii(logger, method_name, event_dict):
    """
    structlog processor that masks PII in log output.

    Phone numbers: +254712345678 -> ****5678
    Emails: user@example.com -> a3f2e1b4...@example.com
    """
    for key, value in event_dict.items():
        if isinstance(value, str):
            value = _PHONE_PATTERN.sub(_mask_phone, value)
            value = _EMAIL_PATTERN.sub(_mask_email, value)
            event_dict[key] = value
    return event_dict
