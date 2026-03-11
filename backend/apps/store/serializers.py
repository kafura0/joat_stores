"""
Store serializers for platform admin endpoints.

StoreProvisionSerializer — validates and creates a store atomically.
StoreListSerializer      — read-only list representation.
StoreStatusSerializer    — validates status transitions.
BrandingSerializer       — public read-only branding response (Story 1.7).

Implementation: Story 1.4, Story 1.7
"""

from django.db import transaction
from django.utils.text import slugify

from rest_framework import serializers

from apps.saas.models import StoreSubscription
from apps.store.models import Store, StoreSettings, StoreStatus, StoreTheme, TenantType
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

        with transaction.atomic():
            # Slug generation inside transaction — prevents race where two concurrent
            # requests generate the same slug and one gets IntegrityError 500.
            slug = self._generate_unique_slug(validated_data["name"])
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
        try:
            return obj.subscription.status
        except StoreSubscription.DoesNotExist:
            return None


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


class BrandingSerializer(serializers.Serializer):
    """
    Public read-only branding response for GET /api/v1/store/branding/.

    Combines Store + StoreSettings + StoreTheme into a single flat payload.
    No auth required — used by storefront SSR to inject tenant CSS variables.

    Implementation: Story 1.7
    """

    store_name = serializers.CharField(source="name")
    logo_url = serializers.SerializerMethodField()
    tagline = serializers.SerializerMethodField()
    primary_color = serializers.SerializerMethodField()
    secondary_color = serializers.SerializerMethodField()
    font_family = serializers.SerializerMethodField()
    currency = serializers.CharField()
    country = serializers.CharField()
    status = serializers.CharField()

    def _get_settings(self, obj):
        settings_obj, _ = StoreSettings.objects.get_or_create(store=obj)
        return settings_obj

    def _get_theme(self, obj):
        theme, _ = StoreTheme.objects.get_or_create(store=obj)
        return theme

    def get_logo_url(self, obj):
        return self._get_settings(obj).logo_url

    def get_tagline(self, obj):
        return self._get_settings(obj).tagline

    def get_primary_color(self, obj):
        return self._get_theme(obj).primary_color

    def get_secondary_color(self, obj):
        return self._get_theme(obj).secondary_color

    def get_font_family(self, obj):
        return self._get_theme(obj).font_family
