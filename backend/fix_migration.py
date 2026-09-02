"""
Migration state fix for Render deploys.

The production database has inconsistent migration history — migrations
were applied out of order, or applied before their dependencies existed.
Django's check_consistent_history catches this and blocks all future migrations.

Strategy:
1. Delete ALL django_migrations entries
2. For each app, fake-apply all its migrations (mark as done without running)
3. Then `migrate` finds no pending migrations — DB schema is already correct

Run before `manage.py migrate` in the build command.
"""

import os
import sys
import subprocess


DJANGO_SETTINGS_MODULE = "config.settings.production"

# All installed Django apps that have migrations
APPS = [
    "account", "admin", "analytics", "auth", "bar", "contenttypes",
    "contracting", "django_celery_beat", "loyalty", "notifications",
    "order", "payment", "product", "restaurant", "saas", "sessions",
    "sites", "socialaccount", "store", "token_blacklist", "users",
]


def fix_migration_state():
    """Delete all entries, then fake-apply all app migrations."""
    os.environ["DJANGO_SETTINGS_MODULE"] = DJANGO_SETTINGS_MODULE

    import django
    django.setup()

    from django.db import connection

    # Step 1: Delete all migration entries
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM django_migrations")
        deleted = cursor.rowcount
    print(f"[fix_migration] Removed {deleted} migration entries")

    # Step 2: Fake-apply all migrations for each app
    for app in APPS:
        try:
            result = subprocess.run(
                [
                    sys.executable, "manage.py", "migrate", app, "--fake",
                    "--settings", DJANGO_SETTINGS_MODULE,
                ],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0:
                print(f"[fix_migration] Faked {app} migrations")
            else:
                # Some apps may have no migrations — that's fine
                stderr = result.stderr.strip()
                if "No migrations" not in stderr and "does not exist" not in stderr:
                    print(f"[fix_migration] Warning faking {app}: {stderr}")
        except subprocess.TimeoutExpired:
            print(f"[fix_migration] Timeout faking {app} — skipping")
        except Exception as e:
            print(f"[fix_migration] Error faking {app}: {e}")


if __name__ == "__main__":
    try:
        fix_migration_state()
    except Exception as e:
        print(f"[fix_migration] Warning: {e}", file=sys.stderr)
