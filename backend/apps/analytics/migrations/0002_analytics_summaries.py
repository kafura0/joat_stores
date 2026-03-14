"""
Add analytics summary models.

Story 8.1: DailyRevenueSummary, HourlyOrderSummary
Story 8.2: AIEvent (append-only)
Story 8.6: TenantHealthSnapshot
Story 8.7: StoreFirstOrderEvent
"""

import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0001_admin_pii_access_log"),
        ("order", "0001_order_cartsnapshot"),
        ("store", "0005_storesettings_low_stock_threshold"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # -------------------------------------------------- DailyRevenueSummary
        migrations.CreateModel(
            name="DailyRevenueSummary",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to="store.store")),
                ("date", models.DateField(db_index=True)),
                ("total_revenue", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("order_count", models.PositiveIntegerField(default=0)),
                ("aov", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("amount_usd", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("top_products", models.JSONField(default=list)),
            ],
            options={"ordering": ["-date"]},
        ),
        migrations.AlterUniqueTogether(
            name="dailyrevenuesummary",
            unique_together={("store", "date")},
        ),
        migrations.AddIndex(
            model_name="dailyrevenuesummary",
            index=models.Index(fields=["store", "date"], name="idx_analytics_drs_store_date"),
        ),

        # ------------------------------------------------- HourlyOrderSummary
        migrations.CreateModel(
            name="HourlyOrderSummary",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to="store.store")),
                ("date", models.DateField(db_index=True)),
                ("hour", models.PositiveSmallIntegerField()),
                ("order_count", models.PositiveIntegerField(default=0)),
                ("revenue", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
            ],
            options={"ordering": ["date", "hour"]},
        ),
        migrations.AlterUniqueTogether(
            name="hourlyordersummary",
            unique_together={("store", "date", "hour")},
        ),
        migrations.AddIndex(
            model_name="hourlyordersummary",
            index=models.Index(fields=["store", "date"], name="idx_analytics_hos_store_date"),
        ),

        # ------------------------------------------------------- AIEvent
        migrations.CreateModel(
            name="AIEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to="store.store")),
                ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("event_type", models.CharField(choices=[("product_view", "Product View"), ("cart_add", "Cart Add"), ("cart_remove", "Cart Remove"), ("search", "Search"), ("order_complete", "Order Complete")], db_index=True, max_length=30)),
                ("entity_id", models.CharField(blank=True, default="", max_length=255)),
                ("metadata", models.JSONField(default=dict)),
                ("occurred_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={"ordering": ["-occurred_at"]},
        ),
        migrations.AddIndex(
            model_name="aievent",
            index=models.Index(fields=["store", "event_type", "occurred_at"], name="idx_analytics_aievent_store_type"),
        ),

        # ------------------------------------------------- TenantHealthSnapshot
        migrations.CreateModel(
            name="TenantHealthSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to="store.store")),
                ("date", models.DateField(db_index=True)),
                ("gmv", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("gmv_usd", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("order_count", models.PositiveIntegerField(default=0)),
                ("subscription_status", models.CharField(blank=True, default="", max_length=30)),
                ("is_healthy", models.BooleanField(default=True)),
            ],
            options={"ordering": ["-date"]},
        ),
        migrations.AlterUniqueTogether(
            name="tenanthealthsnapshot",
            unique_together={("store", "date")},
        ),
        migrations.AddIndex(
            model_name="tenanthealthsnapshot",
            index=models.Index(fields=["date", "is_healthy"], name="idx_analytics_ths_date_health"),
        ),

        # ----------------------------------------------- StoreFirstOrderEvent
        migrations.CreateModel(
            name="StoreFirstOrderEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("store", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="first_order_event", to="store.store")),
                ("order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="order.order")),
                ("first_order_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("occurred_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
            ],
            options={"ordering": ["occurred_at"]},
        ),
        migrations.AddIndex(
            model_name="storefirstorderevent",
            index=models.Index(fields=["occurred_at"], name="idx_analytics_firstorder_at"),
        ),
    ]
