"""
Redis-backed cart service — Story 4.2.

Design:
- Cart key:  "cart:{store_id}:{cart_key}"  where cart_key is either
  an anonymous session ID (from cookie) or the authenticated user's ID.
- TTL: 30 days (refreshed on every write operation).
- Items stored as a JSON list: [{"product_id": ..., "variant_id": ..., "quantity": N}]
- Guest→auth merge: when a user logs in, guest cart is merged into user cart
  and the guest Redis key is deleted.
- Safety-net: write_cart_snapshot() persists to PostgreSQL before STK Push.

Fallback (Story 4.2 AC): if Redis is unavailable the cart operations raise
CartServiceError — callers should fall back to sessionStorage (frontend) or
return a 503 (API).
"""

import json
import uuid
from typing import Any

import structlog

log = structlog.get_logger(__name__)

# Cart TTL: 30 days in seconds
CART_TTL_SECONDS = 30 * 24 * 60 * 60

# Redis key prefix
_PREFIX = "cart"


class CartServiceError(Exception):
    """Raised when Redis is unavailable."""


def _cart_key(store_id: str, cart_ref: str) -> str:
    return f"{_PREFIX}:{store_id}:{cart_ref}"


def _get_redis():
    from django_redis import get_redis_connection

    return get_redis_connection("default")


def get_cart(store_id: str, cart_ref: str) -> list[dict]:
    """
    Return cart items for the given store + cart_ref.
    Returns [] if cart does not exist or Redis is unavailable.
    """
    try:
        r = _get_redis()
        raw = r.get(_cart_key(store_id, cart_ref))
        if raw is None:
            return []
        return json.loads(raw)
    except Exception as exc:
        log.warning("cart_get_failed", cart_ref=cart_ref, error=str(exc))
        return []


def set_cart(store_id: str, cart_ref: str, items: list[dict]) -> None:
    """
    Persist cart items, refreshing the 30-day TTL.
    Raises CartServiceError if Redis write fails.
    """
    try:
        r = _get_redis()
        r.setex(_cart_key(store_id, cart_ref), CART_TTL_SECONDS, json.dumps(items))
    except Exception as exc:
        log.error("cart_set_failed", cart_ref=cart_ref, error=str(exc))
        raise CartServiceError(str(exc)) from exc


def add_to_cart(store_id: str, cart_ref: str, product_id: str, variant_id: str, quantity: int = 1) -> list[dict]:
    """
    Add or increment a line item in the cart.
    Two different variants of the same product are stored as separate line items.
    Returns the updated cart.
    """
    items = get_cart(store_id, cart_ref)

    # Find existing line item for this exact variant
    for item in items:
        if item["variant_id"] == variant_id:
            item["quantity"] += quantity
            set_cart(store_id, cart_ref, items)
            return items

    # New line item
    items.append({
        "product_id": product_id,
        "variant_id": variant_id,
        "quantity": quantity,
    })
    set_cart(store_id, cart_ref, items)
    return items


def remove_from_cart(store_id: str, cart_ref: str, variant_id: str) -> list[dict]:
    """Remove a line item by variant_id. Returns updated cart."""
    items = get_cart(store_id, cart_ref)
    items = [i for i in items if i["variant_id"] != variant_id]
    set_cart(store_id, cart_ref, items)
    return items


def clear_cart(store_id: str, cart_ref: str) -> None:
    """Delete cart from Redis (called after order confirmation)."""
    try:
        r = _get_redis()
        r.delete(_cart_key(store_id, cart_ref))
    except Exception as exc:
        log.warning("cart_clear_failed", cart_ref=cart_ref, error=str(exc))


def merge_carts(store_id: str, guest_ref: str, user_ref: str) -> list[dict]:
    """
    Merge guest cart into user cart on login.
    Guest cart items are appended/incremented in user cart.
    Guest Redis key is deleted after merge.
    """
    guest_items = get_cart(store_id, guest_ref)
    if not guest_items:
        return get_cart(store_id, user_ref)

    user_items = get_cart(store_id, user_ref)
    user_by_variant = {i["variant_id"]: i for i in user_items}

    for guest_item in guest_items:
        vid = guest_item["variant_id"]
        if vid in user_by_variant:
            user_by_variant[vid]["quantity"] += guest_item["quantity"]
        else:
            user_by_variant[vid] = dict(guest_item)

    merged = list(user_by_variant.values())
    set_cart(store_id, user_ref, merged)
    clear_cart(store_id, guest_ref)
    log.info("carts_merged", guest_ref=guest_ref, user_ref=user_ref, items=len(merged))
    return merged


def write_cart_snapshot(store, cart_ref: str, items: list[dict]) -> "CartSnapshot":
    """
    Write cart to PostgreSQL as a safety-net before STK Push.
    Idempotent per cart_ref — updates existing snapshot if found.
    """
    from apps.order.models import CartSnapshot

    snapshot, _ = CartSnapshot.objects.update_or_create(
        store=store,
        cart_key=cart_ref,
        defaults={"items": items},
    )
    return snapshot
