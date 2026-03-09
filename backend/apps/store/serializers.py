"""
Store serializers for platform admin endpoints.

StoreProvisionSerializer — validates and creates a store atomically.
StoreListSerializer      — read-only list representation.
StoreStatusSerializer    — validates status transitions.

Implementation: Story 1.4
"""

from django.db import transaction
from django.utils.text import slugify

from rest_framework import serializers

from apps.saas.models import StoreSubscription
from apps.store.models import Store, StoreStatus, TenantType
from apps.users.models import User


class StoreProvisionSerializer(serializers.Serializer):
    """
    Input serializer for POST /api/v1/platform/stores/.

    Creates Store + StoreSubscription + store_owner User atomically.
    """

    name = serializers.CharField(max_length=255)
    domain = serializers.CharField(max_length=253)
    tenant_type = serializers.ChoiceField(choices=TenantType.choices)
    currency = serializers.CharField(max_length=3, default="KES")
    country = serializers.CharField(max_length=2, default="KE")
    timezone = serializers.CharField(max_length=63, default="Africa/Nairobi")
    payment_methods = serializers.ListField(
        child=serializers.CharField(max_length=50),
        default=list,
        required=False,
    )
    owner_email = serializers.EmailField()

    def validate_domain(self, value):
        value = value.lower().strip()
        if Store.objects.filter(domain=value).exists():
            raise serializers.ValidationError(
                "A store with this domain already exists."
            )
        return value

    def validate_owner_email(self, value):
        value = value.lower().strip()
        return value

    def _generate_unique_slug(self, name):
        """Generate a unique slug from store name."""
        base_slug = slugify(name)[:90]
        slug = base_slug
        counter = 1
        while Store.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    def create(self, validated_data):
        owner_email = validated_data.pop("owner_email")
        slug = self._generate_unique_slug(validated_data["name"])

        with transaction.atomic():
            store = Store.objects.create(
                slug=slug,
                **validated_data,
            )

            StoreSubscription.objects.create(
                store=store,
                status="trial",
            )

            User.objects.create_user(
                email=owner_email,
                password=None,
                store=store,
                role=User.Role.STORE_OWNER,
            )

        return store


class StoreDetailSerializer(serializers.ModelSerializer):
    """Read-only serializer for store detail/list responses."""

    subscription_status = serializers.SerializerMethodField()

    class Meta:
        model = Store
        fields = [
            "id",
            "name",
            "slug",
            "domain",
            "tenant_type",
            "status",
            "currency",
            "country",
            "timezone",
            "payment_methods",
            "subscription_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_subscription_status(self, obj):
        sub = getattr(obj, "subscription", None)
        if sub is None:
            try:
                sub = obj.subscription
            except StoreSubscription.DoesNotExist:
                return None
        return sub.status


# Valid status transitions: (from_status, to_status)
VALID_STATUS_TRANSITIONS = {
    (StoreStatus.PENDING, StoreStatus.ACTIVE),
    (StoreStatus.ACTIVE, StoreStatus.SUSPENDED),
    (StoreStatus.SUSPENDED, StoreStatus.CANCELLED),
}


class StoreStatusSerializer(serializers.Serializer):
    """Validates and applies store status transitions."""

    status = serializers.ChoiceField(choices=StoreStatus.choices)

    def validate_status(self, value):
        store = self.context["store"]
        transition = (store.status, value)
        if transition not in VALID_STATUS_TRANSITIONS:
            raise serializers.ValidationError(
                {
                    "message": (f"Invalid transition: " f"{store.status} → {value}."),
                    "code": "INVALID_STATUS_TRANSITION",
                }
            )
        return value
