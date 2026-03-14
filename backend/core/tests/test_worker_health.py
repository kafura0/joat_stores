"""
Tests for Story 7.3 — Worker Health Endpoint.

GET /health/workers/ — no auth, returns queue depths + worker heartbeats.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory, TestCase

from core.worker_health import WorkerHealthView


class TestWorkerHealthView(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = WorkerHealthView.as_view()

    def _get(self):
        request = self.factory.get("/health/workers/")
        return self.view(request)

    @patch("core.worker_health._get_worker_heartbeats")
    @patch("core.worker_health._get_queue_depth")
    def test_all_healthy_returns_200(self, mock_depth, mock_heartbeats):
        mock_depth.return_value = 0
        mock_heartbeats.return_value = {
            "celery@worker1": {"last_heartbeat": "2026-03-14T00:00:00+00:00", "status": "healthy"}
        }
        with patch("celery.current_app") as mock_app:
            mock_app.backend.client = MagicMock()
            resp = self._get()
        assert resp.status_code == 200
        import json
        data = json.loads(resp.content)
        assert data["status"] == "healthy"
        assert len(data["queues"]) == 5

    @patch("core.worker_health._get_worker_heartbeats")
    @patch("core.worker_health._get_queue_depth")
    def test_degraded_worker_returns_503(self, mock_depth, mock_heartbeats):
        mock_depth.return_value = 0
        mock_heartbeats.return_value = {
            "celery@worker1": {"last_heartbeat": "2026-03-13T00:00:00+00:00", "status": "degraded"}
        }
        with patch("celery.current_app") as mock_app:
            mock_app.backend.client = MagicMock()
            resp = self._get()
        assert resp.status_code == 503

    @patch("core.worker_health._get_worker_heartbeats")
    def test_no_workers_returns_503(self, mock_heartbeats):
        mock_heartbeats.return_value = {}
        with patch("celery.current_app") as mock_app:
            mock_app.backend.client = None
            resp = self._get()
        assert resp.status_code == 503

    def test_health_workers_no_auth_required(self):
        """Endpoint must be accessible without authentication."""
        # This test just verifies no auth middleware blocks the view
        request = self.factory.get("/health/workers/")
        # No credentials set — should not raise 401/403
        with patch("core.worker_health._get_worker_heartbeats", return_value={}):
            with patch("celery.current_app") as mock_app:
                mock_app.backend.client = None
                resp = self.view(request)
        assert resp.status_code in (200, 503)

    def test_queue_list_includes_all_five_queues(self):
        import json
        with patch("core.worker_health._get_worker_heartbeats", return_value={}):
            with patch("celery.current_app") as mock_app:
                mock_app.backend.client = None
                resp = self._get()
        data = json.loads(resp.content)
        queue_names = [q["queue_name"] for q in data["queues"]]
        assert "order.notifications" in queue_names
        assert "inventory.alerts" in queue_names
        assert "billing.reminders" in queue_names
        assert "payments.reconciliation" in queue_names
        assert "analytics.reports" in queue_names
