"""
Restaurant domain models — Story 3.1 (Menu Management API).

Models:
  MenuSection  — ordered grouping of MenuItems (e.g. "Starters", "Mains")
  MenuItem     — individual dish with price, allergen flag, time-based availability
  ModifierGroup — a set of options for a MenuItem (e.g. "Choose sauce"), with
                   min/max selection rules
  Modifier      — individual option within a ModifierGroup, with optional price addition

All models inherit TenantModel (UUID PK, store FK, soft-delete, TenantQuerySet).
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from core.models import TenantModel


class MenuSection(TenantModel):
    """Ordered grouping of MenuItems within a store's menu."""

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    position = models.PositiveSmallIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ["position", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["store", "name"],
                name="uq_restaurant_menusection_store_name",
            )
        ]
        indexes = [
            models.Index(
                fields=["store", "position"],
                name="idx_rst_msection_store_pos",
            )
        ]

    def __str__(self) -> str:
        return self.name


class MenuItem(TenantModel):
    """Individual dish with price, allergen flag, and time-based availability."""

    section = models.ForeignKey(
        MenuSection,
        on_delete=models.CASCADE,
        related_name="items",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    contains_allergens = models.BooleanField(default=False)
    allergen_description = models.TextField(blank=True, default="")
    is_available = models.BooleanField(default=True)

    # Time-based scheduling — null means always available
    available_from = models.TimeField(
        null=True,
        blank=True,
        help_text="Start time for availability window (e.g. 06:00). Null = always.",
    )
    available_until = models.TimeField(
        null=True,
        blank=True,
        help_text="End time for availability window (e.g. 11:00). Null = always.",
    )

    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "name"]
        indexes = [
            models.Index(
                fields=["store", "section"],
                name="idx_rst_mitem_store_section",
            ),
            models.Index(
                fields=["store", "is_available"],
                name="idx_rst_mitem_store_avail",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def is_available_now(self, current_time=None) -> bool:
        """Return True if the item is available at current_time (or right now)."""
        if not self.is_available:
            return False
        if self.available_from is None and self.available_until is None:
            return True
        if current_time is None:
            from django.utils import timezone

            current_time = timezone.localtime().time()
        if self.available_from and self.available_until:
            return self.available_from <= current_time <= self.available_until
        if self.available_from:
            return current_time >= self.available_from
        if self.available_until:
            return current_time <= self.available_until
        return True


class ModifierGroup(TenantModel):
    """A set of options for a MenuItem (e.g. "Choose sauce")."""

    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name="modifier_groups",
    )
    name = models.CharField(max_length=100)
    min_selections = models.PositiveSmallIntegerField(
        default=0,
        help_text="Minimum number of modifiers the customer must choose.",
    )
    max_selections = models.PositiveSmallIntegerField(
        default=1,
        help_text="Maximum number of modifiers the customer may choose.",
    )
    is_required = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(
                fields=["store", "menu_item"],
                name="idx_rst_modgrp_store_item",
            )
        ]

    def __str__(self) -> str:
        return f"{self.menu_item.name} — {self.name}"


class Modifier(TenantModel):
    """Individual option within a ModifierGroup, with optional price addition."""

    modifier_group = models.ForeignKey(
        ModifierGroup,
        on_delete=models.CASCADE,
        related_name="modifiers",
    )
    name = models.CharField(max_length=100)
    price_addition = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default="0.00",
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Additional cost when this modifier is selected.",
    )
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(
                fields=["store", "modifier_group"],
                name="idx_rst_modifier_store_grp",
            )
        ]

    def __str__(self) -> str:
        return self.name
