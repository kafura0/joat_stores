# Story 3.6: Dine-In Order + Denormalized Kitchen Ticket
# Story 3.6b: Customer Dine-In Order Confirmation + Live Status Screen

Status: done

## Story

As a kitchen worker, I want to see new orders appear on the kitchen display within 5 seconds,
with full item and modifier details, without navigating away from the screen.

## Acceptance Criteria

**AC1** — POST /api/v1/restaurant/orders/ → creates DineInOrder + KitchenTicket with denormalized JSON snapshot; single prefetch query (no multi-join); waiter_name + table_number baked in
**AC2** — GET /api/v1/restaurant/kitchen/tickets/ → PENDING + IN_PROGRESS only; zero joins (snapshot-only); < 50ms target
**AC3** — PATCH /kitchen/tickets/{id}/ → state machine (PENDING→IN_PROGRESS→COMPLETED|CANCELLED); mirrors status on DineInOrder; invalid → 422 INVALID_TICKET_TRANSITION
**AC4 (3.6b)** — GET /api/v1/restaurant/orders/{id}/status/ → combined order_status + ticket_status; AllowAny; used by TanStack Query refetchInterval:10000

## Tasks/Subtasks

- [x] Task 1: DineInOrder + KitchenTicket models + InvalidSessionTransition.transition() on KitchenTicket
- [x] Task 2: Migration 0004_add_dineinorder_kitchenticket
- [x] Task 3: Serializers (DineInOrderCreateSerializer, DineInOrderSerializer, KitchenTicketSerializer)
- [x] Task 4: DineInOrderView (POST) — validate + build snapshot + atomic create
- [x] Task 5: KitchenTicketListView (GET) — active-only filter + .only() for < 50ms
- [x] Task 6: KitchenTicketUpdateView (PATCH) — state machine + DineInOrder mirror
- [x] Task 7: OrderStatusView (GET, AllowAny) — Story 3.6b polling endpoint
- [x] Task 8: URL registration (4 new routes)
- [x] Task 9: Factories + 14 tests

## Dev Notes

- items_snapshot format: [{menu_item_id, name, price, quantity, contains_allergens, modifiers:[{modifier_id, name, price_addition}]}]
- Denormalization happens in a single prefetch_related("modifier_groups__modifiers") — one query, no joins at ticket display time
- KitchenTicket uses .only() on list endpoint — no SELECT * needed since all data is in snapshot fields
- DineInOrder.status is mirrored from KitchenTicket transitions: IN_PROGRESS→CONFIRMED, COMPLETED→READY, CANCELLED→CANCELLED
- waiter_name denormalized as get_full_name() or email at creation time
- Frontend polling: kitchen display refetchInterval:5000, customer status refetchInterval:10000

## File List

- backend/apps/restaurant/models.py (modified — DineInOrder, KitchenTicket added)
- backend/apps/restaurant/migrations/0004_add_dineinorder_kitchenticket.py
- backend/apps/restaurant/serializers.py (modified — new serializers)
- backend/apps/restaurant/views.py (modified — 4 new views)
- backend/apps/restaurant/urls.py (modified — 4 new routes)
- backend/apps/restaurant/tests/factories.py (modified — DineInOrderFactory, KitchenTicketFactory)
- backend/apps/restaurant/tests/test_kitchen.py

## Change Log

- 2026-03-14: Stories 3.6 + 3.6b implemented
