"""Add CardTransaction model for Story 2.6 (Stripe card payments)."""

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0006_remove_storetheme_font_family_and_more"),
        ("payment", "0002_add_reversal_reason"),
    ]

    operations = [
        migrations.CreateModel(
            name="CardTransaction",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                ("_safedelete_policy", models.IntegerField(default=1)),
                ("reference", models.CharField(db_index=True, max_length=100)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("currency", models.CharField(default="kes", max_length=3)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PI_CREATED", "Payment Intent Created"),
                            ("PROCESSING", "Processing"),
                            ("SUCCEEDED", "Succeeded"),
                            ("FAILED", "Failed"),
                            ("REFUNDED", "Refunded"),
                        ],
                        default="PI_CREATED",
                        max_length=30,
                    ),
                ),
                ("stripe_payment_intent_id", models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ("stripe_client_secret", models.TextField(blank=True, default="")),
                (
                    "provider",
                    models.CharField(default="stripe", help_text="Card provider: 'stripe' or 'flutterwave'", max_length=20),
                ),
                ("customer_email", models.EmailField(blank=True, default="", max_length=254)),
                ("initiated_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("failure_reason", models.TextField(blank=True, default="")),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to="store.store")),
            ],
            options={
                "db_table": "payment_cardtransaction",
                "indexes": [
                    models.Index(fields=["store", "reference"], name="payment_card_store_ref_idx"),
                    models.Index(fields=["stripe_payment_intent_id"], name="payment_card_pi_idx"),
                ],
            },
        ),
    ]
