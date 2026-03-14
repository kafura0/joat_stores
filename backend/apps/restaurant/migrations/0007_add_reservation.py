"""Migration: add Reservation model (Story 3.9)."""

import django.db.models.deletion
import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("restaurant", "0006_add_payment_link"),
    ]

    operations = [
        migrations.CreateModel(
            name="Reservation",
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
                ("customer_phone", models.CharField(max_length=20)),
                ("customer_name", models.CharField(blank=True, default="", max_length=200)),
                (
                    "table",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reservations",
                        to="restaurant.table",
                    ),
                ),
                ("party_size", models.PositiveSmallIntegerField()),
                ("reserved_for", models.DateTimeField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("CONFIRMED", "Confirmed"),
                            ("SEATED", "Seated"),
                            ("NO_SHOW", "No Show"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        db_index=True,
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("notes", models.TextField(blank=True, default="")),
                (
                    "session",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reservation",
                        to="restaurant.tablesession",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["reserved_for"],
                "abstract": False,
            },
        ),
        migrations.AddIndex(
            model_name="reservation",
            index=models.Index(
                fields=["store", "status"],
                name="idx_rst_reservation_store_status",
            ),
        ),
        migrations.AddIndex(
            model_name="reservation",
            index=models.Index(
                fields=["store", "reserved_for"],
                name="idx_rst_reservation_store_time",
            ),
        ),
    ]
