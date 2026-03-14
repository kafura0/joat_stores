"""Analytics serializers — Stories 8.2, 8.6."""

from rest_framework import serializers

from apps.analytics.models import AIEvent, TenantHealthSnapshot


class AIEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIEvent
        fields = ["id", "store", "customer", "event_type", "entity_id", "metadata", "occurred_at"]
        read_only_fields = fields


class TenantHealthSnapshotSerializer(serializers.ModelSerializer):
    store_name = serializers.SerializerMethodField()

    class Meta:
        model = TenantHealthSnapshot
        fields = [
            "store", "store_name", "date", "gmv", "gmv_usd",
            "order_count", "subscription_status", "is_healthy",
        ]
        read_only_fields = fields

    def get_store_name(self, obj):
        return obj.store.name if obj.store else ""
