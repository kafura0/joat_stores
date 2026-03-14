"""
Order serializers — Story 4.3, 4.4.
"""

from rest_framework import serializers

from apps.order.models import CartSnapshot, Order


class CartItemSerializer(serializers.Serializer):
    """Single cart line item for add-to-cart input."""

    product_id = serializers.UUIDField()
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=99)


class CartSerializer(serializers.Serializer):
    """Full cart response — items with quantity."""

    cart_ref = serializers.CharField()
    items = CartItemSerializer(many=True)
    item_count = serializers.SerializerMethodField()

    def get_item_count(self, obj) -> int:
        return sum(i["quantity"] for i in obj.get("items", []))


class OrderSerializer(serializers.ModelSerializer):
    """Output serializer for Order."""

    class Meta:
        model = Order
        fields = [
            "id",
            "customer_phone",
            "customer_name",
            "customer_email",
            "delivery_address",
            "items_snapshot",
            "total_amount",
            "status",
            "payment_transaction",
            "confirmed_at",
            "fulfilled_at",
            "completed_at",
            "cancelled_at",
            "created_at",
        ]
        read_only_fields = fields


class CheckoutInputSerializer(serializers.Serializer):
    """Input for POST /api/v1/store/checkout/."""

    phone = serializers.CharField(max_length=30)
    name = serializers.CharField(max_length=255, required=False, default="")
    email = serializers.EmailField(required=False, default="")
    delivery_address = serializers.JSONField(required=False, default=None)
    cart_ref = serializers.CharField(max_length=255)
