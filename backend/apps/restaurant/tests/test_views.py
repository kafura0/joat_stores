"""
Tests for restaurant menu views — Story 3.1.

Covers:
- AC1: CRUD for MenuSection, MenuItem, ModifierGroup, Modifier
- AC2: Time-based availability filtering on menu-items list
- AC3: Allergen flag in response
- AC4: Modifier price_addition in response
- AC5: Tenant isolation
"""

from datetime import time
from unittest.mock import patch

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.restaurant.models import MenuSection, Modifier, ModifierGroup
from apps.restaurant.tests.factories import (
    MenuItemFactory,
    MenuSectionFactory,
    ModifierFactory,
    ModifierGroupFactory,
)
from apps.restaurant.views import (
    MenuItemViewSet,
    MenuSectionViewSet,
    ModifierGroupViewSet,
    ModifierViewSet,
)
from apps.store.tests.factories import StoreFactory
from apps.users.tests.factories import UserFactory


def _get_list(viewset_class, store, user, basename):
    factory = APIRequestFactory()
    request = factory.get(f"/api/v1/restaurant/{basename}/")
    force_authenticate(request, user=user)
    request.store = store
    view = viewset_class.as_view({"get": "list"})
    return view(request)


def _post(viewset_class, store, user, basename, data):
    factory = APIRequestFactory()
    request = factory.post(
        f"/api/v1/restaurant/{basename}/", data=data, format="json"
    )
    force_authenticate(request, user=user)
    request.store = store
    view = viewset_class.as_view({"post": "create"})
    return view(request)


# ---------------------------------------------------------------------------
# MenuSection
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_menu_section_list():
    store = StoreFactory()
    user = UserFactory()
    MenuSectionFactory(store=store, name="Starters")
    MenuSectionFactory(store=store, name="Mains")

    response = _get_list(MenuSectionViewSet, store, user, "menu-sections")
    assert response.status_code == 200
    names = [r["name"] for r in response.data["data"]]
    assert "Starters" in names
    assert "Mains" in names


@pytest.mark.django_db
def test_menu_section_create():
    store = StoreFactory()
    user = UserFactory()
    response = _post(
        MenuSectionViewSet,
        store,
        user,
        "menu-sections",
        {"name": "Drinks", "description": "", "position": 0},
    )
    assert response.status_code == 201
    assert MenuSection.objects.filter(store=store, name="Drinks").exists()


@pytest.mark.django_db
def test_menu_section_tenant_isolation():
    store1 = StoreFactory()
    store2 = StoreFactory()
    user = UserFactory()
    MenuSectionFactory(store=store1, name="Store1 Section")
    MenuSectionFactory(store=store2, name="Store2 Section")

    response = _get_list(MenuSectionViewSet, store1, user, "menu-sections")
    names = [r["name"] for r in response.data["data"]]
    assert "Store1 Section" in names
    assert "Store2 Section" not in names


# ---------------------------------------------------------------------------
# MenuItem — time-based filtering
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_menu_item_list_no_time_window():
    """Items with no window always appear."""
    store = StoreFactory()
    user = UserFactory()
    section = MenuSectionFactory(store=store)
    MenuItemFactory(
        store=store, section=section, name="Ugali",
        available_from=None, available_until=None,
    )

    with patch("apps.restaurant.views.timezone") as mock_tz:
        mock_tz.localtime.return_value.time.return_value = time(15, 0)
        response = _get_list(MenuItemViewSet, store, user, "menu-items")

    assert response.status_code == 200
    names = [r["name"] for r in response.data["data"]]
    assert "Ugali" in names


@pytest.mark.django_db
def test_menu_item_list_within_window():
    """Items within their time window are included."""
    store = StoreFactory()
    user = UserFactory()
    section = MenuSectionFactory(store=store)
    MenuItemFactory(
        store=store,
        section=section,
        name="Breakfast",
        available_from=time(6, 0),
        available_until=time(11, 0),
    )

    with patch("apps.restaurant.views.timezone") as mock_tz:
        mock_tz.localtime.return_value.time.return_value = time(8, 0)
        response = _get_list(MenuItemViewSet, store, user, "menu-items")

    names = [r["name"] for r in response.data["data"]]
    assert "Breakfast" in names


@pytest.mark.django_db
def test_menu_item_list_outside_window():
    """Items outside their time window are excluded."""
    store = StoreFactory()
    user = UserFactory()
    section = MenuSectionFactory(store=store)
    MenuItemFactory(
        store=store,
        section=section,
        name="Breakfast",
        available_from=time(6, 0),
        available_until=time(11, 0),
    )

    with patch("apps.restaurant.views.timezone") as mock_tz:
        mock_tz.localtime.return_value.time.return_value = time(14, 0)
        response = _get_list(MenuItemViewSet, store, user, "menu-items")

    names = [r["name"] for r in response.data["data"]]
    assert "Breakfast" not in names


# ---------------------------------------------------------------------------
# Allergen flag
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_menu_item_allergen_flag_in_response():
    """AC3: allergen flag and description included in response."""
    store = StoreFactory()
    user = UserFactory()
    section = MenuSectionFactory(store=store)
    MenuItemFactory(
        store=store,
        section=section,
        name="Peanut Soup",
        contains_allergens=True,
        allergen_description="Contains peanuts",
        available_from=None,
        available_until=None,
    )

    with patch("apps.restaurant.views.timezone") as mock_tz:
        mock_tz.localtime.return_value.time.return_value = time(12, 0)
        response = _get_list(MenuItemViewSet, store, user, "menu-items")

    item = next(r for r in response.data["data"] if r["name"] == "Peanut Soup")
    assert item["contains_allergens"] is True
    assert item["allergen_description"] == "Contains peanuts"


# ---------------------------------------------------------------------------
# Modifier price_addition
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_modifier_price_addition_in_response():
    """AC4: modifier price_addition in response."""
    store = StoreFactory()
    user = UserFactory()
    group = ModifierGroupFactory(store=store)
    ModifierFactory(
        store=store, modifier_group=group, name="Extra cheese", price_addition="50.00"
    )

    response = _get_list(ModifierViewSet, store, user, "modifiers")
    mod = next(r for r in response.data["data"] if r["name"] == "Extra cheese")
    assert mod["price_addition"] == "50.00"


# ---------------------------------------------------------------------------
# ModifierGroup + Modifier CRUD
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_modifier_group_create():
    store = StoreFactory()
    user = UserFactory()
    item = MenuItemFactory(store=store)
    response = _post(
        ModifierGroupViewSet,
        store,
        user,
        "modifier-groups",
        {
            "menu_item": str(item.id),
            "name": "Choose sauce",
            "min_selections": 0,
            "max_selections": 2,
            "is_required": False,
        },
    )
    assert response.status_code == 201
    assert ModifierGroup.objects.filter(store=store, name="Choose sauce").exists()


@pytest.mark.django_db
def test_modifier_create():
    store = StoreFactory()
    user = UserFactory()
    group = ModifierGroupFactory(store=store)
    response = _post(
        ModifierViewSet,
        store,
        user,
        "modifiers",
        {
            "modifier_group": str(group.id),
            "name": "Kachumbari",
            "price_addition": "0.00",
            "is_available": True,
        },
    )
    assert response.status_code == 201
    assert Modifier.objects.filter(store=store, name="Kachumbari").exists()
