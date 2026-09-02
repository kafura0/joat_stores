"""
Migration state fix for Render deploys.

Checks each Django app's tables against what migrations claim as applied.
If an app's tables are completely missing but migrations are marked applied,
deletes those entries so migrate recreates everything from scratch.

Run before `manage.py migrate` in the build command.
"""

import os
import sys

import django

# Map each app to its key tables (first table that should exist after 0001)
APP_TABLES = {
    "analytics": ["analytics_dailyrevenuesummary"],
    "bar": ["bar_tab"],
    "contracting": ["contracting_job"],
    "restaurant": ["restaurant_menusection"],
    "loyalty": ["loyalty_program"],
    "notifications": ["notificationpreference"],
    "saas": ["plan"],
    "order": ["orderticket"],
    "payment": ["paymentmethod"],
    "product": ["product"],
    "store": ["store_store"],
    "users": ["users_user"],
}


def fix_migration_state():
    """Check each app's tables; delete migration entries for apps with missing tables."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
    django.setup()

    from django.db import connection

    with connection.cursor() as cursor:
        # Get all tables that exist
        cursor.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        existing_tables = {row[0] for row in cursor.fetchall()}

        apps_to_reset = []

        for app, tables in APP_TABLES.items():
            key_table = tables[0]
            if key_table not in existing_tables:
                # Table missing — check if migrations claim it exists
                cursor.execute(
                    "SELECT COUNT(*) FROM django_migrations WHERE app = %s",
                    [app],
                )
                migration_count = cursor.fetchone()[0]
                if migration_count > 0:
                    apps_to_reset.append((app, migration_count))

        if not apps_to_reset:
            print("[fix_migration] All apps have their tables — no fix needed")
            return

        # Delete migration entries for broken apps so migrate recreates them
        for app, count in apps_to_reset:
            cursor.execute("DELETE FROM django_migrations WHERE app = %s", [app])
            print(f"[fix_migration] Removed {count} migration entries for '{app}'")

        print(f"[fix_migration] Reset {len(apps_to_reset)} apps — migrate will recreate tables")


if __name__ == "__main__":
    try:
        fix_migration_state()
    except Exception as e:
        print(f"[fix_migration] Warning: {e}", file=sys.stderr)
        # Don't fail the build — migrate will handle the error
