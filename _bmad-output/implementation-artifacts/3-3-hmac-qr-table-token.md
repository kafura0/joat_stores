# Story 3.3: HMAC QR Table Token Generation + Validation

Status: in-progress

## Story

As a restaurant operator,
I want each table's QR code to be cryptographically signed,
So that customers cannot forge a QR code to join a table they are not at.

## Acceptance Criteria

**AC1** — Token generation: HMAC-SHA256, encodes store_id + table_id + timestamp, 24h TTL
**AC2** — Token validation: valid/unexpired → table+store; invalid → 400 INVALID_QR_TOKEN; expired → 400 QR_TOKEN_EXPIRED
**AC3** — Replay prevention: used token stored in Redis (key: qr:used:{token_hash}, TTL=token TTL); second use → 400 QR_TOKEN_ALREADY_USED

## Tasks/Subtasks

- [x] Task 1: Table model
- [x] Task 2: QR token generation endpoint
- [x] Task 3: QR token validation endpoint (with Redis replay guard)
- [x] Task 4: Tests

## Dev Notes

- Table belongs to Store (TenantModel)
- HMAC-SHA256 key: store-specific secret (HMAC_QR_SECRET env setting or store.qr_secret)
- Token: base64url(json({store_id, table_id, timestamp})) + "." + hex(hmac)
- TTL default: 86400s (24h). Configurable per store.
- Redis replay guard: SET NX with TTL = token expiry remaining
- Use django-redis get_redis_connection("default")

## Dev Agent Record

### Completion Notes
Table model, QR token generation + validation endpoints, Redis replay guard.
11 tests.

## File List

- backend/apps/restaurant/models.py (modified — Table model added)
- backend/apps/restaurant/migrations/0002_add_table.py
- backend/apps/restaurant/qr.py
- backend/apps/restaurant/views.py (modified)
- backend/apps/restaurant/urls.py (modified)
- backend/apps/restaurant/tests/test_qr.py

## Change Log

- 2026-03-14: Story 3.3 implemented
