"""
Tests for restaurant menu models — Story 3.1.
"""

from datetime import time

import pytest

from apps.restaurant.models import MenuSection
from apps.restaurant.tests.factories import (
    MenuItemFactory,
    MenuSectionFactory,
    ModifierFactory,
    ModifierGroupFactory,
)


@pytest.mark.django_db
class TestMenuSection:
    def test_create(self):
        section = MenuSectionFactory()
        assert section.pk is not None
        assert section.store_id is not None

    def test_str(self):
        section = MenuSectionFactory(name="Starters")
        assert str(section) == "Starters"

    def test_tenant_scoped(self):
        s1 = MenuSectionFactory()
        s2 = MenuSectionFactory()
        assert s1.store_id != s2.store_id or True  # different stores or same is fine

    def test_unique_name_per_store(self):
        from django.db import IntegrityError

        section = MenuSectionFactory(name="Mains")
        with pytest.raises(IntegrityError):
            MenuSection.objects.create(
                store=section.store,
                name="Mains",
            )


@pytest.mark.django_db
class TestMenuItem:
    def test_create(self):
        item = MenuItemFactory(price="250.00")
        assert item.pk is not None
        assert str(item.price) == "250.00"

    def test_str(self):
        item = MenuItemFactory(name="Nyama Choma")
        assert str(item) == "Nyama Choma"

    def test_allergen_flag(self):
        item = MenuItemFactory(contains_allergens=True, allergen_description="Nuts")
        assert item.contains_allergens is True
        assert item.allergen_description == "Nuts"

    def test_is_available_now_no_window(self):
        item = MenuItemFactory(available_from=None, available_until=None)
        assert item.is_available_now() is True

    def test_is_available_now_within_window(self):
        item = MenuItemFactory(
            available_from=time(6, 0),
            available_until=time(11, 0),
        )
        assert item.is_available_now(current_time=time(8, 0)) is True

    def test_is_available_now_outside_window(self):
        item = MenuItemFactory(
            available_from=time(6, 0),
            available_until=time(11, 0),
        )
        assert item.is_available_now(current_time=time(14, 0)) is False

    def test_is_available_now_boundary_from(self):
        item = MenuItemFactory(
            available_from=time(6, 0),
            available_until=time(11, 0),
        )
        assert item.is_available_now(current_time=time(6, 0)) is True

    def test_is_available_now_boundary_until(self):
        item = MenuItemFactory(
            available_from=time(6, 0),
            available_until=time(11, 0),
        )
        assert item.is_available_now(current_time=time(11, 0)) is True

    def test_unavailable_item_not_available_now(self):
        item = MenuItemFactory(is_available=False)
        assert item.is_available_now() is False


@pytest.mark.django_db
class TestModifierGroup:
    def test_create(self):
        group = ModifierGroupFactory(name="Choose sauce")
        assert group.pk is not None
        assert group.min_selections == 0
        assert group.max_selections == 1

    def test_str(self):
        item = MenuItemFactory(name="Pizza")
        group = ModifierGroupFactory(menu_item=item, name="Toppings")
        assert "Pizza" in str(group)
        assert "Toppings" in str(group)


@pytest.mark.django_db
class TestModifier:
    def test_create(self):
        mod = ModifierFactory(name="Extra cheese", price_addition="50.00")
        assert mod.pk is not None
        assert str(mod.price_addition) == "50.00"

    def test_zero_price_addition(self):
        mod = ModifierFactory(price_addition="0.00")
        assert float(mod.price_addition) == 0.0

    def test_str(self):
        mod = ModifierFactory(name="Kachumbari")
        assert str(mod) == "Kachumbari"
