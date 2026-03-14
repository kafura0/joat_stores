"""
Epic 9 — SaaS Plans + Subscription Management.

Story 9.1: Expand Plan with pricing, feature flags, resource limits.
Story 9.2: Expand StoreSubscription with period tracking + state machine fields.
Story 9.3: current_payment_transaction FK for M-Pesa renewal.
Story 9.7: Suspension / cancellation audit timestamps.
"""

import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("saas", "0001_plan_storesubscription_stubs"),
        ("payment", "0001_mpesa_transaction"),
    ]

    operations = [
        # ---- Plan expansions (Story 9.1) ----
        migrations.AddField(
            model_name="plan",
            name="slug",
            field=models.SlugField(default="free", unique=True, max_length=50),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="plan",
            name="price_kes",
            field=models.DecimalField(
                decimal_places=2, default=Decimal("0.00"),
                help_text="Plan price in Kenya Shillings (0 = free).",
                max_digits=10,
            ),
        ),
        migrations.AddField(
            model_name="plan",
            name="billing_cycle",
            field=models.CharField(
                choices=[("monthly", "Monthly"), ("annual", "Annual")],
                default="monthly",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="plan",
            name="trial_days",
            field=models.PositiveIntegerField(default=14),
        ),
        migrations.AddField(
            model_name="plan",
            name="max_products",
            field=models.PositiveIntegerField(
                blank=True, null=True,
                help_text="Max catalogue products (null = unlimited).",
            ),
        ),
        migrations.AddField(
            model_name="plan",
            name="max_orders_per_month",
            field=models.PositiveIntegerField(
                blank=True, null=True,
                help_text="Max orders per calendar month (null = unlimited).",
            ),
        ),
        migrations.AddField(
            model_name="plan",
            name="max_staff",
            field=models.PositiveIntegerField(
                blank=True, null=True,
                help_text="Max staff accounts (null = unlimited).",
            ),
        ),
        migrations.AddField(
            model_name="plan",
            name="has_analytics",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="plan",
            name="has_qr_codes",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="plan",
            name="has_ai_features",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="plan",
            name="has_whatsapp",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="plan",
            name="is_public",
            field=models.BooleanField(
                default=True,
                help_text="Visible on the public pricing page.",
            ),
        ),
        migrations.AddField(
            model_name="plan",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name="plan",
            name="name",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterModelOptions(
            name="plan",
            options={"ordering": ["price_kes"]},
        ),

        # ---- StoreSubscription expansions (Story 9.2) ----
        migrations.AddField(
            model_name="storesubscription",
            name="period_start",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="storesubscription",
            name="period_end",
            field=models.DateField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="storesubscription",
            name="trial_ends_at",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="storesubscription",
            name="status",
            field=models.CharField(
                choices=[
                    ("trial", "Trial"),
                    ("active", "Active"),
                    ("past_due", "Past Due"),
                    ("suspended", "Suspended"),
                    ("cancelled", "Cancelled"),
                ],
                db_index=True,
                default="trial",
                max_length=20,
            ),
        ),

        # ---- M-Pesa renewal FK (Story 9.3) ----
        migrations.AddField(
            model_name="storesubscription",
            name="current_payment_transaction",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="payment.mpesatransaction",
            ),
        ),

        # ---- Suspension / cancellation audit (Story 9.7) ----
        migrations.AddField(
            model_name="storesubscription",
            name="past_due_since",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="storesubscription",
            name="suspended_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="storesubscription",
            name="cancelled_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
