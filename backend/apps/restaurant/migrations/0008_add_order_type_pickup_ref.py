"""Migration: add order_type + pickup_reference to DineInOrder (Story 3.10)."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("restaurant", "0007_add_reservation"),
    ]

    operations = [
        migrations.AddField(
            model_name="dineinorder",
            name="order_type",
            field=models.CharField(
                choices=[("dine_in", "Dine In"), ("takeaway", "Takeaway")],
                db_index=True,
                default="dine_in",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="dineinorder",
            name="pickup_reference",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Unique pickup reference for takeaway orders.",
                max_length=20,
            ),
        ),
    ]
