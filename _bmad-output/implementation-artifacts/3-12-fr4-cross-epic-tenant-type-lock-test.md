# Story 3.12 — FR4 Cross-Epic Tenant Type Lock Test

## Status: done

## Implementation Summary

Closes the FR4 loop: the tenant_type lock guard (implemented in Epic 1's
`Store.save()`) now explicitly checks for `DineInOrder` from the restaurant
app. Tests tagged `cross_tenant` verify the guard fires end-to-end across
Epic 1 (Store model) and Epic 3 (restaurant orders).

## Changes

### `apps/store/models.py` — Store.save() guard update
Refactored the single `from apps.order.models import Order` import into a
dedicated `_has_existing_orders()` method that checks each commerce vertical:

| Vertical | Model checked | App |
|----------|--------------|-----|
| Restaurant | `DineInOrder` | `apps.restaurant` |
| Retail | `Order` | `apps.order` (Epic 4, stub) |

Each import is wrapped in `try/except Exception` so the guard degrades
gracefully before a vertical's migrations have run.

### Tests — `backend/apps/restaurant/tests/test_tenant_lock.py`

All tests tagged with `@pytest.mark.cross_tenant` (NFR3 requirement):

| Test | Scenario |
|------|----------|
| `test_tenant_type_locked_after_first_dine_in_order` | AC1: lock fires after DineInOrder |
| `test_tenant_type_can_change_before_any_orders` | Change allowed pre-order |
| `test_tenant_type_not_locked_when_saving_same_type` | Same type update always allowed |
| `test_tenant_type_lock_is_per_store` | Lock is tenant-scoped |
| `test_fr4_guard_covers_all_dine_in_order_types` | Takeaway orders (session=None) also lock |

## Acceptance Criteria Verification
- AC1 ✅ `ValidationError` raised on `tenant_type` change after `DineInOrder` exists
- AC2 ✅ No exception when changing before any orders
- AC3 ✅ Same-type save on locked store succeeds
- AC4 ✅ Lock is per-store (other store's orders don't affect this store)
- AC5 ✅ Takeaway DineInOrders (session=None) trigger lock equally
- NFR3 ✅ All tests tagged `cross_tenant`; must pass on every PR touching models/views
