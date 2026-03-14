"""
Bar domain serializers.

Stories 5.1-5.5.
"""

from decimal import Decimal

from rest_framework import serializers

from apps.bar.models import AgeRestrictionLog, HappyHour, Tab, TabItem, TabRound, TabShare


class TabItemSerializer(serializers.ModelSerializer):
    removal_info = serializers.SerializerMethodField()

    class Meta:
        model = TabItem
        fields = [
            "id",
            "menu_item",
            "name",
            "unit_price",
            "quantity",
            "is_happy_hour",
            "created_at",
            "removed_at",
            "removal_info",
        ]
        read_only_fields = fields

    def get_removal_info(self, obj):
        if not obj.removed_at:
            return None
        return {
            "removed_by": obj.removed_by_name or "staff",
            "at": obj.removed_at.strftime("%H:%M"),
        }


class TabRoundSerializer(serializers.ModelSerializer):
    items = TabItemSerializer(many=True, read_only=True)

    class Meta:
        model = TabRound
        fields = ["id", "round_number", "created_at", "items"]
        read_only_fields = fields


class TabSerializer(serializers.ModelSerializer):
    total_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = Tab
        fields = [
            "id",
            "customer",
            "customer_name",
            "status",
            "total_amount",
            "opened_at",
            "settled_at",
        ]
        read_only_fields = ["id", "status", "total_amount", "opened_at", "settled_at"]


class TabDetailSerializer(TabSerializer):
    rounds = TabRoundSerializer(many=True, read_only=True)

    class Meta(TabSerializer.Meta):
        fields = list(TabSerializer.Meta.fields) + ["rounds"]
        read_only_fields = fields


class AddRoundSerializer(serializers.Serializer):
    """Request body for POST /api/v1/bar/tabs/{id}/rounds/"""

    items = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        help_text=(
            "List of {menu_item_id, quantity, acknowledge_age_restriction?} dicts."
        ),
    )
    customer_phone = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Required if customer adds age-restricted items without auth.",
    )

    def validate_items(self, items):
        for item in items:
            if "menu_item_id" not in item:
                raise serializers.ValidationError("Each item must have menu_item_id.")
            qty = item.get("quantity", 1)
            if not isinstance(qty, int) or qty < 1:
                raise serializers.ValidationError("quantity must be a positive integer.")
        return items


class RemoveItemSerializer(serializers.Serializer):
    """Request body for DELETE /api/v1/bar/tabs/{tab_id}/items/{item_id}/"""

    # No body fields required; staff identity comes from request.user
    pass


class SplitTabSerializer(serializers.Serializer):
    """Request body for POST /api/v1/bar/tabs/{id}/split/"""

    shares = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        help_text="List of {payer_phone, amount} or {payer_phone, percentage} dicts.",
    )

    def validate_shares(self, shares):
        for share in shares:
            if "payer_phone" not in share:
                raise serializers.ValidationError("Each share must have payer_phone.")
            has_amount = "amount" in share
            has_pct = "percentage" in share
            if not has_amount and not has_pct:
                raise serializers.ValidationError(
                    "Each share must have either amount or percentage."
                )
            if has_amount:
                try:
                    amt = Decimal(str(share["amount"]))
                    if amt <= 0:
                        raise serializers.ValidationError("amount must be positive.")
                except Exception:
                    raise serializers.ValidationError("amount must be a valid decimal.")
        return shares


class TabShareSerializer(serializers.ModelSerializer):
    class Meta:
        model = TabShare
        fields = [
            "id",
            "payer_phone",
            "amount",
            "percentage",
            "status",
            "created_at",
        ]
        read_only_fields = fields


class HappyHourSerializer(serializers.ModelSerializer):
    class Meta:
        model = HappyHour
        fields = [
            "id",
            "name",
            "start_time",
            "end_time",
            "discount_percent",
            "days_of_week",
            "is_active",
        ]
        read_only_fields = ["id"]
