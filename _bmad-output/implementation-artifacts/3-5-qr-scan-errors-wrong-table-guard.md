# Story 3.5: QR Scan Errors + Wrong-Table Guard

Status: done

## Story

As a customer,
I want a clear, friendly error if I scan the wrong table's QR code or a damaged/expired code,
So that I can correct the situation without frustration and without placing an order at the wrong table.

## Acceptance Criteria

**AC1** — Valid token response includes confirmation_prompt ("You're joining Table N's session at [Store Name]. Is this correct?") and fallback_url (/t/{table_id}/)
**AC2** — GET /t/{table_id}/ returns table_number, store_name, and help message; 404 for unknown/inactive tables
**AC3** — Expired token → "This QR code has expired. Please ask your waiter to refresh it." (user-friendly, no internal details)
**AC4** — Tampered/invalid token → "Invalid or damaged QR code. Please ask staff for help." (generic, no HMAC/signature details)

## Tasks/Subtasks

- [x] Task 1: Update QR validate view — user-friendly error messages, confirmation_prompt, fallback_url
- [x] Task 2: PublicTableView (GET /t/{table_id}/) — fallback URL endpoint
- [x] Task 3: fallback_urls.py + root URL config registration
- [x] Task 4: 8 tests (test_qr_errors.py)

## Dev Notes

- Error messages are normalized in the VIEW layer, not in qr.py — the QR module keeps internal error reasons for logging
- _USER_MESSAGES dict maps error codes to customer-safe strings
- /t/{table_id}/ registered at root level (not under /api/v1/restaurant/) — matches the UX design fallback URL format
- Internal error details logged via structlog before returning generic response

## File List

- backend/apps/restaurant/views.py (modified — QRTokenValidateView updated + PublicTableView added)
- backend/apps/restaurant/fallback_urls.py (new)
- backend/config/urls.py (modified — /t/<uuid:table_id>/ registered)
- backend/apps/restaurant/tests/test_qr_errors.py (new)

## Change Log

- 2026-03-14: Story 3.5 implemented
