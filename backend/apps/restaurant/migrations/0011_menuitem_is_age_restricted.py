"""
Add is_age_restricted flag to MenuItem.

Required by Story 5.3 (bar age-restricted items).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("restaurant", "0010_add_bill_share"),
    ]

    operations = [
        migrations.AddField(
            model_name="menuitem",
            name="is_age_restricted",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "If True, customers must acknowledge age restriction (18+) "
                    "before ordering this item in a bar tab."
                ),
            ),
        ),
    ]
