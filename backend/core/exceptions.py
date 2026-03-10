"""
custom_exception_handler

DRF exception handler that normalises all error responses to:
  {
    "errors": [
      { "field": "email", "message": "This field is required.", "code": "required" }
    ]
  }

Handles:
  - ValidationError (field-level and non-field)
  - PermissionDenied -> 403
  - NotAuthenticated -> 401
  - Http404 -> 404
  - Throttled -> 429
  - Unhandled exceptions -> 500

Implementation: Story 1.6
"""

from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """Normalise all DRF errors to {errors: [{field, message, code}]}."""
    response = exception_handler(exc, context)

    if response is None:
        # Unhandled exception — let Django/Sentry handle 500
        return None

    errors = []

    if isinstance(exc, ValidationError):
        errors = _flatten_validation_errors(exc.detail)
    elif isinstance(exc, NotAuthenticated):
        errors = [
            {
                "field": None,
                "message": "Authentication credentials were not provided.",
                "code": "NOT_AUTHENTICATED",
            }
        ]
    elif isinstance(exc, AuthenticationFailed):
        errors = [
            {
                "field": None,
                "message": str(exc.detail),
                "code": "AUTHENTICATION_FAILED",
            }
        ]
    elif isinstance(exc, PermissionDenied):
        errors = [
            {
                "field": None,
                "message": str(exc.detail),
                "code": "PERMISSION_DENIED",
            }
        ]
    elif isinstance(exc, Throttled):
        wait = exc.wait
        errors = [
            {
                "field": None,
                "message": (
                    f"Rate limit exceeded. Retry after {wait:.0f}s."
                    if wait
                    else "Rate limit exceeded."
                ),
                "code": "RATE_LIMIT_EXCEEDED",
            }
        ]
    else:
        # Generic DRF error (404, 405, etc.)
        detail = exc.detail if hasattr(exc, "detail") else str(exc)
        code = getattr(exc, "default_code", "ERROR")
        errors = [
            {
                "field": None,
                "message": str(detail),
                "code": str(code).upper(),
            }
        ]

    response.data = {"errors": errors}
    return response


def _flatten_validation_errors(detail):
    """Flatten DRF ValidationError detail into [{field, message, code}]."""
    errors = []

    if isinstance(detail, list):
        for item in detail:
            if isinstance(item, dict):
                # Nested dict in list (e.g. {"message": ..., "code": ...})
                errors.append(
                    {
                        "field": None,
                        "message": item.get("message", str(item)),
                        "code": item.get("code", "VALIDATION_ERROR"),
                    }
                )
            else:
                errors.append(
                    {
                        "field": None,
                        "message": str(item),
                        "code": getattr(item, "code", "VALIDATION_ERROR"),
                    }
                )
    elif isinstance(detail, dict):
        for field, messages in detail.items():
            if field == "non_field_errors":
                field_name = None
            else:
                field_name = field
            if isinstance(messages, list):
                for msg in messages:
                    errors.append(
                        {
                            "field": field_name,
                            "message": str(msg),
                            "code": getattr(msg, "code", "VALIDATION_ERROR"),
                        }
                    )
            elif isinstance(messages, dict):
                # Nested dict (e.g. {"message": ..., "code": ...})
                errors.append(
                    {
                        "field": field_name,
                        "message": messages.get("message", str(messages)),
                        "code": messages.get("code", "VALIDATION_ERROR"),
                    }
                )
            else:
                errors.append(
                    {
                        "field": field_name,
                        "message": str(messages),
                        "code": getattr(messages, "code", "VALIDATION_ERROR"),
                    }
                )
    else:
        errors.append(
            {
                "field": None,
                "message": str(detail),
                "code": "VALIDATION_ERROR",
            }
        )

    return errors
