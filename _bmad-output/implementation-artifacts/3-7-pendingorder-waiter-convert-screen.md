# Story 3.7: PendingOrder + Waiter Convert Screen

Status: done

## Story

As a customer who wants to pre-select their order before arriving,
I want to browse the menu, choose items, and receive a PIN I can give my waiter when seated,
So that my order is ready to fire the moment I sit down.

## Acceptance Criteria

**AC1** — POST /api/v1/restaurant/pending-orders/ (AllowAny) → PendingOrder with 6-digit PIN, expires_at = now + 24h
**AC2** — Celery beat hourly task purge_expired_pending_orders: soft-deletes PENDING past expires_at; PAID orders flagged for review (not deleted), warning logged
**AC3** — GET /pending-orders/lookup/?pin= or ?phone= → waiter finds order; CONVERTED orders return 404
**AC4** — POST /pending-orders/{id}/convert/ → converts PENDING|PAID order to DineInOrder + KitchenTicket atomically; PendingOrder.status→CONVERTED; 404 if already CONVERTED or session not OPEN

## Tasks/Subtasks

- [x] Task 1: PendingOrder model + _generate_pin() helper; migration 0005
- [x] Task 2: Celery task purge_expired_pending_orders; registered in CELERY_BEAT_SCHEDULE (hourly)
- [x] Task 3: Serializers: PendingOrderCreateSerializer, PendingOrderSerializer, PendingOrderLookupSerializer
- [x] Task 4: PendingOrderCreateView (POST, AllowAny)
- [x] Task 5: PendingOrderLookupView (GET, authenticated)
- [x] Task 6: PendingOrderConvertView (POST, authenticated)
- [x] Task 7: URL registration (3 new routes)
- [x] Task 8: PendingOrderFactory + 11 tests

## Dev Notes

- items_snapshot built with same logic as DineInOrderView (single prefetch query)
- expires_at = timezone.now() + 24h at creation — Celery purges past this
- PAID orders (Story 3.8 hook): not auto-deleted, log warning for operator review
- Convert is atomic: DineInOrder + KitchenTicket in single transaction.atomic()
- PIN is 6-digit zero-padded random int; collision risk low (1-in-1M per store)
- Converted orders not retrievable via lookup (status not in PENDING|PAID filter)

## File List

- backend/apps/restaurant/models.py (modified — PendingOrder added)
- backend/apps/restaurant/migrations/0005_add_pending_order.py
- backend/apps/restaurant/tasks.py (new)
- backend/apps/restaurant/serializers.py (modified — 3 new serializers)
- backend/apps/restaurant/views.py (modified — 3 new views)
- backend/apps/restaurant/urls.py (modified — 3 new routes)
- backend/apps/restaurant/tests/factories.py (modified — PendingOrderFactory)
- backend/apps/restaurant/tests/test_pending_order.py
- backend/config/settings/base.py (modified — purge beat schedule added)

## Change Log

- 2026-03-14: Story 3.7 implemented
