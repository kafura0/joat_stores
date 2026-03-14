"""Migration: add low_stock_threshold to StoreSettings (Story 4.1)."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0004_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="storesettings",
            name="low_stock_threshold",
            field=models.IntegerField(
                default=5,
                help_text="Variant inventory_count at or below which a low-stock alert fires.",
            ),
        ),
    ]
