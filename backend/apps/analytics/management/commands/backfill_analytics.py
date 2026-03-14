"""
./manage.py backfill_analytics --days=30

Story 8.1 — Backfill DailyRevenueSummary + HourlyOrderSummary for all active stores.

Idempotent: uses update_or_create so running twice for the same date range
does not create duplicate records.

Usage:
  ./manage.py backfill_analytics             # last 30 days
  ./manage.py backfill_analytics --days=7    # last 7 days
  ./manage.py backfill_analytics --days=90   # last 90 days
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Backfill DailyRevenueSummary + HourlyOrderSummary for the past N days."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Number of days to backfill (default: 30).",
        )

    def handle(self, *args, **options):
        from apps.analytics.tasks import _run_daily_summary

        days = options["days"]
        today = timezone.localdate()

        self.stdout.write(f"Backfilling analytics for past {days} days...")

        for i in range(days, 0, -1):
            target_date = today - timedelta(days=i)
            try:
                _run_daily_summary(target_date)
                self.stdout.write(f"  ✓ {target_date}")
            except Exception as exc:
                self.stderr.write(f"  ✗ {target_date}: {exc}")

        self.stdout.write(self.style.SUCCESS(f"Backfill complete. {days} days processed."))
