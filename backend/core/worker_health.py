"""
Story 7.3 — Worker Health Endpoint.

GET /health/workers/

Returns per-queue depth and last worker heartbeat.
HTTP 200 = all workers healthy.
HTTP 503 = any worker heartbeat > 60s old (degraded).

No authentication required — used by infra monitoring (Uptime Robot, etc).
"""

import time
from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.http import JsonResponse
from django.views import View


QUEUE_NAMES = [
    "order.notifications",
    "inventory.alerts",
    "billing.reminders",
    "payments.reconciliation",
    "analytics.reports",
]

HEARTBEAT_TIMEOUT_SECONDS = getattr(settings, "CELERY_WORKER_HEARTBEAT_TIMEOUT", 60)


def _get_queue_depth(redis_client, queue_name: str) -> int:
    """Return pending message count for a RabbitMQ/Redis queue."""
    try:
        # For Redis broker: queue is stored as a list under the queue name
        depth = redis_client.llen(queue_name)
        return int(depth) if depth is not None else 0
    except Exception:
        return -1  # unknown


def _get_worker_heartbeats(app) -> dict[str, dict]:
    """
    Return per-worker heartbeat info from Celery's inspect API.

    Returns: {worker_name: {"last_heartbeat": iso_str, "status": "healthy"|"degraded"}}
    """
    results = {}
    try:
        inspect = app.control.inspect(timeout=2.0)
        stats = inspect.stats()
        if not stats:
            return {}

        now = time.time()
        for worker_name, worker_stats in stats.items():
            heartbeat_ts = worker_stats.get("clock", None)
            if heartbeat_ts is None:
                results[worker_name] = {"last_heartbeat": None, "status": "unknown"}
                continue

            try:
                age = now - float(heartbeat_ts)
                status = "degraded" if age > HEARTBEAT_TIMEOUT_SECONDS else "healthy"
                last_hb = datetime.fromtimestamp(float(heartbeat_ts), tz=dt_timezone.utc).isoformat()
            except Exception:
                status = "unknown"
                last_hb = None

            results[worker_name] = {"last_heartbeat": last_hb, "status": status}

    except Exception:
        pass

    return results


class WorkerHealthView(View):
    """
    GET /health/workers/

    Returns queue depths + worker heartbeats.
    No auth required.
    """

    def get(self, request):
        from celery import current_app

        queues = []
        is_degraded = False

        try:
            redis_client = current_app.backend.client if hasattr(current_app.backend, "client") else None

            for queue_name in QUEUE_NAMES:
                depth = _get_queue_depth(redis_client, queue_name) if redis_client else -1
                queues.append({"queue_name": queue_name, "depth": depth})

        except Exception:
            for queue_name in QUEUE_NAMES:
                queues.append({"queue_name": queue_name, "depth": -1})

        # Worker heartbeats
        worker_heartbeats = _get_worker_heartbeats(current_app)
        workers = []
        for worker_name, info in worker_heartbeats.items():
            if info.get("status") == "degraded":
                is_degraded = True
            workers.append({"worker": worker_name, **info})

        # If no workers at all, that's degraded
        if not workers:
            is_degraded = True

        status_code = 503 if is_degraded else 200
        return JsonResponse(
            {
                "status": "degraded" if is_degraded else "healthy",
                "queues": queues,
                "workers": workers,
            },
            status=status_code,
        )
