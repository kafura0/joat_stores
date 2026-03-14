"""Loyalty serializers — Epic 10."""

from rest_framework import serializers

from apps.loyalty.models import (
    CustomerProfile,
    CustomerStampCard,
    LoyaltyAccount,
    PointsTransaction,
    StampCard,
)


class LoyaltyAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyAccount
        fields = ["id", "customer_phone", "points_balance", "lifetime_earned"]
        read_only_fields = fields


class PointsTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointsTransaction
        fields = ["id", "delta", "balance_after", "source", "reference", "occurred_at"]
        read_only_fields = fields


class StampCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = StampCard
        fields = [
            "id", "name", "stamps_required", "reward_description",
            "points_per_stamp", "is_active",
        ]
        read_only_fields = ["id"]


class CustomerStampCardSerializer(serializers.ModelSerializer):
    stamp_card = StampCardSerializer(read_only=True)
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = CustomerStampCard
        fields = [
            "id", "stamp_card", "customer_phone", "stamps_count",
            "redeemed_count", "last_stamp_at", "progress_percent",
        ]
        read_only_fields = fields

    def get_progress_percent(self, obj):
        required = obj.stamp_card.stamps_required
        if required == 0:
            return 100
        return min(100, round(obj.stamps_count / required * 100))


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = [
            "id", "customer_phone", "customer_email", "customer_name",
            "order_count", "total_spent", "first_order_at", "last_order_at",
        ]
        read_only_fields = fields
