"""
One-time migration state fix for Render deploys.

If analytics.0002 was marked as applied but analytics_aievent table was never
created (interrupted deploy), this script:
1. Drops any partially-created analytics tables
2. Unapplies the broken migration entries
So migrate can recreate everything from scratch.

Run before `manage.py migrate` in the build command.
"""

import os
import sys

import django


ANALYTICS_TABLES = [
    "analytics_dailyrevenuesummary",
    "analytics_hourlyordersummary",
    "analytics_aievent",
    "analytics_tenanthealthsnapshot",
    "analytics_storefirstorderevent",
    "analytics_adminpiiaccesslog",
]


def fix_analytics_migrations():
    """Check if analytics_aievent table exists; if not, clean up and unapply."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
    django.setup()

    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'analytics_aievent'"
        )
        aievent_exists = cursor.fetchone() is not None

    if aievent_exists:
        print("[fix_migration] analytics_aievent exists — no fix needed")
        return

    print("[fix_migration] analytics_aievent missing — cleaning up partial state")

    from django.db import connection

    with connection.cursor() as cursor:
        # Drop any partially-created analytics tables (foreign keys may block drop)
        for table in ANALYTICS_TABLES:
            cursor.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
                [table],
            )
            if cursor.fetchone():
                # Drop with CASCADE to handle foreign key dependencies
                cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
                print(f"[fix_migration] Dropped partial table: {table}")

        # Unapply migration entries so migrate recreates everything
        cursor.execute(
            "DELETE FROM django_migrations WHERE app = 'analytics' AND name IN "
            "('0002_analytics_summaries', '0003_rename_idx_analytics_aievent_store_type_an_aievent_store_type_and_more')"
        )
        deleted = cursor.rowcount
        print(f"[fix_migration] Removed {deleted} migration entries — migrate will recreate all analytics tables")


if __name__ == "__main__":
    try:
        fix_analytics_migrations()
    except Exception as e:
        print(f"[fix_migration] Warning: {e}", file=sys.stderr)
        # Don't fail the build — migrate will handle the error
