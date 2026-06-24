"""
FCMDevice model — push notification device registration.

SafeDeleteModel columns (deleted, deleted_by_cascade) and UUID PK changes
are omitted — they were already applied via raw SQL or are pre-existing
DB state that doesn't match the auto-generated migration.
Only FCMDevice creation is a real DB operation.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0001_notifications_initial"),
        ("users", "0003_platform_user_model"),
    ]

    operations = [
        migrations.CreateModel(
            name="FCMDevice",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "registration_id",
                    models.TextField(help_text="FCM device token from the mobile app."),
                ),
                (
                    "platform",
                    models.CharField(
                        choices=[
                            ("android", "Android"),
                            ("ios", "iOS"),
                            ("web", "Web"),
                        ],
                        default="android",
                        max_length=10,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "FCM Device",
                "verbose_name_plural": "FCM Devices",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="fcmdevice",
            name="platform_user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="fcm_devices",
                to="users.platformuser",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="fcmdevice",
            unique_together={("platform_user", "registration_id")},
        ),
    ]
