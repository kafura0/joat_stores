from rest_framework import serializers

from apps.store.models import Store


class HubRegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    full_name = serializers.CharField(max_length=255, required=False, default="")
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")


class HubLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class LinkedStoreSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.SlugField()
    domain = serializers.CharField()
    tenant_type = serializers.CharField()
    logo_url = serializers.SerializerMethodField()
    tagline = serializers.SerializerMethodField()

    def get_logo_url(self, obj):
        try:
            return obj.settings.logo_url or ""
        except Exception:
            return ""

    def get_tagline(self, obj):
        try:
            return obj.settings.tagline or ""
        except Exception:
            return ""


class HubOrderItemSerializer(serializers.Serializer):
    product_name = serializers.CharField(source="name", default="")
    variant_name = serializers.CharField(default="")
    quantity = serializers.IntegerField(default=1)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)


class HubOrderSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    store_id = serializers.UUIDField(source="store.id")
    store_name = serializers.CharField(source="store.name")
    store_slug = serializers.SlugField(source="store.slug")
    status = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    items_count = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()

    def get_items_count(self, obj):
        return len(obj.items_snapshot)


class HubLoyaltySerializer(serializers.Serializer):
    store_id = serializers.UUIDField(source="store.id")
    store_name = serializers.CharField(source="store.name")
    points_balance = serializers.IntegerField()
    lifetime_earned = serializers.IntegerField()


class PlatformUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    phone = serializers.CharField()
    full_name = serializers.CharField()
    avatar_url = serializers.URLField()
    created_at = serializers.DateTimeField()
