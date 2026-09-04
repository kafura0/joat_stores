"""
Core Celery base task utilities.

Story 7.1 — DLQ + Exponential Backoff Hardening.

All tasks across all queues MUST use DLQTask as their base class or apply
the retry_with_backoff decorator. This ensures:
  - Exponential backoff: countdown = 60 * (2 ** retries)
  - Max 5 retries
  - On final failure: route to DLQ + capture Sentry event

Task dispatch pattern (REQUIRED — never call .delay() inside a DB transaction):
  from django.db import transaction
  transaction.on_commit(lambda: my_task.delay(arg))
"""

import logging

import structlog
from celery import Task, shared_task
from celery.exceptions import MaxRetriesExceededError

logger = structlog.get_logger(__name__)


class DLQTask(Task):
    """
    Base Celery task class with:
      - Exponential backoff: countdown = 60 * (2 ** self.request.retries)
      - max_retries = 5
      - On final failure: Sentry capture + DLQ routing

    Usage:
        @shared_task(bind=True, base=DLQTask, queue="order.notifications")
        def my_task(self, arg):
            ...
    """

    max_retries = 5
    # acks_late ensures the task is not removed from the queue until it completes
    acks_late = True

    def retry(self, args=None, kwargs=None, exc=None, throw=True, eta=None, countdown=None, **options):
        """Override retry to enforce exponential backoff."""
        retries = self.request.retries
        if countdown is None:
            countdown = 60 * (2 ** retries)
        return super().retry(
            args=args, kwargs=kwargs, exc=exc, throw=throw,
            countdown=countdown, **options
        )

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Route to DLQ and capture Sentry on final failure."""
        try:
            import sentry_sdk
            sentry_sdk.capture_exception(
                exc,
                extras={
                    "task_name": self.name,
                    "task_id": task_id,
                    "queue": self.queue,
                    "args": str(args)[:500],
                    "kwargs": str(kwargs)[:500],
                },
            )
        except Exception:
            pass  # never let Sentry crash the handler

        logger.error(
            "task_failed_max_retries",
            task_name=self.name,
            task_id=task_id,
            exc=str(exc),
        )

        # Publish to DLQ for manual investigation
        try:
            _publish_to_dlq(self.name, task_id, args, kwargs, str(exc))
        except Exception:
            pass


def _publish_to_dlq(task_name: str, task_id: str, args, kwargs, error: str) -> None:
    """
    Publish a failed task record to the dead-letter queue.

    DLQ is a Redis sorted set: key="celery:dlq", score=timestamp, value=JSON.
    This allows operators to inspect failed tasks via Redis CLI or Flower.
    """
    import json
    import time

    try:
        from django.core.cache import cache

        record = json.dumps(
            {
                "task_name": task_name,
                "task_id": task_id,
                "args": str(args)[:500],
                "kwargs": str(kwargs)[:500],
                "error": error,
                "failed_at": time.time(),
            }
        )
        # Use Redis directly for sorted set operations
        redis_client = cache.client.get_client()
        redis_client.zadd("celery:dlq", {record: time.time()})
        # Cap DLQ at 10,000 entries (ZREMRANGEBYRANK removes oldest)
        redis_client.zremrangebyrank("celery:dlq", 0, -10001)
    except Exception:
        pass  # DLQ publish failure is non-fatal


# ---------------------------------------------------------------------------
# System tasks
# ---------------------------------------------------------------------------


@shared_task(queue="analytics.reports")
def heartbeat():
    """Simple heartbeat task — runs every 5 min to verify Celery workers are alive."""
    import structlog
    logger = structlog.get_logger(__name__)
    logger.info("heartbeat_ok")
