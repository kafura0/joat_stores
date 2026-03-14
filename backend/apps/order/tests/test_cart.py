"""
Tests for Story 4.2 — Redis Cart (30-Day TTL, Guest + Auth).

Covers:
- AC1: Cart persisted in Redis with 30-day TTL
- AC2: Cart restored on return visit
- AC3: Guest cart merged into user cart on login
- AC4: Cart written to PostgreSQL before STK Push
- AC5: Two variants of same product = two separate line items
"""

from unittest.mock import MagicMock, patch

import pytest

from apps.order import cart as cart_service
from apps.store.tests.factories import StoreFactory


@pytest.fixture
def store():
    return StoreFactory()


# ---------------------------------------------------------------------------
# AC1 + AC2 — Persist + restore cart
# ---------------------------------------------------------------------------

def test_cart_add_and_get(store):
    """Cart add → get returns same items."""
    with patch("apps.order.cart._get_redis") as mock_redis:
        r = MagicMock()
        stored = {}
        r.setex.side_effect = lambda k, ttl, v: stored.update({k: v})
        r.get.side_effect = lambda k: stored.get(k)
        mock_redis.return_value = r

        cart_service.add_to_cart(str(store.id), "guest-001", "prod-1", "var-1", 2)
        items = cart_service.get_cart(str(store.id), "guest-001")

    assert len(items) == 1
    assert items[0]["variant_id"] == "var-1"
    assert items[0]["quantity"] == 2


def test_cart_add_refreshes_ttl(store):
    """Every write calls setex with CART_TTL_SECONDS."""
    with patch("apps.order.cart._get_redis") as mock_redis:
        r = MagicMock()
        r.get.return_value = None
        mock_redis.return_value = r

        cart_service.add_to_cart(str(store.id), "guest-001", "prod-1", "var-1", 1)

    r.setex.assert_called_once()
    _, ttl, _ = r.setex.call_args[0]
    assert ttl == cart_service.CART_TTL_SECONDS


def test_cart_get_returns_empty_when_missing(store):
    with patch("apps.order.cart._get_redis") as mock_redis:
        r = MagicMock()
        r.get.return_value = None
        mock_redis.return_value = r

        items = cart_service.get_cart(str(store.id), "unknown-ref")
    assert items == []


# ---------------------------------------------------------------------------
# AC5 — Two variants of same product = two line items
# ---------------------------------------------------------------------------

def test_two_variants_are_separate_line_items(store):
    with patch("apps.order.cart._get_redis") as mock_redis:
        stored = {}
        r = MagicMock()
        r.setex.side_effect = lambda k, ttl, v: stored.update({k: v})
        r.get.side_effect = lambda k: stored.get(k)
        mock_redis.return_value = r

        cart_service.add_to_cart(str(store.id), "cart-x", "prod-1", "var-M-Red", 1)
        cart_service.add_to_cart(str(store.id), "cart-x", "prod-1", "var-L-Red", 1)
        items = cart_service.get_cart(str(store.id), "cart-x")

    assert len(items) == 2
    variant_ids = {i["variant_id"] for i in items}
    assert variant_ids == {"var-M-Red", "var-L-Red"}


def test_same_variant_increments_quantity(store):
    with patch("apps.order.cart._get_redis") as mock_redis:
        stored = {}
        r = MagicMock()
        r.setex.side_effect = lambda k, ttl, v: stored.update({k: v})
        r.get.side_effect = lambda k: stored.get(k)
        mock_redis.return_value = r

        cart_service.add_to_cart(str(store.id), "cart-y", "prod-1", "var-M", 1)
        cart_service.add_to_cart(str(store.id), "cart-y", "prod-1", "var-M", 2)
        items = cart_service.get_cart(str(store.id), "cart-y")

    assert len(items) == 1
    assert items[0]["quantity"] == 3


# ---------------------------------------------------------------------------
# AC3 — Guest cart merged into user cart
# ---------------------------------------------------------------------------

def test_merge_carts_combines_items(store):
    import json

    with patch("apps.order.cart._get_redis") as mock_redis:
        stored = {}
        r = MagicMock()
        r.setex.side_effect = lambda k, ttl, v: stored.update({k: v})
        r.get.side_effect = lambda k: stored.get(k)
        r.delete.side_effect = lambda k: stored.pop(k, None)
        mock_redis.return_value = r

        # Set up guest cart
        stored[f"cart:{store.id}:guest-abc"] = json.dumps([
            {"product_id": "p1", "variant_id": "v1", "quantity": 1}
        ])
        # Set up user cart
        stored[f"cart:{store.id}:user-123"] = json.dumps([
            {"product_id": "p2", "variant_id": "v2", "quantity": 2}
        ])

        merged = cart_service.merge_carts(str(store.id), "guest-abc", "user-123")

    assert len(merged) == 2
    # Guest key deleted
    r.delete.assert_called_once()


# ---------------------------------------------------------------------------
# AC4 — Cart snapshot written to PostgreSQL
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_write_cart_snapshot(store):
    from apps.order.models import CartSnapshot

    items = [{"product_id": "p1", "variant_id": "v1", "quantity": 1}]
    snapshot = cart_service.write_cart_snapshot(store, "cart-ref-001", items)

    assert snapshot.cart_key == "cart-ref-001"
    assert snapshot.items == items
    assert CartSnapshot.objects.filter(store=store, cart_key="cart-ref-001").exists()


@pytest.mark.django_db
def test_write_cart_snapshot_is_idempotent(store):
    """Calling twice for same cart_ref updates rather than duplicates."""
    from apps.order.models import CartSnapshot

    items1 = [{"product_id": "p1", "variant_id": "v1", "quantity": 1}]
    items2 = [{"product_id": "p1", "variant_id": "v1", "quantity": 3}]

    cart_service.write_cart_snapshot(store, "idem-ref", items1)
    cart_service.write_cart_snapshot(store, "idem-ref", items2)

    assert CartSnapshot.objects.filter(store=store, cart_key="idem-ref").count() == 1
    snap = CartSnapshot.objects.get(store=store, cart_key="idem-ref")
    assert snap.items[0]["quantity"] == 3
