"""Migration: add DineInOrder and KitchenTicket models (Story 3.6)."""

import django.core.validators
import django.db.models.deletion
import uuid
from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("restaurant", "0003_add_table_session"),
    ]

    operations = [
        # -----------------------------------------------------------------------
        # DineInOrder
        # -----------------------------------------------------------------------
        migrations.CreateModel(
            name="DineInOrder",
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
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="orders",
                        to="restaurant.tablesession",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("CONFIRMED", "Confirmed by kitchen"),
                            ("READY", "Ready for service"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        db_index=True,
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("items_snapshot", models.JSONField()),
                (
                    "total_amount",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                    ),
                ),
                ("placed_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-placed_at"],
                "abstract": False,
            },
        ),
        migrations.AddIndex(
            model_name="dineinorder",
            index=models.Index(
                fields=["store", "status"],
                name="idx_rst_dineinorder_store_status",
            ),
        ),
        migrations.AddIndex(
            model_name="dineinorder",
            index=models.Index(
                fields=["session"],
                name="idx_rst_dineinorder_session",
            ),
        ),
        # -----------------------------------------------------------------------
        # KitchenTicket
        # -----------------------------------------------------------------------
        migrations.CreateModel(
            name="KitchenTicket",
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
                    "order",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ticket",
                        to="restaurant.dineinorder",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("IN_PROGRESS", "In Progress"),
                            ("COMPLETED", "Completed"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        db_index=True,
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("items_snapshot", models.JSONField()),
                (
                    "waiter_name",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Denormalized waiter name from session.assigned_waiter at creation time.",
                        max_length=200,
                    ),
                ),
                (
                    "table_number",
                    models.PositiveSmallIntegerField(
                        help_text="Denormalized table number at creation time.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-created_at"],
                "abstract": False,
            },
        ),
        migrations.AddIndex(
            model_name="kitchenticket",
            index=models.Index(
                fields=["store", "status"],
                name="idx_rst_kitchenticket_store_status",
            ),
        ),
    ]
