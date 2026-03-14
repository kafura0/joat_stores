# Hand-written migration: Story 1.3
# PostgreSQL cannot ALTER COLUMN bigint→uuid directly. Use RunSQL to:
#   1. Drop PK constraint
#   2. Drop old bigint column
#   3. Add UUID column as new PK

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0001_initial"),
    ]

    operations = [
        # ----- StoreSettings -----
        migrations.RunSQL(
            sql=[
                # Drop default sequence and PK, add new UUID PK
                "ALTER TABLE store_storesettings DROP CONSTRAINT store_storesettings_pkey;",
                "ALTER TABLE store_storesettings DROP COLUMN id;",
                "ALTER TABLE store_storesettings ADD COLUMN id uuid PRIMARY KEY DEFAULT gen_random_uuid();",
            ],
            reverse_sql=[
                "ALTER TABLE store_storesettings DROP CONSTRAINT store_storesettings_pkey;",
                "ALTER TABLE store_storesettings DROP COLUMN id;",
                "ALTER TABLE store_storesettings ADD COLUMN id bigserial PRIMARY KEY;",
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="storesettings",
                    name="id",
                    field=models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
            ],
        ),
        # ----- StoreTheme -----
        migrations.RunSQL(
            sql=[
                "ALTER TABLE store_storetheme DROP CONSTRAINT store_storetheme_pkey;",
                "ALTER TABLE store_storetheme DROP COLUMN id;",
                "ALTER TABLE store_storetheme ADD COLUMN id uuid PRIMARY KEY DEFAULT gen_random_uuid();",
            ],
            reverse_sql=[
                "ALTER TABLE store_storetheme DROP CONSTRAINT store_storetheme_pkey;",
                "ALTER TABLE store_storetheme DROP COLUMN id;",
                "ALTER TABLE store_storetheme ADD COLUMN id bigserial PRIMARY KEY;",
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="storetheme",
                    name="id",
                    field=models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
            ],
        ),
    ]
