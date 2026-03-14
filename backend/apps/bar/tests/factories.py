"""
Factory-boy factories for bar domain.
"""

from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from apps.bar.models import AgeRestrictionLog, HappyHour, Tab, TabItem, TabRound, TabShare
from apps.restaurant.tests.factories import MenuItemFactory
from apps.store.tests.factories import StoreFactory


class TabFactory(DjangoModelFactory):
    class Meta:
        model = Tab

    store = factory.SubFactory(StoreFactory)
    customer = None
    customer_name = factory.Sequence(lambda n: f"Customer {n}")
    status = Tab.STATUS_OPEN


class TabRoundFactory(DjangoModelFactory):
    class Meta:
        model = TabRound

    store = factory.SelfAttribute("tab.store")
    tab = factory.SubFactory(TabFactory)
    round_number = 1


class TabItemFactory(DjangoModelFactory):
    class Meta:
        model = TabItem

    store = factory.SelfAttribute("tab.store")
    tab = factory.SubFactory(TabFactory)
    round = factory.SubFactory(TabRoundFactory, tab=factory.SelfAttribute("..tab"))
    menu_item = factory.SubFactory(MenuItemFactory, store=factory.SelfAttribute("..store"))
    name = factory.Sequence(lambda n: f"Item {n}")
    unit_price = Decimal("200.00")
    quantity = 1
    is_happy_hour = False


class HappyHourFactory(DjangoModelFactory):
    class Meta:
        model = HappyHour

    store = factory.SubFactory(StoreFactory)
    name = "Happy Hour"
    start_time = "17:00"
    end_time = "19:00"
    discount_percent = Decimal("20.00")
    days_of_week = []
    is_active = True


class TabShareFactory(DjangoModelFactory):
    class Meta:
        model = TabShare

    store = factory.SelfAttribute("tab.store")
    tab = factory.SubFactory(TabFactory)
    payer_phone = "+254700000001"
    amount = Decimal("500.00")
    status = TabShare.STATUS_PENDING
    payment_transaction = None
