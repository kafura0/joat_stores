"""
Initial bar app migration.

Creates: Tab, TabRound, TabItem, AgeRestrictionLog, HappyHour, TabShare

Story 5.1: Tab + state machine
Story 5.2: TabRound, TabItem (with removal audit)
Story 5.3: AgeRestrictionLog
Story 5.4: HappyHour
Story 5.5: TabShare
"""

import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("restaurant", "0011_menuitem_is_age_restricted"),
        ("payment", "0002_add_reversal_reason"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("store", "0005_storesettings_low_stock_threshold"),
    ]

    operations = [
        # ------------------------------------------------------------------ Tab
        migrations.CreateModel(
            name="Tab",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("deleted", models.DateTimeField(db_index=True, editable=False, null=True)),
                ("deleted_by_cascade", models.BooleanField(default=False, editable=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(app_label)s_%(class)s_set", to="store.store")),
                ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="bar_tabs", to=settings.AUTH_USER_MODEL)),
                ("customer_name", models.CharField(blank=True, default="", max_length=200)),
                ("status", models.CharField(choices=[("OPEN", "Open"), ("BILL_REQUESTED", "Bill Requested"), ("SETTLED", "Settled")], db_index=True, default="OPEN", max_length=20)),
                ("opened_at", models.DateTimeField(auto_now_add=True)),
                ("settled_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ["-opened_at"]},
        ),
        migrations.AddIndex(
            model_name="tab",
            index=models.Index(fields=["store", "status"], name="idx_bar_tab_store_status"),
        ),

        # ------------------------------------------------------------ TabRound
        migrations.CreateModel(
            name="TabRound",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("deleted", models.DateTimeField(db_index=True, editable=False, null=True)),
                ("deleted_by_cascade", models.BooleanField(default=False, editable=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(app_label)s_%(class)s_set", to="store.store")),
                ("tab", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rounds", to="bar.tab")),
                ("round_number", models.PositiveSmallIntegerField(help_text="Sequential round number within the tab (1-indexed).")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["round_number"]},
        ),
        migrations.AddConstraint(
            model_name="tabround",
            constraint=models.UniqueConstraint(fields=["tab", "round_number"], name="uq_bar_tabround_tab_round_number"),
        ),

        # ------------------------------------------------------------- TabItem
        migrations.CreateModel(
            name="TabItem",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("deleted", models.DateTimeField(db_index=True, editable=False, null=True)),
                ("deleted_by_cascade", models.BooleanField(default=False, editable=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(app_label)s_%(class)s_set", to="store.store")),
                ("tab", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="bar.tab")),
                ("round", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="bar.tabround")),
                ("menu_item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="tab_items", to="restaurant.menuitem")),
                ("name", models.CharField(max_length=150)),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal("0.00"))])),
                ("quantity", models.PositiveSmallIntegerField(default=1)),
                ("is_happy_hour", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("removed_at", models.DateTimeField(blank=True, null=True)),
                ("removed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("removed_by_name", models.CharField(blank=True, default="", max_length=200)),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddIndex(
            model_name="tabitem",
            index=models.Index(fields=["tab", "removed_at"], name="idx_bar_tabitem_tab_removed"),
        ),

        # ------------------------------------------------------- AgeRestrictionLog
        migrations.CreateModel(
            name="AgeRestrictionLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("deleted", models.DateTimeField(db_index=True, editable=False, null=True)),
                ("deleted_by_cascade", models.BooleanField(default=False, editable=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(app_label)s_%(class)s_set", to="store.store")),
                ("tab", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="age_restriction_logs", to="bar.tab")),
                ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("customer_phone", models.CharField(blank=True, default="", max_length=20)),
                ("acknowledged_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-acknowledged_at"]},
        ),
        migrations.AddIndex(
            model_name="agerestrictionlog",
            index=models.Index(fields=["tab", "customer"], name="idx_bar_agerestrictionlog_tab_customer"),
        ),

        # ---------------------------------------------------------- HappyHour
        migrations.CreateModel(
            name="HappyHour",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("deleted", models.DateTimeField(db_index=True, editable=False, null=True)),
                ("deleted_by_cascade", models.BooleanField(default=False, editable=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(app_label)s_%(class)s_set", to="store.store")),
                ("name", models.CharField(max_length=100)),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("discount_percent", models.DecimalField(
                    decimal_places=2, max_digits=5,
                    validators=[
                        django.core.validators.MinValueValidator(Decimal("0")),
                        django.core.validators.MaxValueValidator(Decimal("100")),
                    ],
                )),
                ("days_of_week", models.JSONField(default=list)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["start_time"]},
        ),
        migrations.AddIndex(
            model_name="happyhour",
            index=models.Index(fields=["store", "is_active"], name="idx_bar_happyhour_store_active"),
        ),

        # ----------------------------------------------------------- TabShare
        migrations.CreateModel(
            name="TabShare",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("deleted", models.DateTimeField(db_index=True, editable=False, null=True)),
                ("deleted_by_cascade", models.BooleanField(default=False, editable=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(app_label)s_%(class)s_set", to="store.store")),
                ("tab", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="shares", to="bar.tab")),
                ("payer_phone", models.CharField(max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal("0.00"))])),
                ("item_ids", models.JSONField(default=list)),
                ("percentage", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("PAID", "Paid"), ("FAILED", "Failed / timed out")], db_index=True, default="PENDING", max_length=20)),
                ("payment_transaction", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="tab_shares", to="payment.mpesatransaction")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="tabshare",
            index=models.Index(fields=["store", "tab", "status"], name="idx_bar_tabshare_tab_status"),
        ),
    ]
