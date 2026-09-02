"""
Notifications app — Story 10.3, 10.5.
"""

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("store", "0005_storesettings_low_stock_threshold"),
    ]

    operations = [
        # ---------------------------------------------------- WhatsAppMessage
        migrations.CreateModel(
            name="WhatsAppMessage",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to="store.store")),
                ("recipient_phone", models.CharField(db_index=True, max_length=30)),
                ("template", models.CharField(choices=[("order_confirmation", "Order Confirmation"), ("loyalty_reward", "Loyalty Reward"), ("stamp_threshold", "Stamp Card Reward"), ("subscription_renewal", "Subscription Renewal"), ("generic", "Generic")], default="generic", max_length=50)),
                ("message_body", models.TextField()),
                ("status", models.CharField(choices=[("queued", "Queued"), ("sent", "Sent"), ("failed", "Failed")], db_index=True, default="queued", max_length=20)),
                ("external_message_id", models.CharField(blank=True, default="", max_length=255)),
                ("error_detail", models.TextField(blank=True, default="")),
                ("queued_at", models.DateTimeField(auto_now_add=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ["-queued_at"]},
        ),
        migrations.AddIndex(
            model_name="whatsappmessage",
            index=models.Index(fields=["store", "queued_at"], name="idx_notif_wa_store_queued"),
        ),

        # -------------------------------------------- WhatsAppInboundMessage
        migrations.CreateModel(
            name="WhatsAppInboundMessage",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to="store.store")),
                ("sender_phone", models.CharField(db_index=True, max_length=30)),
                ("raw_body", models.TextField()),
                ("parsed_intent", models.CharField(blank=True, default="", help_text="Detected intent: 'order', 'menu', 'status', 'unknown'.", max_length=50)),
                ("response_sent", models.BooleanField(default=False)),
                ("received_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={"ordering": ["-received_at"]},
        ),
    ]
