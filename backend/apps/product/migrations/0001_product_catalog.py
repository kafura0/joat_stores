"""Migration: add product catalog models (Story 4.1)."""

import django.core.validators
import django.db.models.deletion
import uuid
from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("store", "0004_initial"),
    ]

    operations = [
        # Category
        migrations.CreateModel(
            name="Category",
            fields=[
                ("deleted", models.DateTimeField(db_index=True, editable=False, null=True)),
                ("deleted_by_cascade", models.BooleanField(default=False, editable=False)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "store",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="store.store",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True, default="")),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="children",
                        to="product.category",
                    ),
                ),
                ("position", models.IntegerField(default=0)),
            ],
            options={"ordering": ["position", "name"], "abstract": False},
        ),
        migrations.AddIndex(
            model_name="category",
            index=models.Index(fields=["store", "parent"], name="idx_product_category_parent"),
        ),
        # Product
        migrations.CreateModel(
            name="Product",
            fields=[
                ("deleted", models.DateTimeField(db_index=True, editable=False, null=True)),
                ("deleted_by_cascade", models.BooleanField(default=False, editable=False)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "store",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="store.store",
                    ),
                ),
                (
                    "category",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="products",
                        to="product.category",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("attribute_names", models.JSONField(default=list)),
                ("is_available", models.BooleanField(db_index=True, default=True)),
            ],
            options={"ordering": ["name"], "abstract": False},
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["store", "is_available"], name="idx_product_store_available"),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["store", "category"], name="idx_product_store_category"),
        ),
        # Variant
        migrations.CreateModel(
            name="Variant",
            fields=[
                ("deleted", models.DateTimeField(db_index=True, editable=False, null=True)),
                ("deleted_by_cascade", models.BooleanField(default=False, editable=False)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "store",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="store.store",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="variants",
                        to="product.product",
                    ),
                ),
                ("attribute_values", models.JSONField(default=dict)),
                (
                    "price",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                    ),
                ),
                ("inventory_count", models.IntegerField(default=0)),
                ("is_available", models.BooleanField(default=True)),
                ("sku", models.CharField(blank=True, default="", max_length=100)),
            ],
            options={"ordering": ["id"], "abstract": False},
        ),
        migrations.AddIndex(
            model_name="variant",
            index=models.Index(fields=["store", "product"], name="idx_variant_store_product"),
        ),
        migrations.AddIndex(
            model_name="variant",
            index=models.Index(fields=["store", "is_available"], name="idx_variant_available"),
        ),
        # ProductImage
        migrations.CreateModel(
            name="ProductImage",
            fields=[
                ("deleted", models.DateTimeField(db_index=True, editable=False, null=True)),
                ("deleted_by_cascade", models.BooleanField(default=False, editable=False)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "store",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="store.store",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="images",
                        to="product.product",
                    ),
                ),
                (
                    "variant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="images",
                        to="product.variant",
                    ),
                ),
                ("image", models.ImageField(upload_to="products/images/")),
                ("alt_text", models.CharField(blank=True, default="", max_length=255)),
                ("position", models.IntegerField(default=0)),
                ("is_default", models.BooleanField(default=False)),
            ],
            options={"ordering": ["position", "id"], "abstract": False},
        ),
        migrations.AddIndex(
            model_name="productimage",
            index=models.Index(fields=["store", "product"], name="idx_productimage_product"),
        ),
    ]
