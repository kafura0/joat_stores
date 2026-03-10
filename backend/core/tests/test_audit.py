"""
Tests for Story 1.6: PII audit logging + structlog PII scrubber.
"""

from django.test import TestCase

import pytest

from apps.analytics.models import AdminPIIAccessLog
from apps.store.models import Store
from apps.users.models import User
from core.audit import _mask_email, _mask_phone, log_pii_access, scrub_pii


class TestPIIScrubber(TestCase):
    """Test structlog PII scrubber processor (no DB needed)."""

    def test_mask_phone_kenyan_format(self):
        from core.audit import _PHONE_PATTERN

        result = _PHONE_PATTERN.sub(_mask_phone, "Call +254712345678")
        assert result == "Call ****5678"

    def test_mask_phone_local_format(self):
        from core.audit import _PHONE_PATTERN

        result = _PHONE_PATTERN.sub(_mask_phone, "Call 0712345678")
        assert result == "Call ****5678"

    def test_mask_email(self):
        from core.audit import _EMAIL_PATTERN

        result = _EMAIL_PATTERN.sub(_mask_email, "user@example.com")
        assert "@example.com" in result
        assert "user" not in result
        assert "..." in result

    def test_scrub_pii_processor(self):
        event_dict = {
            "event": "User login",
            "email": "john@example.com",
            "phone": "+254712345678",
        }
        result = scrub_pii(None, None, event_dict)
        assert "john" not in result["email"]
        assert "@example.com" in result["email"]
        assert "****5678" in result["phone"]

    def test_scrub_pii_ignores_non_string(self):
        event_dict = {"count": 42, "active": True}
        result = scrub_pii(None, None, event_dict)
        assert result["count"] == 42
        assert result["active"] is True


@pytest.mark.django_db
class TestAdminPIIAccessLog(TestCase):
    """Test PII audit log model."""

    def test_log_pii_access_creates_record(self):
        store = Store.objects.create(
            name="Audit Store",
            slug="audit-store",
            domain="audit.joat.com",
        )
        admin = User.objects.create_user(
            email="admin@joat.com",
            password="pass",
            role="platform_admin",
        )
        log_pii_access(
            user=admin,
            store=store,
            record_type="User",
            record_id="some-uuid",
            path="/api/v1/users/some-uuid/",
            method="GET",
        )
        assert AdminPIIAccessLog.objects.count() == 1
        entry = AdminPIIAccessLog.objects.first()
        assert entry.user == admin
        assert entry.store == store
        assert entry.record_type == "User"
        assert entry.record_id == "some-uuid"
        assert entry.path == "/api/v1/users/some-uuid/"

    def test_log_pii_access_without_store(self):
        admin = User.objects.create_user(
            email="admin2@joat.com",
            password="pass",
            role="platform_admin",
        )
        log_pii_access(
            user=admin,
            store=None,
            record_type="User",
            record_id="uuid-123",
        )
        assert AdminPIIAccessLog.objects.count() == 1
