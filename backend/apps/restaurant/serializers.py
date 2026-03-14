"""
Restaurant serializers — Story 3.1 (Menu Management API).
"""

from rest_framework import serializers

from apps.restaurant.models import MenuItem, MenuSection, Modifier, ModifierGroup


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
