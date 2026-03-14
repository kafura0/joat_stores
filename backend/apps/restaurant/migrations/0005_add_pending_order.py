"""Migration: add PendingOrder model (Story 3.7)."""

import django.core.validators
import django.db.models.deletion
import uuid
from decimal import Decimal

from django.db import migrations, models

import apps.restaurant.models


class Migration(migrations.Migration):

    dependencies = [
        ("restaurant", "0004_add_dineinorder_kitchenticket"),
    ]

    operations = [
        migrations.CreateModel(
            name="PendingOrder",
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
                ("phone", models.CharField(max_length=20)),
                (
                    "pin",
                    models.CharField(
                        default=apps.restaurant.models._generate_pin,
                        max_length=6,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("PAID", "Paid in advance"),
                            ("CONVERTED", "Converted to dine-in"),
                            ("EXPIRED", "Expired"),
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
                ("expires_at", models.DateTimeField()),
                (
                    "converted_order",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="pending_order",
                        to="restaurant.dineinorder",
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
            model_name="pendingorder",
            index=models.Index(
                fields=["store", "status"],
                name="idx_rst_pendingorder_store_status",
            ),
        ),
        migrations.AddIndex(
            model_name="pendingorder",
            index=models.Index(
                fields=["store", "pin", "status"],
                name="idx_rst_pendingorder_store_pin_status",
            ),
        ),
        migrations.AddIndex(
            model_name="pendingorder",
            index=models.Index(
                fields=["store", "phone", "status"],
                name="idx_rst_pendingorder_store_phone_status",
            ),
        ),
    ]
