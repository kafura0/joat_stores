# Story 3.9: Reservation Model

Status: done

## Story

As a customer, I want to book a table at a restaurant for a specific time and party size
and receive a confirmation via WhatsApp or SMS.

## Acceptance Criteria

**AC1** — POST /api/v1/restaurant/reservations/ → status PENDING; send_reservation_notification task dispatched (countdown=0, queue=notifications, event="created")
**AC2** — PATCH /reservations/{id}/confirm/ → PENDING→CONFIRMED + notification; 422 INVALID_RESERVATION_TRANSITION on bad move
**AC3** — PATCH /reservations/{id}/seat/ → CONFIRMED→SEATED; auto-creates OPEN TableSession for reserved table; reservation.session FK set; 400 TABLE_NOT_ASSIGNED if table is None
**AC4** — PATCH /reservations/{id}/no-show/ → CONFIRMED→NO_SHOW; 422 on bad transition

## Tasks/Subtasks

- [x] Task 1: Reservation model: PENDING→CONFIRMED→SEATED|NO_SHOW|CANCELLED; table FK (nullable); session OneToOneField; migration 0007
- [x] Task 2: send_reservation_notification Celery task (queue=notifications, max_retries=3); stubs WhatsApp/SMS until Story 10.3
- [x] Task 3: ReservationSerializer
- [x] Task 4: ReservationViewSet: create, confirm, seat, no-show actions; direct PATCH→405
- [x] Task 5: Router registration (reservations/)
- [x] Task 6: 10 tests (test_reservation.py)

## Dev Notes

- Notification dispatch happens in perform_create + each transition action
- seat/ action creates TableSession in a try/except IntegrityError → 409 DUPLICATE_SESSION
- Valid state machine: PENDING→[CONFIRMED|CANCELLED], CONFIRMED→[SEATED|NO_SHOW|CANCELLED]
- WhatsApp/SMS TODO: Story 10.3 replaces the structlog stub in send_reservation_notification

## File List

- backend/apps/restaurant/models.py (modified — Reservation model added)
- backend/apps/restaurant/migrations/0007_add_reservation.py
- backend/apps/restaurant/tasks.py (modified — send_reservation_notification added)
- backend/apps/restaurant/serializers.py (modified — ReservationSerializer)
- backend/apps/restaurant/views.py (modified — ReservationViewSet)
- backend/apps/restaurant/urls.py (modified — reservations/ registered)
- backend/apps/restaurant/tests/test_reservation.py

## Change Log

- 2026-03-14: Story 3.9 implemented
