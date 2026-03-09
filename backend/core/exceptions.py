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
  - PermissionDenied → 403
  - NotAuthenticated → 401
  - Http404 → 404
  - Unhandled exceptions → 500 (Sentry captures these)

Implementation: Story 1.6
"""
# TODO: Story 1.6 — implement custom_exception_handler


def custom_exception_handler(exc, context):
    """Placeholder. Story 1.6 implements the full normalised error envelope."""
    from rest_framework.views import exception_handler
    return exception_handler(exc, context)
