"""
Epic 10 — Customer Loyalty + Engagement.

Story 10.1: LoyaltyAccount, PointsTransaction
Story 10.2: StampCard, CustomerStampCard, CustomerStamp
Story 10.4: CustomerProfile
"""

import decimal
import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("store", "0005_storesettings_low_stock_threshold"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ------------------------------------------------------- LoyaltyAccount
        migrations.CreateModel(
            name="LoyaltyAccount",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to="store.store")),
                ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="loyalty_accounts", to=settings.AUTH_USER_MODEL)),
                ("customer_phone", models.CharField(db_index=True, max_length=30)),
                ("points_balance", models.IntegerField(default=0)),
                ("lifetime_earned", models.IntegerField(default=0)),
            ],
            options={"ordering": ["-lifetime_earned"]},
        ),
        migrations.AlterUniqueTogether(
            name="loyaltyaccount",
            unique_together={("store", "customer_phone")},
        ),

        # ----------------------------------------------------- PointsTransaction
        migrations.CreateModel(
            name="PointsTransaction",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to="store.store")),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="transactions", to="loyalty.loyaltyaccount")),
                ("delta", models.IntegerField(help_text="Positive = earned, negative = redeemed/expired.")),
                ("balance_after", models.IntegerField()),
                ("source", models.CharField(choices=[("order", "Order"), ("redemption", "Redemption"), ("manual", "Manual Adjustment"), ("expiry", "Expiry")], db_index=True, max_length=20)),
                ("reference", models.CharField(blank=True, default="", max_length=255)),
                ("occurred_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={"ordering": ["-occurred_at"]},
        ),
        migrations.AddIndex(
            model_name="pointstransaction",
            index=models.Index(fields=["store", "occurred_at"], name="idx_loyalty_tx_store_date"),
        ),

        # ----------------------------------------------------------- StampCard
        migrations.CreateModel(
            name="StampCard",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to="store.store")),
                ("name", models.CharField(max_length=100)),
                ("stamps_required", models.PositiveIntegerField(default=10)),
                ("reward_description", models.CharField(max_length=255)),
                ("points_per_stamp", models.IntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["name"]},
        ),

        # ------------------------------------------------------ CustomerStampCard
        migrations.CreateModel(
            name="CustomerStampCard",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to="store.store")),
                ("stamp_card", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="customer_cards", to="loyalty.stampcard")),
                ("customer_phone", models.CharField(db_index=True, max_length=30)),
                ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("stamps_count", models.PositiveIntegerField(default=0)),
                ("redeemed_count", models.PositiveIntegerField(default=0)),
                ("last_stamp_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ["-last_stamp_at"]},
        ),
        migrations.AlterUniqueTogether(
            name="customerstampcard",
            unique_together={("store", "stamp_card", "customer_phone")},
        ),

        # --------------------------------------------------------- CustomerStamp
        migrations.CreateModel(
            name="CustomerStamp",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to="store.store")),
                ("customer_card", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="stamps", to="loyalty.customerstampcard")),
                ("order_reference", models.CharField(blank=True, default="", max_length=255)),
                ("earned_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={"ordering": ["-earned_at"]},
        ),

        # ----------------------------------------------------- CustomerProfile
        migrations.CreateModel(
            name="CustomerProfile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to="store.store")),
                ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="customer_profiles", to=settings.AUTH_USER_MODEL)),
                ("customer_phone", models.CharField(db_index=True, max_length=30)),
                ("customer_email", models.EmailField(blank=True, default="")),
                ("customer_name", models.CharField(blank=True, default="", max_length=255)),
                ("order_count", models.PositiveIntegerField(default=0)),
                ("total_spent", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=14)),
                ("first_order_at", models.DateTimeField(blank=True, null=True)),
                ("last_order_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ["-last_order_at"]},
        ),
        migrations.AlterUniqueTogether(
            name="customerprofile",
            unique_together={("store", "customer_phone")},
        ),
        migrations.AddIndex(
            model_name="customerprofile",
            index=models.Index(fields=["store", "last_order_at"], name="idx_loyalty_profile_store_last"),
        ),
    ]
