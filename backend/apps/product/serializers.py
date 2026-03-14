"""
Product catalog serializers — Story 4.1.
"""

from rest_framework import serializers

from apps.product.models import Category, Product, ProductImage, Variant


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description", "parent", "position"]
        read_only_fields = ["id"]


class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "product", "variant", "image", "image_url", "alt_text", "position", "is_default"]
        read_only_fields = ["id", "image_url"]

    def get_image_url(self, obj) -> str | None:
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class VariantSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Variant
        fields = [
            "id",
            "product",
            "attribute_values",
            "price",
            "inventory_count",
            "is_available",
            "sku",
            "images",
        ]
        read_only_fields = ["id", "images"]


class ProductSerializer(serializers.ModelSerializer):
    """Read/write serializer for Product (without nested variants — for list view)."""

    class Meta:
        model = Product
        fields = [
            "id",
            "category",
            "name",
            "description",
            "attribute_names",
            "is_available",
        ]
        read_only_fields = ["id"]


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Detail serializer with full variant + image nesting.

    Used for GET /api/v1/store/products/{id}/.
    Prices are pre-loaded in the payload so the storefront can switch variants
    client-side without an extra API call (Story 4.1 AC).
    """

    variants = VariantSerializer(many=True, read_only=True)
    images = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "category",
            "name",
            "description",
            "attribute_names",
            "is_available",
            "variants",
            "images",
        ]
        read_only_fields = list(fields)

    def get_images(self, obj):
        """Return product-level images (variant=None) only."""
        product_images = obj.images.filter(variant__isnull=True)
        return ProductImageSerializer(
            product_images,
            many=True,
            context=self.context,
        ).data


class ProductImageUploadSerializer(serializers.ModelSerializer):
    """Input serializer for image upload endpoint."""

    class Meta:
        model = ProductImage
        fields = ["product", "variant", "image", "alt_text", "position", "is_default"]
