# Story 3.4: Table + TableSession State Machine + Waiter Assignment

Status: done

## Story

As a restaurant waiter,
I want to open a table session when customers are seated and assign myself as the waiter,
So that all orders for that table are linked to me and visible on kitchen tickets.

## Acceptance Criteria

**AC1** — Session creation: valid QR scan → POST /api/v1/restaurant/sessions/ → creates OPEN session; UniqueConstraint enforces one OPEN per table — duplicate → 400 DUPLICATE_SESSION (DB IntegrityError mapped to ValidationError)
**AC2** — Waiter assignment: PATCH /sessions/{id}/assign-waiter/ → sets assigned_waiter FK; closed session → 422 INVALID_SESSION_TRANSITION
**AC3** — State machine OPEN→BILL_REQUESTED→CLOSED via .transition(); invalid transitions → 422 INVALID_SESSION_TRANSITION; direct PATCH → 405

## Tasks/Subtasks

- [x] Task 1: TableSession model + InvalidSessionTransition exception + state machine
- [x] Task 2: Migration 0003_add_table_session
- [x] Task 3: TableSessionSerializer
- [x] Task 4: TableSessionViewSet (create, assign-waiter, request-bill, close)
- [x] Task 5: URL registration
- [x] Task 6: QR validate updated to return open_session_id
- [x] Task 7: TableSessionFactory + 13 tests

## Dev Notes

- TableSession inherits TenantModel (UUID PK, store FK, soft-delete)
- UniqueConstraint: partial (condition=Q(status="OPEN")) — one OPEN per table
- closed_at populated automatically on CLOSED transition
- assigned_waiter FK → settings.AUTH_USER_MODEL; waiter name denormalized in serializer
- State machine enforced via transition() method only — update() viewset action returns 405
- QR validate now returns open_session_id alongside table/store details

## File List

- backend/apps/restaurant/models.py (modified — TableSession + InvalidSessionTransition added)
- backend/apps/restaurant/migrations/0003_add_table_session.py
- backend/apps/restaurant/serializers.py (modified — TableSessionSerializer added)
- backend/apps/restaurant/views.py (modified — TableSessionViewSet + QR validate updated)
- backend/apps/restaurant/urls.py (modified — sessions router registered)
- backend/apps/restaurant/tests/factories.py (modified — TableSessionFactory added)
- backend/apps/restaurant/tests/test_session.py

## Change Log

- 2026-03-14: Story 3.4 implemented
