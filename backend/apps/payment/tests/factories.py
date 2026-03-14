"""
factory-boy factories for payment domain.
"""

import uuid
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from apps.payment.models import MpesaTransaction, MpesaTransactionStatus
from apps.store.tests.factories import StoreFactory


class MpesaTransactionFactory(DjangoModelFactory):
    class Meta:
        model = MpesaTransaction

    store = factory.SubFactory(StoreFactory)
    reference = factory.LazyAttribute(lambda o: f"test-ref-{uuid.uuid4().hex[:8]}")
    phone = "+254700000000"
    amount = Decimal("500.00")
    status = MpesaTransactionStatus.CONFIRMED
    checkout_request_id = factory.LazyAttribute(lambda o: f"ws_CO_{uuid.uuid4().hex[:16]}")
    mpesa_receipt_number = None
    merchant_request_id = factory.LazyAttribute(lambda o: f"MR-{uuid.uuid4().hex[:8]}")
