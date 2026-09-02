"""
One-time migration state fix for Render deploys.

If analytics.0002 was marked as applied but the tables were never created
(interrupted deploy), this script unapplies 0002 and 0003 so migrate can
recreate them from scratch.

Run before `manage.py migrate` in the build command.
"""

import os
import sys

import django


def fix_analytics_migrations():
    """Check if analytics tables exist; if not, unapply broken migrations."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
    django.setup()

    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'analytics_aievent'"
        )
        table_exists = cursor.fetchone() is not None

    if table_exists:
        print("[fix_migration] analytics_aievent table exists — no fix needed")
        return

    print("[fix_migration] analytics_aievent table missing — unapplying broken migrations")

    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM django_migrations WHERE app = 'analytics' AND name IN "
            "('0002_analytics_summaries', '0003_rename_idx_analytics_aievent_store_type_an_aievent_store_type_and_more')"
        )
        deleted = cursor.rowcount
        print(f"[fix_migration] Removed {deleted} broken migration entries")


if __name__ == "__main__":
    try:
        fix_analytics_migrations()
    except Exception as e:
        print(f"[fix_migration] Warning: {e}", file=sys.stderr)
        # Don't fail the build — migrate will handle the error
