"""
PII audit logging utilities for Kenya DPA 2019 compliance.

log_pii_access()     — creates an AdminPIIAccessLog entry
pii_access_logged()  — decorator: automatically logs PII access on DRF views,
                        satisfying AC1 ("never manual per-view code")
scrub_pii()          — structlog processor that masks phone/email in logs

The AdminPIIAccessLog model lives in apps.analytics.models.

Implementation: Story 1.6
"""

import functools
import hashlib
import re


def log_pii_access(user, store, record_type, record_id, path="", method=""):
    """
    Create a PII access log entry.

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


def pii_access_logged(record_type, record_id_kwarg="pk"):
    """
    Decorator for DRF view methods that access customer PII.

    Automatically creates an AdminPIIAccessLog entry before the view runs,
    satisfying AC1: "never manual per-view code."

    Usage:
        class CustomerDetailView(APIView):
            @pii_access_logged(record_type="User")
            def get(self, request, pk):
                ...

    The log entry is created even if the view raises an exception,
    ensuring the audit trail is complete.
    """

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(self_or_request, *args, **kwargs):
            # Support both function-based (request first) and class-based views
            if hasattr(self_or_request, "request"):
                # Class-based view: first arg is `self` (the view instance)
                request = self_or_request.request
            else:
                request = self_or_request

            record_id = kwargs.get(record_id_kwarg, "")
            store = getattr(request, "store", None)
            user = request.user if request.user.is_authenticated else None

            try:
                log_pii_access(
                    user=user,
                    store=store,
                    record_type=record_type,
                    record_id=record_id,
                    path=request.path,
                    method=request.method,
                )
            except Exception:
                # Never let audit logging break the actual view
                pass

            return view_func(self_or_request, *args, **kwargs)

        return wrapper

    return decorator


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


def _scrub_string(value):
    """Apply PII masking to a single string."""
    value = _PHONE_PATTERN.sub(_mask_phone, value)
    value = _EMAIL_PATTERN.sub(_mask_email, value)
    return value


def _scrub_value(value):
    """Recursively scrub PII from strings, dicts, and lists."""
    if isinstance(value, str):
        return _scrub_string(value)
    if isinstance(value, dict):
        return {k: _scrub_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub_value(item) for item in value]
    return value


def scrub_pii(logger, method_name, event_dict):
    """
    structlog processor that masks PII in log output.

    Handles nested dicts and lists in event_dict values.

    Phone numbers: +254712345678 -> ****5678
    Emails: user@example.com -> a3f2e1b4...@example.com
    """
    for key, value in event_dict.items():
        event_dict[key] = _scrub_value(value)
    return event_dict
