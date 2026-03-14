"""
Analytics async tasks.

Story 7.2: generate_daily_summary, send_merchant_weekly_digest (Beat schedule)
Story 8.1: Full DailyRevenueSummary + HourlyOrderSummary population (Epic 8)

Queue: analytics.reports
DLQ pattern: max_retries=5, countdown=60 * (2 ** retries)
"""

import structlog
from celery import shared_task
from django.utils import timezone

from core.tasks import DLQTask

logger = structlog.get_logger(__name__)


@shared_task(
    bind=True,
    base=DLQTask,
    queue="analytics.reports",
    max_retries=5,
)
def generate_daily_summary(self, target_date_str: str = None) -> None:
    """
    Story 7.2 / Story 8.1 — Generate DailyRevenueSummary + HourlyOrderSummary
    for all active stores for the previous calendar day.

    Scheduled: daily at 00:05 via Celery Beat.
    Also callable manually for backfills: generate_daily_summary.delay("2026-03-13")

    Full aggregation logic implemented in Epic 8 (Story 8.1).
    """
    try:
        from datetime import date, timedelta

        if target_date_str:
            from datetime import datetime
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        else:
            target_date = (timezone.localdate() - timedelta(days=1))

        logger.info("generate_daily_summary_start", date=str(target_date))
        # TODO: Epic 8 — aggregate Order + MpesaTransaction data into
        # DailyRevenueSummary + HourlyOrderSummary for all active stores
        logger.info("generate_daily_summary_complete", date=str(target_date))

    except Exception as exc:
        logger.exception("generate_daily_summary_failed")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(
    bind=True,
    base=DLQTask,
    queue="analytics.reports",
    max_retries=3,
)
def send_merchant_weekly_digest(self) -> None:
    """
    Story 7.2 — Send weekly analytics digest to all store owners.

    Scheduled: Mondays at 08:00 via Celery Beat.
    Digest includes: weekly revenue, order count, top products.

    Full email implementation in Epic 12 (SendGrid integration).
    """
    try:
        logger.info("send_merchant_weekly_digest_start")
        # TODO: Epic 12 — query DailyRevenueSummary for past 7 days,
        # send summary email to each store owner
        logger.info("send_merchant_weekly_digest_complete")
    except Exception as exc:
        logger.exception("send_merchant_weekly_digest_failed")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
