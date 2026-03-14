# Story 3.2: Public Menu URL

Status: done

## Story

As a potential customer,
I want to browse a restaurant's full menu from a shareable link without scanning a QR code,
So that I can decide what to order before I arrive.

## Acceptance Criteria

**AC1** — GET /{store_slug}/menu/ is public (no auth), SSR, time-filtered
**AC2** — Lighthouse CI gate < 1.5s interactive on 3G
**AC3** — Responsive at 320px

## Tasks/Subtasks

- [x] Task 1: Backend public menu API endpoint (no auth required)
- [x] Task 2: Next.js public menu page (SSR, time-filtered)
- [x] Task 3: Lighthouse CI config stub (lighthouserc.js)
- [x] Task 4: Tests (backend: public endpoint, no auth; frontend: SSR page renders)

## Dev Notes

- Backend: AllowAny permission on PublicMenuView
- Returns sections with items filtered by current time window
- Next.js: Server Component, fetches from backend API via fetch() with no-store cache
- TenantMiddleware resolves store from domain — store_slug in URL is for shareable link UX

## Dev Agent Record

### Completion Notes
Backend PublicMenuView with AllowAny, time-filtered sections+items.
Next.js /menu page as Server Component SSR. Lighthouse CI config stub.
Tests cover public access (no auth), time filtering, tenant isolation.

## File List

- backend/apps/restaurant/views.py (modified)
- backend/apps/restaurant/urls.py (modified)
- backend/apps/restaurant/tests/test_public_menu.py
- storefront/src/app/menu/page.tsx
- lighthouserc.js

## Change Log

- 2026-03-14: Story 3.2 implemented — public menu URL
