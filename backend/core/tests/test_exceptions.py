"""
Tests for Story 1.6: custom_exception_handler.

Tests the normalised error envelope: {errors: [{field, message, code}]}.
"""

from django.test import TestCase

from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)

from core.exceptions import custom_exception_handler


class TestCustomExceptionHandler(TestCase):
    """Test error normalisation to {errors: [...]} envelope."""

    def _handle(self, exc):
        return custom_exception_handler(exc, context={})

    def test_field_validation_error(self):
        exc = ValidationError({"email": ["This field is required."]})
        resp = self._handle(exc)
        assert resp.status_code == 400
        errors = resp.data["errors"]
        assert len(errors) == 1
        assert errors[0]["field"] == "email"
        assert "required" in errors[0]["message"].lower()

    def test_non_field_validation_error(self):
        exc = ValidationError({"non_field_errors": ["Passwords do not match."]})
        resp = self._handle(exc)
        errors = resp.data["errors"]
        assert errors[0]["field"] is None

    def test_list_validation_error(self):
        exc = ValidationError(["Something went wrong."])
        resp = self._handle(exc)
        errors = resp.data["errors"]
        assert len(errors) == 1
        assert errors[0]["field"] is None

    def test_not_authenticated(self):
        exc = NotAuthenticated()
        resp = self._handle(exc)
        assert resp.status_code == 401
        errors = resp.data["errors"]
        assert errors[0]["code"] == "NOT_AUTHENTICATED"

    def test_authentication_failed(self):
        exc = AuthenticationFailed("Token expired.")
        resp = self._handle(exc)
        assert resp.status_code == 401
        errors = resp.data["errors"]
        assert errors[0]["code"] == "AUTHENTICATION_FAILED"

    def test_permission_denied(self):
        exc = PermissionDenied("Store owner access required.")
        resp = self._handle(exc)
        assert resp.status_code == 403
        errors = resp.data["errors"]
        assert errors[0]["code"] == "PERMISSION_DENIED"

    def test_throttled(self):
        exc = Throttled(wait=30)
        resp = self._handle(exc)
        assert resp.status_code == 429
        errors = resp.data["errors"]
        assert errors[0]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "30" in errors[0]["message"]

    def test_not_found(self):
        exc = NotFound("Store not found.")
        resp = self._handle(exc)
        assert resp.status_code == 404
        assert "errors" in resp.data

    def test_multiple_field_errors(self):
        exc = ValidationError(
            {
                "email": ["Required."],
                "name": ["Too short.", "Invalid chars."],
            }
        )
        resp = self._handle(exc)
        errors = resp.data["errors"]
        assert len(errors) == 3

    def test_dict_in_validation_error(self):
        """Test nested dict format from StoreStatusSerializer."""
        exc = ValidationError(
            {
                "status": {
                    "message": "Invalid transition.",
                    "code": "INVALID_STATUS_TRANSITION",
                }
            }
        )
        resp = self._handle(exc)
        errors = resp.data["errors"]
        assert errors[0]["field"] == "status"
        assert errors[0]["code"] == "INVALID_STATUS_TRANSITION"
