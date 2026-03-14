"""
Restaurant serializers — Story 3.1, 3.4, 3.6.
"""

from decimal import Decimal

from rest_framework import serializers

from apps.restaurant.models import (
    DineInOrder,
    KitchenTicket,
    MenuItem,
    MenuSection,
    Modifier,
    ModifierGroup,
    Table,
    TableSession,
)


class ModifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modifier
        fields = [
            "id",
            "modifier_group",
            "name",
            "price_addition",
            "is_available",
        ]
        read_only_fields = ["id"]


class ModifierGroupSerializer(serializers.ModelSerializer):
    modifiers = ModifierSerializer(many=True, read_only=True)

    class Meta:
        model = ModifierGroup
        fields = [
            "id",
            "menu_item",
            "name",
            "min_selections",
            "max_selections",
            "is_required",
            "modifiers",
        ]
        read_only_fields = ["id"]


class MenuItemSerializer(serializers.ModelSerializer):
    modifier_groups = ModifierGroupSerializer(many=True, read_only=True)

    class Meta:
        model = MenuItem
        fields = [
            "id",
            "section",
            "name",
            "description",
            "price",
            "contains_allergens",
            "allergen_description",
            "is_available",
            "available_from",
            "available_until",
            "position",
            "modifier_groups",
        ]
        read_only_fields = ["id"]


class MenuSectionSerializer(serializers.ModelSerializer):
    items = MenuItemSerializer(many=True, read_only=True)

    class Meta:
        model = MenuSection
        fields = [
            "id",
            "name",
            "description",
            "position",
            "items",
        ]
        read_only_fields = ["id"]


class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = [
            "id",
            "number",
            "name",
            "capacity",
            "is_active",
        ]
        read_only_fields = ["id"]


class TableSessionSerializer(serializers.ModelSerializer):
    table_number = serializers.IntegerField(source="table.number", read_only=True)
    assigned_waiter_name = serializers.SerializerMethodField()

    class Meta:
        model = TableSession
        fields = [
            "id",
            "table",
            "table_number",
            "status",
            "assigned_waiter",
            "assigned_waiter_name",
            "opened_at",
            "closed_at",
        ]
        read_only_fields = [
            "id",
            "table_number",
            "status",
            "assigned_waiter_name",
            "opened_at",
            "closed_at",
        ]

    def get_assigned_waiter_name(self, obj) -> str | None:
        if obj.assigned_waiter_id is None:
            return None
        user = obj.assigned_waiter
        return user.get_full_name() or user.email


# ---------------------------------------------------------------------------
# Story 3.6 — DineInOrder + KitchenTicket
# ---------------------------------------------------------------------------


class OrderItemInputSerializer(serializers.Serializer):
    """Validates a single line item in a dine-in order request."""

    menu_item_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=99)
    selected_modifier_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=True,
        default=list,
    )


class DineInOrderCreateSerializer(serializers.Serializer):
    """Input serializer for POST /api/v1/restaurant/orders/."""

    session_id = serializers.UUIDField()
    items = serializers.ListField(
        child=OrderItemInputSerializer(),
        min_length=1,
    )

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required.")
        return value


class DineInOrderSerializer(serializers.ModelSerializer):
    """Output serializer for DineInOrder."""

    ticket_status = serializers.SerializerMethodField()

    class Meta:
        model = DineInOrder
        fields = [
            "id",
            "session",
            "status",
            "items_snapshot",
            "total_amount",
            "placed_at",
            "ticket_status",
        ]
        read_only_fields = fields

    def get_ticket_status(self, obj) -> str | None:
        # Access via reverse OneToOne — may not be prefetched in all contexts
        try:
            return obj.ticket.status
        except KitchenTicket.DoesNotExist:
            return None


class KitchenTicketSerializer(serializers.ModelSerializer):
    """Output serializer for kitchen display endpoint."""

    class Meta:
        model = KitchenTicket
        fields = [
            "id",
            "order",
            "status",
            "items_snapshot",
            "waiter_name",
            "table_number",
            "created_at",
        ]
        read_only_fields = fields
