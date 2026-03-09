"""
Analytics async tasks — queue: analytics.reports

DLQ pattern: max_retries=5, countdown=60 * (2 ** self.request.retries)
Full implementation in Epic 8.
"""

from celery import shared_task


@shared_task(bind=True, max_retries=5, queue="analytics.reports")
def generate_daily_summary(self, store_id: int, date_str: str) -> None:
    """Generate pre-aggregated DailyRevenueSummary. Epic 8 implements the full body."""
    try:
        # TODO: Epic 8 — aggregate orders for date, write DailyRevenueSummary record
        pass
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))
