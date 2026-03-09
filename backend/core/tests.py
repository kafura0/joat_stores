"""
Smoke tests for the core module.

These tests verify the project scaffold is wired correctly and Django
settings are importable.  They intentionally avoid DB access so they
pass in every environment (local, CI, Docker).
"""

from django.conf import settings


class TestProjectScaffold:
    """Verify the monorepo scaffold is correctly configured."""

    def test_secret_key_is_set(self):
        """SECRET_KEY must be non-empty."""
        assert settings.SECRET_KEY, "SECRET_KEY must not be empty"

    def test_installed_apps_includes_core_apps(self):
        """All custom apps must be present in INSTALLED_APPS."""
        installed = settings.INSTALLED_APPS
        required_apps = [
            "apps.store",
            "apps.users",
            "apps.order",
            "apps.product",
            "apps.payment",
            "apps.inventory",
            "apps.restaurant",
            "apps.bar",
            "apps.contracting",
            "apps.loyalty",
            "apps.notifications",
            "apps.saas",
            "apps.analytics",
            "apps.ai",
        ]
        for app in required_apps:
            assert app in installed, f"Expected '{app}' in INSTALLED_APPS"

    def test_celery_queues_configured(self):
        """All 5 named Celery queues must be declared."""
        from django.conf import settings as s

        queue_names = {q.name for q in s.CELERY_TASK_QUEUES}
        expected = {
            "order.notifications",
            "inventory.alerts",
            "billing.reminders",
            "payments.reconciliation",
            "analytics.reports",
        }
        assert (
            expected == queue_names
        ), f"Celery queue mismatch. Expected: {expected}, Got: {queue_names}"

    def test_database_setting_present(self):
        """DATABASES['default'] must be configured."""
        assert "default" in settings.DATABASES
        assert settings.DATABASES["default"]["ENGINE"]
