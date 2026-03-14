"""
factory-boy factories for store domain.
"""

import uuid

import factory
from factory.django import DjangoModelFactory

from apps.store.models import Store, TenantType


class StoreFactory(DjangoModelFactory):
    class Meta:
        model = Store

    name = factory.Sequence(lambda n: f"Test Store {n}")
    slug = factory.LazyAttribute(lambda o: f"store-{uuid.uuid4().hex[:8]}")
    domain = factory.LazyAttribute(lambda o: f"{o.slug}.joat.com")
    country = "KE"
    tenant_type = TenantType.RESTAURANT
