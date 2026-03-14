"""
Factory-boy factories for restaurant domain — Story 3.1, Story 3.4, Story 3.6.
"""

from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

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
from apps.store.tests.factories import StoreFactory


class MenuSectionFactory(DjangoModelFactory):
    class Meta:
        model = MenuSection

    store = factory.SubFactory(StoreFactory)
    name = factory.Sequence(lambda n: f"Section {n}")
    description = ""
    position = factory.Sequence(lambda n: n)


class MenuItemFactory(DjangoModelFactory):
    class Meta:
        model = MenuItem

    store = factory.SelfAttribute("section.store")
    section = factory.SubFactory(MenuSectionFactory)
    name = factory.Sequence(lambda n: f"Item {n}")
    description = ""
    price = "150.00"
    contains_allergens = False
    allergen_description = ""
    is_available = True
    available_from = None
    available_until = None
    position = factory.Sequence(lambda n: n)


class ModifierGroupFactory(DjangoModelFactory):
    class Meta:
        model = ModifierGroup

    store = factory.SelfAttribute("menu_item.store")
    menu_item = factory.SubFactory(MenuItemFactory)
    name = factory.Sequence(lambda n: f"Group {n}")
    min_selections = 0
    max_selections = 1
    is_required = False


class ModifierFactory(DjangoModelFactory):
    class Meta:
        model = Modifier

    store = factory.SelfAttribute("modifier_group.store")
    modifier_group = factory.SubFactory(ModifierGroupFactory)
    name = factory.Sequence(lambda n: f"Modifier {n}")
    price_addition = "0.00"
    is_available = True


class TableFactory(DjangoModelFactory):
    class Meta:
        model = Table

    store = factory.SubFactory(StoreFactory)
    number = factory.Sequence(lambda n: n + 1)
    name = ""
    capacity = 4
    is_active = True


class TableSessionFactory(DjangoModelFactory):
    class Meta:
        model = TableSession

    store = factory.SelfAttribute("table.store")
    table = factory.SubFactory(TableFactory)
    status = TableSession.STATUS_OPEN
    assigned_waiter = None
    closed_at = None


_DEFAULT_SNAPSHOT = [
    {
        "menu_item_id": "00000000-0000-0000-0000-000000000001",
        "name": "Nyama Choma",
        "price": "850.00",
        "quantity": 1,
        "contains_allergens": False,
        "modifiers": [],
    }
]


class DineInOrderFactory(DjangoModelFactory):
    class Meta:
        model = DineInOrder

    store = factory.SelfAttribute("session.store")
    session = factory.SubFactory(TableSessionFactory)
    status = DineInOrder.STATUS_PENDING
    items_snapshot = factory.LazyFunction(lambda: list(_DEFAULT_SNAPSHOT))
    total_amount = Decimal("850.00")


class KitchenTicketFactory(DjangoModelFactory):
    class Meta:
        model = KitchenTicket

    store = factory.SelfAttribute("order.store")
    order = factory.SubFactory(DineInOrderFactory)
    status = KitchenTicket.STATUS_PENDING
    items_snapshot = factory.LazyFunction(lambda: list(_DEFAULT_SNAPSHOT))
    waiter_name = "Test Waiter"
    table_number = 1
