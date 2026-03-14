"""
Tests for Story 3.2 — Public Menu URL.

Covers:
- AC1: GET /api/v1/restaurant/public-menu/ is accessible without auth
- AC1: Out-of-schedule items are excluded
- Tenant isolation: only sections/items of the resolved store are returned
"""

from datetime import time
from unittest.mock import patch

import pytest
from rest_framework.test import APIRequestFactory

from apps.restaurant.tests.factories import (
    MenuItemFactory,
    MenuSectionFactory,
)
from apps.restaurant.views import PublicMenuView
from apps.store.tests.factories import StoreFactory


def _call_public_menu(store):
    factory = APIRequestFactory()
    request = factory.get("/api/v1/restaurant/public-menu/")
    # No force_authenticate — public endpoint
    request.store = store
    view = PublicMenuView.as_view()
    return view(request)


@pytest.mark.django_db
def test_public_menu_no_auth_required():
    """AC1: endpoint accessible without authentication."""
    store = StoreFactory()
    response = _call_public_menu(store)
    assert response.status_code == 200


@pytest.mark.django_db
def test_public_menu_returns_sections_with_items():
    """AC1: sections and their items are returned."""
    store = StoreFactory()
    section = MenuSectionFactory(store=store, name="Mains")
    MenuItemFactory(
        store=store, section=section, name="Ugali",
        available_from=None, available_until=None,
    )

    response = _call_public_menu(store)
    assert response.status_code == 200
    sections = response.data["data"]
    assert any(s["name"] == "Mains" for s in sections)
    mains = next(s for s in sections if s["name"] == "Mains")
    assert any(i["name"] == "Ugali" for i in mains["items"])


@pytest.mark.django_db
def test_public_menu_excludes_out_of_schedule_items():
    """AC1: items outside time window are excluded."""
    store = StoreFactory()
    section = MenuSectionFactory(store=store)
    MenuItemFactory(
        store=store, section=section, name="Breakfast",
        available_from=time(6, 0), available_until=time(11, 0),
    )

    with patch("apps.restaurant.views.timezone") as mock_tz:
        mock_tz.localtime.return_value.time.return_value = time(14, 0)
        response = _call_public_menu(store)

    sections = response.data["data"]
    all_items = [i for s in sections for i in s["items"]]
    assert not any(i["name"] == "Breakfast" for i in all_items)


@pytest.mark.django_db
def test_public_menu_includes_in_schedule_items():
    """AC1: items within time window are included."""
    store = StoreFactory()
    section = MenuSectionFactory(store=store)
    MenuItemFactory(
        store=store, section=section, name="Lunch Special",
        available_from=time(12, 0), available_until=time(15, 0),
    )

    with patch("apps.restaurant.views.timezone") as mock_tz:
        mock_tz.localtime.return_value.time.return_value = time(13, 0)
        response = _call_public_menu(store)

    sections = response.data["data"]
    all_items = [i for s in sections for i in s["items"]]
    assert any(i["name"] == "Lunch Special" for i in all_items)


@pytest.mark.django_db
def test_public_menu_tenant_isolation():
    """Only sections from the resolved store are returned."""
    store1 = StoreFactory()
    store2 = StoreFactory()
    MenuSectionFactory(store=store1, name="Store1 Section")
    MenuSectionFactory(store=store2, name="Store2 Section")

    response = _call_public_menu(store1)
    sections = response.data["data"]
    names = [s["name"] for s in sections]
    assert "Store1 Section" in names
    assert "Store2 Section" not in names


@pytest.mark.django_db
def test_public_menu_no_store_returns_404():
    """Missing store context returns 404."""
    factory = APIRequestFactory()
    request = factory.get("/api/v1/restaurant/public-menu/")
    request.store = None  # type: ignore[assignment]
    view = PublicMenuView.as_view()
    response = view(request)
    assert response.status_code == 404


@pytest.mark.django_db
def test_public_menu_includes_allergen_flag():
    """Allergen flag is included in public menu item response."""
    store = StoreFactory()
    section = MenuSectionFactory(store=store)
    MenuItemFactory(
        store=store, section=section, name="Peanut Stew",
        contains_allergens=True, allergen_description="Peanuts",
        available_from=None, available_until=None,
    )

    response = _call_public_menu(store)
    sections = response.data["data"]
    all_items = [i for s in sections for i in s["items"]]
    item = next(i for i in all_items if i["name"] == "Peanut Stew")
    assert item["contains_allergens"] is True
    assert item["allergen_description"] == "Peanuts"
