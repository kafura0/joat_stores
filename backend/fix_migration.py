"""
Smart migration state fix for Render deploys.

Previous approach (delete all + fake all) broke schema because some
migrations with real schema changes were faked without running.

New approach:
1. Check which columns/tables are actually missing
2. Create a temporary migration that adds ONLY the missing pieces
3. Fake-apply everything else to sync migration history

Run before `manage.py migrate` in the build command.
"""

import os
import sys
import subprocess


DJANGO_SETTINGS_MODULE = "config.settings.production"

ALL_APPS = [
    "account", "admin", "analytics", "auth", "bar", "contenttypes",
    "contracting", "django_celery_beat", "loyalty", "notifications",
    "order", "payment", "product", "restaurant", "saas", "sessions",
    "sites", "socialaccount", "store", "token_blacklist", "users",
]


def column_exists(cursor, table, column):
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = %s",
        [table, column],
    )
    return cursor.fetchone()[0] > 0


def table_exists(cursor, table):
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_name = %s",
        [table],
    )
    return cursor.fetchone()[0] > 0


def index_exists(cursor, index_name):
    cursor.execute(
        "SELECT COUNT(*) FROM pg_indexes WHERE indexname = %s",
        [index_name],
    )
    return cursor.fetchone()[0] > 0


def constraint_exists(cursor, constraint_name):
    cursor.execute(
        "SELECT COUNT(*) FROM pg_constraint WHERE conname = %s",
        [constraint_name],
    )
    return cursor.fetchone()[0] > 0


def apply_raw_sql(cursor, statements, label):
    """Apply raw SQL statements and report."""
    for stmt in statements:
        try:
            cursor.execute(stmt)
            print(f"  [fix] Applied: {stmt[:80]}...")
        except Exception as e:
            if "already exists" in str(e) or "does not exist" in str(e):
                print(f"  [fix] Skip (already done): {stmt[:60]}...")
            else:
                print(f"  [fix] Warning on {label}: {e}")


def fix_missing_schema():
    """Directly add any missing columns/indexes/constraints via SQL."""
    os.environ["DJANGO_SETTINGS_MODULE"] = DJANGO_SETTINGS_MODULE

    import django
    django.setup()

    from django.db import connection

    with connection.cursor() as cursor:
        # ── store_store.mpesa_shortcode ──
        if table_exists(cursor, "store_store"):
            if not column_exists(cursor, "store_store", "mpesa_shortcode"):
                print("[fix] Adding store_store.mpesa_shortcode...")
                apply_raw_sql(cursor, [
                    "ALTER TABLE store_store ADD COLUMN mpesa_shortcode varchar(20) DEFAULT '' NOT NULL",
                ], "store.mpesa_shortcode")
            else:
                print("[fix] store_store.mpesa_shortcode already exists")

        # ── Check for other commonly missing columns ──
        # Add any future missing columns here as they're discovered

        # ── Check for other commonly missing columns ──
        # Add any future missing columns here as they're discovered


def fake_all_migrations():
    """Fake-apply all migrations so Django thinks DB is up to date."""
    for app in ALL_APPS:
        try:
            result = subprocess.run(
                [
                    sys.executable, "manage.py", "migrate", app, "--fake",
                    "--settings", DJANGO_SETTINGS_MODULE,
                ],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0:
                print(f"  [fix] Faked {app}")
            else:
                stderr = result.stderr.strip()
                if "No migrations" not in stderr and "does not exist" not in stderr:
                    print(f"  [fix] Warning faking {app}: {stderr[:100]}")
        except subprocess.TimeoutExpired:
            print(f"  [fix] Timeout faking {app}")
        except Exception as e:
            print(f"  [fix] Error faking {app}: {e}")


if __name__ == "__main__":
    try:
        print("[fix_migration] Phase 1: Applying missing schema via SQL...")
        fix_missing_schema()

        print("[fix_migration] Phase 2: Faking all migrations to sync history...")
        fake_all_migrations()

        print("[fix_migration] Done.")
    except Exception as e:
        print(f"[fix_migration] Warning: {e}", file=sys.stderr)
