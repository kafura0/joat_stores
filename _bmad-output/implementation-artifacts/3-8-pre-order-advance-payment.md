# Story 3.8: Pre-Order + Advance Payment

Status: done

## Story

As a customer who wants their food ready the moment they arrive,
I want to pay for my order in advance online,
So that the kitchen starts preparation on confirmation of my seating without any delay.

## Acceptance Criteria

**AC1** — POST /api/v1/restaurant/pending-orders/{id}/pay/ (AllowAny) → calls initiate_payment() with reference=f"pending-{order.id}"; STK Push sent; 429 on rate limit; 502 on Daraja failure
**AC2** — payment_confirmed signal handler (restaurant/apps.py) → reference.startswith("pending-") → PendingOrder.status→PAID; does not raise if order already converted/expired
**AC3** — Convert PAID order → DineInOrder.payment_transaction linked to confirmed MpesaTransaction; kitchen fires on waiter confirmation, not on payment
**AC4** — PAID+expired: purge task logs warning, does NOT delete (verified in Story 3.7 tests)

## Tasks/Subtasks

- [x] Task 1: payment_transaction FK on DineInOrder; migration 0006_add_payment_link
- [x] Task 2: payment_confirmed signal receiver in RestaurantConfig.ready()
- [x] Task 3: PendingOrderPayView (POST, AllowAny)
- [x] Task 4: PendingOrderConvertView updated to link payment_transaction on PAID conversion
- [x] Task 5: URL registration (/pending-orders/{id}/pay/)
- [x] Task 6: 8 tests (test_preorder_payment.py)

## Dev Notes

- STK Push reference: f"pending-{order.id}" — signal receiver parses this prefix
- DineInOrder.payment_transaction is SET_NULL on delete — no cascade deletion of payment records
- "Kitchen fires on waiter confirmation": KitchenTicket is created in convert(), not in pay()
- Signal registered in RestaurantConfig.ready() via payment_confirmed.connect()

## File List

- backend/apps/restaurant/models.py (modified — payment_transaction FK on DineInOrder)
- backend/apps/restaurant/migrations/0006_add_payment_link.py
- backend/apps/restaurant/apps.py (modified — signal receiver connected in ready())
- backend/apps/restaurant/views.py (modified — PendingOrderPayView added, ConvertView updated)
- backend/apps/restaurant/urls.py (modified — /pay/ route added)
- backend/apps/restaurant/tests/test_preorder_payment.py

## Change Log

- 2026-03-14: Story 3.8 implemented
