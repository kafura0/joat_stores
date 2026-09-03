---
title: Architecture Review — PRD joat_stores
reviewer: Winston (System Architect)
date: 2026-09-03
prd: prd-joat_stores-2026-09-03
---

# Architecture Review: JOAT Stores PRD

## Executive Summary

The PRD is well-structured and the addendum captures the right architectural decisions. However, there are several gaps between what the PRD *describes* and what the codebase *actually supports*. The most critical issues are the unimplemented X-Store-ID role check, the Celery worker cost cliff (free → starter), and the absence of a concrete EOD reconciliation implementation.

---

## Findings

### CRITICAL

| # | Issue | Detail | Recommended Fix |
|---|-------|--------|-----------------|
| C-1 | **X-Store-ID vulnerability is unpatched** | `TenantMiddleware` (middleware.py:59-79) accepts X-Store-ID from *any* request — there is no JWT role check. A store owner with a valid JWT for Store A can send `X-Store-ID: <Store-B-UUID>` and access Store B data. The addendum (A1) describes the fix but it is not implemented. This is FR-1's primary test case. | Decode the JWT in middleware when X-Store-ID is present. If `role != platform_admin`, return 403. Add the cross-tenant isolation test (`pytest -m cross_tenant`) to CI before launch. This is a launch blocker. |
| C-2 | **Celery worker requires Render Starter plan ($7/mo) — cost not budgeted** | `render.yaml:80-137` comments out the worker and beat services, noting they require `plan: starter`. The PRD assumes Render free tier is sufficient (§6.1, assumption index). Enabling the worker creates a hard $7/mo cost floor. Beat adds another $7/mo. Total: $14/mo minimum. | Update the cost model in the PRD. Free tier is viable only if all async tasks (notifications, payment reconciliation, EOD) are moved to synchronous processing — which is unacceptable for payment flows. Budget $14/mo from day 1 or accept that payments may silently fail on free tier. |
| C-3 | **M-Pesa callback arrives during cold boot — no retry strategy defined** | Addendum A3 proposes cron-job.org pinging every 10min to prevent Render free tier sleep. But cron-job.org is a free third-party service with no SLA. If it misses a ping and Render sleeps, incoming M-Pesa webhooks hit a dead endpoint. Safaricom retries webhooks, but the retry window is有限 (typically 3 attempts over ~30s). | Define a fallback: (1) Use UptimeRobot (already planned) as primary keepalive instead of cron-job.org, (2) add a `/api/v1/payments/mpesa-callback-retry/` endpoint that accepts deferred callbacks, (3) document Safaricom's retry policy and ensure the 10min ping interval stays well within it. |

### HIGH

| # | Issue | Detail | Recommended Fix |
|---|-------|--------|-----------------|
| H-1 | **Tab.total_amount is an O(n) property — N+1 on every access** | `bar/models.py:124-130` computes `total_amount` by iterating all active TabItem records. This is called on every tab list/detail response. With 20 items per tab and 30 tabs per screen load, that's 600 extra queries per page render. The addendum (A9) mentions pre-computing but doesn't specify the field type or migration strategy. | Add `total_amount` as a concrete `DecimalField` on `Tab`. Recompute on `TabItem.save()` / `TabItem.delete()` via `post_save`/`post_delete` signals (not `post_delete` on soft-delete — use the safedelete signal). Add a migration that backfills from existing data. This is a launch performance requirement. |
| H-2 | **EOD reconciliation has no fallback if raw SQL is slow** | Addendum A6 proposes raw SQL `GROUP BY date, payment_method` for v1. At 100 orders/day this is fine. But if a store does 500+ orders/day (busy Saturday night), the query scans ~1.5MB of JSON per day. No index exists on `TabItem.created_at` joined to `Tab.store_id` for date-range filtering. | Add a composite index: `CREATE INDEX idx_bar_tabitem_store_date ON bar_tabitem (store_id, created_at) WHERE removed_at IS NULL;`. Also add a materialized view or summary table as a v1.5 backup — the raw SQL approach works until it doesn't, and there's no graceful degradation. |
| H-3 | **Connection exhaustion at 10 concurrent users** | Addendum A10 sets `CONN_MAX_AGE=4` with PgBouncer `pool_size=10`. Render free tier has 1 outbound connection. With 2 gunicorn workers + 1 Celery worker = 3 persistent connections. At 10 concurrent admin users hitting the platform metrics endpoint (FR-20), connection wait times spike. PgBouncer helps but `pool_size=10` is tight. | Increase PgBouncer `pool_size` to 20 (still under Supabase's 60-connection limit). Add connection timeout configuration: `CONN_MAX_AGE=0` (short-lived connections) with PgBouncer handling pooling. Or better: switch gunicorn to `--workers 1 --threads 4` to reduce connection count at the cost of concurrency. |
| H-4 | **Missing API endpoint specification** | The PRD references `GET /api/v1/bar/reconciliation/` (FR-13) and WhatsApp summary (FR-14) but does not specify: (a) the reconciliation response schema, (b) pagination for tab list endpoints, (c) the staff PIN auth flow for FR-19, (d) the QR code verification endpoint for FR-16. Missing endpoints make story estimation unreliable. | Add an API surface appendix to the PRD listing all endpoints with method, path, and response shape. At minimum: `POST /api/v1/bar/tabs/{id}/pay-cash/`, `GET /api/v1/bar/reconciliation/`, `POST /api/v1/auth/staff-pin/`, `GET /api/v1/storefront/qr-verify/`. |
| H-5 | **WhatsApp daily summary has no error handling spec** | Addendum A8 says "failed sends logged and retried once." But: (a) what if Twilio is down during the 22:00 EAT window? (b) what if the store owner's phone number is invalid? (c) what's the retry interval? (d) is there a circuit breaker for repeated failures? | Define: retry with 5min backoff (max 3 attempts), dead-letter if all fail, invalid phone numbers flagged on StoreSettings, Twilio status callback for delivery confirmation. Add a `WhatsAppDeliveryLog` model or append to the notification table. |

### MEDIUM

| # | Issue | Detail | Recommended Fix |
|---|-------|--------|-----------------|
| M-1 | **BarDailyReconciliation model deferral is risky** | Addendum A6 defers the model to "month 3-6." But the EOD report (FR-13) needs to be *reproducible* — if the raw SQL is re-run, it must produce identical results. Without a persisted model, there's no audit trail for discrepancies. A bar owner who disputes a reconciliation has no historical record. | Create a lightweight `BarDailyReconciliation` model in v1 with fields: `store FK`, `date`, `tab_count`, `total_revenue`, `total_collected`, `discrepancy`, `payment_method_breakdown JSON`, `reconciled_by FK`, `created_at`. Write-once, never update. This is < 200 bytes/row and provides the audit trail the business needs. |
| M-2 | **Data retention strategy lacks concrete implementation** | Addendum A7 says "monthly Celery task `archive_old_orders`" but no task exists in `apps/order/tasks.py` or `apps/analytics/tasks.py`. The task needs to: (1) backfill `DailyRevenueSummary` for the month, (2) hard-delete `Order` records > 90 days, (3) cascade to `CartSnapshot`. Without this, Supabase hits 500MB in ~2 years (per assumption), but the actual timeline is shorter if stores do 300+ orders/day. | Implement `archive_old_orders` in `apps/order/tasks.py`. Use `DELETE FROM order_order WHERE created_at < NOW() - INTERVAL '90 days' AND store_id = :store_id` after summary backfill. Add a monitoring query that alerts at 80% Supabase capacity. |
| M-3 | **Happy hour edge case: midnight crossover** | `HappyHour.is_active_now()` (bar/models.py:335-346) uses `start_time <= current_time <= end_time`. If happy hour is 10pm-2am, this fails because `22:00 <= 02:00` is false. The model doesn't support overnight windows. | Add `is_overnight` boolean field to `HappyHour`. If true, the check becomes: `current_time >= start_time OR current_time <= end_time`. This is a common bar scenario (late-night specials). |
| M-4 | **Subscription billing has no payment method storage** | Addendum A5 says "charge stored M-Pesa payment method." But `MpesaTransaction` stores one-time STK Push results — there's no concept of a "saved payment method" for recurring billing. M-Pesa doesn't support tokenized recurring charges like Stripe does. | Either: (a) initiate a new STK Push for each billing cycle (requires owner to enter PIN monthly — bad UX), (b) use M-Pesa's Recurring Checkout API (if available in Kenya), or (c) defer subscription billing to manual payment with a "mark as paid" admin action. The PRD should be explicit about this limitation. |
| M-5 | **PWA service worker cache invalidation undefined** | FR-15 says service worker caches shell with "stale-while-revalidate." But there's no versioning strategy for the cache. When the storefront deploys a new version, users on the old PWA will see stale CSS/JS until they manually refresh. | Add a cache version hash to `sw.js` (e.g., `CACHE_NAME = 'joat-v{BUILD_HASH}'`). On deploy, the new hash invalidates the old cache. Use `skipWaiting()` + `clients.claim()` for immediate activation. |

### LOW

| # | Issue | Detail | Recommended Fix |
|---|-------|--------|-----------------|
| L-1 | **AgeRestrictionLog doesn't handle staff override** | FR-9 says "first alcohol item requires age acknowledgement." But what if a staff member adds alcohol without acknowledgement (rush hour, muscle memory)? There's no enforcement at the API level — only a UI prompt. | Add a `@require_age_acknowledgement` decorator on the `TabItem` create endpoint. If `menu_item.is_age_restricted` and no `AgeRestrictionLog` exists for the tab, reject with 400. |
| L-2 | **QR code HMAC secret rotation not addressed** | `render.yaml` generates `HMAC_QR_SECRET` but there's no rotation mechanism. If the secret is compromised, all existing QR codes become forgeable. | Document a rotation procedure: generate new secret, update env var, redeploy. Old codes remain valid until their HMAC expires (add a 24h expiry to QR codes). |
| L-3 | **Store suspension check happens twice in middleware** | `TenantMiddleware.process_request` checks `store.status == StoreStatus.SUSPENDED` in both the X-Store-ID branch (line 69) and the Host branch (line 112). This is duplicated logic. | Extract to a helper method `_check_suspended(store, path)` to DRY up the logic and reduce the chance of the two branches diverging. |
| L-4 | **No rate limiting on STK Push initiation** | FR-10 doesn't mention rate limiting on STK Push. A malicious actor could spam the endpoint and generate Safaricom API charges for the store. | Add DRF throttling: `AnonRateRate('10/hour')` on the payment initiation endpoint. Per-store throttle: `scope='mpesa_stk'` with limit based on subscription tier. |

---

## Answers to Specific Questions

### Is the BarDailyReconciliation model needed in v1?

**Yes, build it in v1.** The raw SQL approach (addendum A6) defers the problem but creates two new ones: (1) no audit trail for reconciliation disputes, and (2) the query must be re-runnable with identical results, which is fragile without a persisted artifact. The model is ~200 bytes/row — at 1 reconciliation/day/store × 365 days × 10 stores = 730KB after a year. This is trivial against Supabase's 500MB limit. Build the model, write once, never update. It's the boring, correct choice.

### Is the Celery worker fix sufficient for production?

**No — it's necessary but not sufficient.** Uncommenting the worker in render.yaml solves the silent failure problem. But: (1) it creates a $7/mo cost floor that contradicts the "free tier sufficient" assumption, (2) there's no health monitoring for the worker itself (the health endpoint exists but nothing *acts* on it), (3) the worker shares the same `DJANGO_SECRET_KEY` via `fromService` — if the web service is redeployed, the worker's key goes stale until it restarts. Add: (a) UptimeRobot on `/health/workers/` with 5min interval, (b) worker auto-restart on key rotation, (c) update the cost model.

### Are there N+1 query risks in the described flows?

**Yes — three confirmed risks:**
1. **`Tab.total_amount`** (bar/models.py:124): Queries all TabItem records on every access. With 30 open tabs on screen, this fires 30 queries × ~5 items = 150 extra queries. Fix: concrete field + signal recalculation.
2. **Admin dashboard "recent orders"** (addendum A9 mentions this): Order → payment_transaction FK not prefetched. Fix: `select_related("payment_transaction")` on the queryset.
3. **Tab list with rounds**: Loading a tab list will trigger N+1 on `tab.rounds.all()` and `tab.items.all()`. Fix: `Prefetch("rounds", queryset=TabRound.objects.prefetch_related("items"))`.

### Is the data retention strategy sound?

**Partially.** The 12-month retention for KRA compliance is correct. But: (1) the archive task doesn't exist yet, (2) there's no monitoring for Supabase capacity, (3) hard-deleting Order records cascades to CartSnapshot but not to MpesaTransaction (which has `on_delete=SET_NULL` — orphaned payment records). The strategy is *directionally correct* but needs implementation + safeguards.

### Are there missing API endpoints?

**Yes — at least 6 endpoints are referenced but not specified:**
1. `POST /api/v1/bar/tabs/{id}/pay-cash/` — mentioned in FR-7 but no request/response shape
2. `GET /api/v1/bar/reconciliation/` — mentioned in FR-13 but no query params or response schema
3. `POST /api/v1/auth/staff-pin/` — referenced in FR-19 but no auth flow defined
4. `GET /api/v1/storefront/qr-verify/` — referenced in FR-16 but no verification logic
5. `POST /api/v1/bar/tabs/{id}/request-bill/` — implied by FR-6 but not explicitly listed
6. `GET /api/v1/health/celery/` — referenced in addendum A2 but not in the PRD

---

## Summary

| Severity | Count | Launch Blockers |
|----------|-------|-----------------|
| CRITICAL | 3 | C-1 (X-Store-ID), C-2 (Celery cost), C-3 (webhook retry) |
| HIGH | 5 | H-1 (N+1), H-4 (missing endpoints) |
| MEDIUM | 5 | — |
| LOW | 4 | — |

**Bottom line:** The architecture is sound in direction but has implementation gaps that will cause production incidents. C-1 is a security vulnerability. C-2 is a budget surprise. H-1 is a performance cliff at scale. Fix these three before launch.
