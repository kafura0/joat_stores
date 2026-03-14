"""Migration: add payment_transaction FK to DineInOrder (Story 3.8)."""

import django.db.models.deletion

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("restaurant", "0005_add_pending_order"),
        ("payment", "0002_add_reversal_reason"),
    ]

    operations = [
        migrations.AddField(
            model_name="dineinorder",
            name="payment_transaction",
            field=models.ForeignKey(
                blank=True,
                help_text="M-Pesa transaction linked to this order (advance or table-side payment).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="dine_in_orders",
                to="payment.mpesatransaction",
            ),
        ),
    ]
