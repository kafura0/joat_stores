"""Add reversal_reason field to MpesaTransaction.

Generated for Story 2.5: Payment Reconciliation + Reversal
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payment", "0001_mpesa_transaction"),
    ]

    operations = [
        migrations.AddField(
            model_name="mpesatransaction",
            name="reversal_reason",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
