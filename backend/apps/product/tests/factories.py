"""
factory-boy factories for product catalog — Story 4.1.
"""

from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from apps.product.models import Category, Product, ProductImage, Variant
from apps.store.tests.factories import StoreFactory


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category

    store = factory.SubFactory(StoreFactory)
    name = factory.Sequence(lambda n: f"Category {n}")
    description = ""
    parent = None
    position = factory.Sequence(lambda n: n)


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    store = factory.SubFactory(StoreFactory)
    category = None
    name = factory.Sequence(lambda n: f"Product {n}")
    description = ""
    attribute_names = factory.LazyFunction(lambda: ["Size", "Colour"])
    is_available = True


class VariantFactory(DjangoModelFactory):
    class Meta:
        model = Variant

    store = factory.SelfAttribute("product.store")
    product = factory.SubFactory(ProductFactory)
    attribute_values = factory.LazyFunction(lambda: {"Size": "M", "Colour": "Black"})
    price = Decimal("1500.00")
    inventory_count = 10
    is_available = True
    sku = ""
