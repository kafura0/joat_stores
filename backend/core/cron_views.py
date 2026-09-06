"""
Internal cron endpoint — triggered by Upstash QStash.

QStash sends a signed request to this endpoint on schedule.
The endpoint dispatches Celery tasks without needing Celery Beat.

Setup (free tier):
  1. Set CRON_SECRET env var in Render (random 32+ char string)
  2. Create QStash schedules in Upstash Console:
     - POST /api/v1/internal/run-cron/ with body {"task": "heartbeat", "secret": "..."}
       Schedule: every 5 minutes
     - POST /api/v1/internal/run-cron/ with body {"task": "warm_branding_cache", "secret": "..."}
       Schedule: every hour
     - POST /api/v1/internal/run-cron/ with body {"task": "check_low_stock", "secret": "..."}
       Schedule: every hour
"""

import json
import os

import structlog
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = structlog.get_logger(__name__)

# Allowed tasks — whitelist to prevent abuse
ALLOWED_TASKS = {
    "heartbeat": "core.tasks.heartbeat",
    "warm_branding_cache": "apps.store.tasks.warm_branding_cache",
    "check_low_stock": "apps.inventory.tasks.check_low_stock",
}


@csrf_exempt
@require_POST
def run_cron(request):
    """
    Internal cron trigger — called by Upstash QStash.

    Request body: {
      "task": "heartbeat" | "warm_branding_cache" | "check_low_stock",
      "secret": "YOUR_CRON_SECRET"
    }
    """
    # Parse body
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "invalid JSON"}, status=400)

    # Verify secret
    cron_secret = os.environ.get("CRON_SECRET")
    if cron_secret and body.get("secret") != cron_secret:
        logger.warning("cron_invalid_secret")
        return JsonResponse({"error": "unauthorized"}, status=403)

    # Get task name
    task_name = body.get("task")
    if not task_name:
        return JsonResponse({"error": "missing 'task' field"}, status=400)

    if task_name not in ALLOWED_TASKS:
        logger.warning("cron_unknown_task", task=task_name)
        return JsonResponse({"error": f"unknown task: {task_name}"}, status=400)

    # Dispatch task
    from celery import Celery

    app = Celery("joat_stores")
    app.config_from_object("django.conf:settings", namespace="CELERY")

    task_path = ALLOWED_TASKS[task_name]
    logger.info("cron_dispatching", task=task_name, path=task_path)

    app.send_task(task_path)

    return JsonResponse({"status": "dispatched", "task": task_name})
