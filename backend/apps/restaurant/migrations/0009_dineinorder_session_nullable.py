"""Migration: make DineInOrder.session nullable for takeaway orders (Story 3.10)."""

import django.db.models.deletion

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("restaurant", "0008_add_order_type_pickup_ref"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dineinorder",
            name="session",
            field=models.ForeignKey(
                blank=True,
                help_text="Null for takeaway orders — no table session required.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="orders",
                to="restaurant.tablesession",
            ),
        ),
    ]
