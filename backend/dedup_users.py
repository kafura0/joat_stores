"""
Deduplicate users by email — keeps the oldest record per email.

Run during build to prevent MultipleObjectsReturned on login.
"""

import os
import sys


DJANGO_SETTINGS_MODULE = "config.settings.production"


if __name__ == "__main__":
    os.environ["DJANGO_SETTINGS_MODULE"] = DJANGO_SETTINGS_MODULE

    import django
    django.setup()

    from django.db import connection

    with connection.cursor() as cursor:
        # Find duplicate emails
        cursor.execute("""
            SELECT email, COUNT(*) as cnt
            FROM users_user
            WHERE email IS NOT NULL AND email != ''
            GROUP BY email
            HAVING COUNT(*) > 1
        """)
        dupes = cursor.fetchall()

        if not dupes:
            print("[dedup] No duplicate emails found")
            sys.exit(0)

        for email, count in dupes:
            print(f"[dedup] Found {count} users with email={email}")

            # Keep the oldest (by pk/created_at), delete the rest
            cursor.execute("""
                DELETE FROM users_user
                WHERE id NOT IN (
                    SELECT MIN(id) FROM users_user
                    WHERE email = %s
                ) AND email = %s
            """, [email, email])
            deleted = cursor.rowcount
            print(f"[dedup] Deleted {deleted} duplicate(s), kept 1")

    print("[dedup] Done")
