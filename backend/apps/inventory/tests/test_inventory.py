"""
Tests for inventory app — Story 4.1 low-stock alerts.

Covers:
  - check_low_stock Celery task dispatches alerts for low-stock variants
  - check_low_stock respects StoreSettings.low_stock_threshold
  - check_low_stock handles missing store gracefully
  - check_low_stock handles no low-stock variants (zero alerts dispatched)
"""

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.store.models import TenantType
from apps.store.tests.factories import StoreFactory


@pytest.fixture
def store():
    return StoreFactory(tenant_type=TenantType.RETAIL)


@pytest.fixture
def product(store):
    from apps.product.models import Product

    return Product.objects.create(store=store, name="Test Product")


@pytest.mark.django_db
class TestCheckLowStockTask:
    """Tests for the check_low_stock Celery task."""

    @patch("apps.product.tasks.send_low_stock_alert")
    def test_dispatches_alerts_for_low_stock_variants(self, mock_alert, store, product):
        from apps.inventory.tasks import check_low_stock
        from apps.product.models import Variant

        Variant.objects.create(
            store=store,
            product=product,
            attribute_values={"Size": "S"},
            price=Decimal("9.99"),
            inventory_count=2,
            is_available=True,
        )
        Variant.objects.create(
            store=store,
            product=product,
            attribute_values={"Size": "L"},
            price=Decimal("29.99"),
            inventory_count=20,
            is_available=True,
        )

        check_low_stock(str(store.id))

        assert mock_alert.delay.call_count == 1

    @patch("apps.product.tasks.send_low_stock_alert")
    def test_respects_custom_threshold(self, mock_alert, store, product):
        from apps.inventory.tasks import check_low_stock
        from apps.product.models import Variant
        from apps.store.models import StoreSettings

        StoreSettings.objects.create(store=store, low_stock_threshold=15)

        Variant.objects.create(
            store=store,
            product=product,
            attribute_values={"Size": "S"},
            price=Decimal("9.99"),
            inventory_count=12,
            is_available=True,
        )

        check_low_stock(str(store.id))

        assert mock_alert.delay.call_count == 1

    @patch("apps.product.tasks.send_low_stock_alert")
    def test_no_alerts_when_stock_ok(self, mock_alert, store, product):
        from apps.inventory.tasks import check_low_stock
        from apps.product.models import Variant

        Variant.objects.create(
            store=store,
            product=product,
            attribute_values={"Size": "S"},
            price=Decimal("9.99"),
            inventory_count=50,
            is_available=True,
        )

        check_low_stock(str(store.id))

        mock_alert.delay.assert_not_called()

    @patch("apps.product.tasks.send_low_stock_alert")
    def test_ignores_unavailable_variants(self, mock_alert, store, product):
        from apps.inventory.tasks import check_low_stock
        from apps.product.models import Variant

        Variant.objects.create(
            store=store,
            product=product,
            attribute_values={"Size": "S"},
            price=Decimal("9.99"),
            inventory_count=1,
            is_available=False,
        )

        check_low_stock(str(store.id))

        mock_alert.delay.assert_not_called()

    def test_handles_missing_store(self):
        from apps.inventory.tasks import check_low_stock

        fake_id = str(uuid.uuid4())

        with pytest.raises(Exception):
            check_low_stock(fake_id)

    @patch("apps.product.tasks.send_low_stock_alert")
    def test_max_50_variants(self, mock_alert, store, product):
        from apps.inventory.tasks import check_low_stock
        from apps.product.models import Variant

        for i in range(55):
            Variant.objects.create(
                store=store,
                product=product,
                attribute_values={"Index": str(i)},
                price=Decimal("1.00"),
                inventory_count=1,
                is_available=True,
            )

        check_low_stock(str(store.id))

        assert mock_alert.delay.call_count == 50
