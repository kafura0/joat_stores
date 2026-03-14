"""
factory-boy factories for order domain — Stories 4.2, 4.3, 4.4.
"""

from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from apps.order.models import Order, OrderStatus
from apps.store.tests.factories import StoreFactory


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = Order

    store = factory.SubFactory(StoreFactory)
    customer_phone = "+254712000001"
    customer_name = "Test Customer"
    customer_email = "customer@test.com"
    delivery_address = None
    items_snapshot = factory.LazyFunction(lambda: [
        {
            "variant_id": "00000000-0000-0000-0000-000000000001",
            "product_id": "00000000-0000-0000-0000-000000000002",
            "quantity": 1,
            "price": "1500.00",
            "line_total": "1500.00",
        }
    ])
    total_amount = Decimal("1500.00")
    status = OrderStatus.PENDING
    payment_transaction = None
    customer = None
