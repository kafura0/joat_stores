"""
SaaS serializers — Epic 9.
"""

from rest_framework import serializers

from apps.saas.models import Plan, StoreSubscription


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            "id",
            "slug",
            "name",
            "price_kes",
            "billing_cycle",
            "trial_days",
            "max_products",
            "max_orders_per_month",
            "max_staff",
            "has_analytics",
            "has_qr_codes",
            "has_ai_features",
            "has_whatsapp",
            "api_rate_limit",
            "is_public",
            "is_active",
        ]
        read_only_fields = ["id"]


class StoreSubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=Plan.objects.filter(is_active=True),
        source="plan",
        write_only=True,
        required=False,
        allow_null=True,
    )
    days_until_expiry = serializers.SerializerMethodField()
    renewal_amount_kes = serializers.SerializerMethodField()

    class Meta:
        model = StoreSubscription
        fields = [
            "id",
            "store_id",
            "plan",
            "plan_id",
            "status",
            "period_start",
            "period_end",
            "trial_ends_at",
            "past_due_since",
            "suspended_at",
            "cancelled_at",
            "days_until_expiry",
            "renewal_amount_kes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "store_id", "status", "period_start", "period_end",
            "trial_ends_at", "past_due_since", "suspended_at", "cancelled_at",
            "created_at", "updated_at",
        ]

    def get_days_until_expiry(self, obj):
        return obj.days_until_expiry

    def get_renewal_amount_kes(self, obj):
        return str(obj.renewal_amount_kes)
