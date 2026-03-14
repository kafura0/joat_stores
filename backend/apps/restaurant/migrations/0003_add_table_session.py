"""Migration: add TableSession model (Story 3.4)."""

import django.db.models.deletion
import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("restaurant", "0002_add_table"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TableSession",
            fields=[
                (
                    "deleted",
                    models.DateTimeField(db_index=True, editable=False, null=True),
                ),
                (
                    "deleted_by_cascade",
                    models.BooleanField(default=False, editable=False),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "store",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="store.store",
                    ),
                ),
                (
                    "table",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sessions",
                        to="restaurant.table",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("OPEN", "Open"),
                            ("BILL_REQUESTED", "Bill Requested"),
                            ("CLOSED", "Closed"),
                        ],
                        db_index=True,
                        default="OPEN",
                        max_length=20,
                    ),
                ),
                (
                    "assigned_waiter",
                    models.ForeignKey(
                        blank=True,
                        help_text="Waiter assigned to this session; name appears on kitchen tickets.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("opened_at", models.DateTimeField(auto_now_add=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "ordering": ["-opened_at"],
                "abstract": False,
            },
        ),
        migrations.AddConstraint(
            model_name="tablesession",
            constraint=models.UniqueConstraint(
                condition=models.Q(status="OPEN"),
                fields=["table"],
                name="uq_restaurant_tablesession_one_open_per_table",
            ),
        ),
        migrations.AddIndex(
            model_name="tablesession",
            index=models.Index(
                fields=["store", "status"],
                name="idx_rst_tablesession_store_status",
            ),
        ),
        migrations.AddIndex(
            model_name="tablesession",
            index=models.Index(
                fields=["table", "status"],
                name="idx_rst_tablesession_table_status",
            ),
        ),
    ]
