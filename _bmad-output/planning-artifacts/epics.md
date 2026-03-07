---
stepsCompleted: [step-01-validate-prerequisites, step-02-design-epics, step-03-create-stories, step-04-final-validation]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
---

# joat_stores - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for joat_stores, decomposing the requirements from the PRD, UX Design, and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

#### Multi-Tenant Platform

FR1: System shall resolve tenant from incoming domain (e.g., `techstore.joat.com`) or `X-Store-ID` header on every request, populating `request.store` before any business logic executes.
FR2: Platform shall manage full tenant lifecycle with states: `pending` → `active` → `suspended` → `cancelled`, each with defined system behaviour (storefront 503 on suspended, data retained 90 days on cancelled).
FR3: System shall support three tenant types (`retail`, `restaurant`, `bar`) as a configuration parameter that activates the relevant feature modules without code changes or redeployment.
FR4: Tenant type shall be locked after the first order is placed; `Store.save()` override raises `IntegrityError` if `tenant_type` changes on a store with existing orders.
FR5: Tenant isolation shall be enforced at 5 layers: middleware (request.store resolution), base queryset (TenantQuerySet), serializer (auto-populate store), permission class (IsStoreScoped), admin (StoreAdmin base class).
FR6: Store-scoped admin shall restrict all data visibility to the authenticated user's own store; no cross-tenant data ever returned.
FR7: Platform admin dashboard shall provide full multi-tenant visibility with tenant health, combined GMV, per-tenant deep-dives, and unit economics tracking.
FR8: Store provisioning sequence (Create Store → Assign Domain → Set tenant_type → Create StoreSubscription → Assign store_owner) shall be wrapped in `transaction.atomic()` — partial state is a hard failure.

#### Retail Commerce

FR9: Product catalog shall support categories, product attributes, variants (size × colour combinations), per-variant inventory tracking, and multi-image media.
FR10: Cart shall be backed by Redis with a 30-day TTL, supporting guest and authenticated sessions, persisting across browser close and session expiry.
FR11: Order lifecycle shall follow: `pending` → `confirmed` → `fulfilled` → `completed` (or `cancelled`), enforced via `order.transition_status()` — never direct field assignment.
FR12: Guest checkout shall allow purchase without account creation; registration prompt appears only post-payment as an optional offer.
FR13: Authenticated checkout shall support Google Sign-In via OAuth2 PKCE producing a store-scoped customer account with `store_id` in scope during the OAuth callback.
FR14: M-Pesa STK Push shall be initiated for checkout, restaurant bill, bar tab settlement, and SaaS subscription renewal via the Daraja API client in `apps/payment/daraja.py`.
FR15: Card payment scaffold shall exist (Stripe/Flutterwave endpoints returning 501 at MVP) — no card processing live at MVP.
FR16: Order confirmation email shall be sent asynchronously via Celery (`order.notifications` queue) within 60 seconds of order confirmation.
FR17: Low-stock alerts shall trigger automatically when inventory falls below threshold, dispatching supplier notification emails via Celery (`inventory.alerts` queue).
FR18: All uploaded images shall be server-side compressed to WebP via Pillow, max 800KB; original file deleted from temp storage immediately after compression.

#### F&B — Restaurant Module

FR19: Restaurant tenant type shall activate menu management, QR dine-in, table session management, kitchen order view, and time-based menu scheduling.
FR20: Menu management shall support sections, items, modifier groups (min/max selection rules), and individual modifiers with additive pricing.
FR21: System shall support three order types: dine-in (QR per table), takeaway, and delivery.
FR22: QR code per table shall encode `store_id` + `table_id` + HMAC signature; unsigned QR codes shall be rejected.
FR23: Table session state machine shall be: `OPEN` → `BILL_REQUESTED` → `CLOSED`; only one `OPEN` session per table enforced via DB `UniqueConstraint`.
FR24: Kitchen order view shall return only `PENDING` and `IN_PROGRESS` tickets, completing in < 50ms (no multi-table joins); kitchen display shall poll every 5 seconds via TanStack Query `refetchInterval`.
FR25: M-Pesa bill payment at table shall use STK Push; multiple payers supported (split bill) with per-person itemization.
FR26: Menu items shall support time-based scheduling (breakfast/lunch/dinner service windows); out-of-schedule items hidden from storefront automatically.
FR27: Allergen information (`contains_allergens` flag) shall be displayable per menu item.

#### F&B — Bar Module

FR28: Bar tenant sub-type shall activate tab management, round ordering, age-restricted item enforcement, and happy hour pricing; requires `apps/restaurant/` active.
FR29: Tab state machine shall be: `OPEN` → `BILL_REQUESTED` → `SETTLED`; state transitions enforced in code, never direct field assignment.
FR30: Round ordering shall be possible on an existing open tab without re-authentication.
FR31: Age-restricted items (`is_age_restricted=True`) shall require an age acknowledgement (`AgeRestrictionLog` entry) before the item can be added to a tab.
FR32: Happy hour pricing shall be evaluated and snapshotted at item-add time; prices never recalculated at settlement; "HH" badge visible on discounted items; automatic notice on first full-price item added.
FR33: Tab settlement shall support split-pay via M-Pesa with individual STK Push per person.

#### Payments

FR34: STK Push initiation shall be idempotent — check for existing `pending` or `confirmed` payment on the same order before initiating a new push; return existing payment record if found.
FR35: All Daraja webhooks shall be verified via HMAC signature before processing; `ResultCode == 0` alone is not verification.
FR36: `MpesaTransaction.mpesa_receipt_number` shall have `unique=True` DB constraint; duplicate webhook returns HTTP 200 (never 4xx) to prevent Daraja retry storms.
FR37: Celery Beat `reconcile_payments` task shall run daily, querying Daraja Transaction Status API for `STK_PUSH_INITIATED` payments older than 2 hours.
FR38: M-Pesa reversal shall create a new `Payment(type='REVERSAL')` linked to the original — never mutate original; reversal only within 24-hour window (422 `REVERSAL_WINDOW_EXPIRED` if exceeded).
FR39: STK Push timeout (`ResultCode: 1032` or `1037`) shall set payment status to `EXPIRED` (never `FAILED`); order stays `PENDING`; customer sees retry prompt.
FR40: Daraja OAuth2 access token shall be cached in Redis (`daraja:access_token:{env}`, TTL 3500s) — never fetched per STK Push call.

#### Auth & RBAC

FR41: JWT tokens shall include a `store_id` claim and `role` claim (`platform_admin`, `store_owner`, `store_manager`, `customer`); RBAC from JWT claims only — never `is_staff` or Django group membership.
FR42: Access token in memory only; refresh token in httpOnly cookie; never `localStorage` for tokens.
FR43: Plan-based feature flags shall be enforced server-side on every request from `request.store.subscription.plan` — never cached in JWT or session.
FR44: API rate limits shall be read from `request.store.subscription.plan.api_rate_limit` — never hardcoded.
FR45: `AdminPIIAccessLog(user, store, record_type, record_id, accessed_at)` shall be created for every admin access to customer PII — Kenya DPA 2019 compliance.

#### Async Infrastructure

FR46: Celery workers shall use 5 named queues: `order.notifications`, `inventory.alerts`, `billing.reminders`, `payments.reconciliation`, `analytics.reports`.
FR47: Dead-letter queue (DLQ) shall be configured before any async task is written; tasks use exponential backoff (max 5 retries, countdown = `60 * (2 ** retries)`).
FR48: Celery Beat shall run: daily payment reconciliation, daily analytics summary generation, weekly merchant digest, subscription renewal reminder 3 days before period end.
FR49: Worker health endpoint `/health/workers/` shall expose queue depth and last heartbeat per worker.
FR50: Celery Flower shall run as a Docker service for queue monitoring.

#### Analytics

FR51: Per-store analytics shall provide: daily revenue, order count, AOV, top products — read from pre-aggregated `DailyRevenueSummary` tables (never live ORM aggregations on Order/Payment tables).
FR52: Restaurant analytics shall include: peak hours (hour-of-day bucketing via `HourlyOrderSummary`), table turn rate (from `TableSession.status = 'closed'` signal).
FR53: Bar analytics shall include: tab completion rate and round size (from `Tab.status = 'settled'` signal), occupancy hours.
FR54: Platform analytics shall provide: GMV (sum of all tenant `DailyRevenueSummary.total_revenue`), `TenantHealthSnapshot` (one per tenant per day), unit economics (cost-per-tenant vs revenue-per-tenant).
FR55: Analytics data capture shall occur as a side effect via Django `post_save` signals + `transaction.on_commit` Celery tasks — never inside primary business logic.
FR56: `AIEvent` model shall capture product views, cart adds/removes, searches, and order completions from day one (append-only; never update/delete events).
FR57: Analytics dashboards shall display yesterday's data (Celery Beat `generate_daily_summary` runs at 00:05 daily); admin UI copy must document this.

#### SaaS Scaffold

FR58: `Plan` model shall have fields: `name`, `product_limit`, `staff_limit`, `analytics_tier`, `ai_access`, `custom_domain`, `api_rate_limit`, `monthly_price_kes`, `monthly_price_usd`.
FR59: `StoreSubscription` lifecycle: `trial` → `active` → `past_due` → `suspended` → `cancelled`; 14-day trial, 7-day grace period on non-payment.
FR60: M-Pesa subscription renewal shall be triggered via Celery Beat STK Push flow, separate from customer checkout STK Push flow (separate callback endpoint and Celery queue).
FR61: Usage limit enforcement via `enforce_plan_limit(store, feature, current_count)` in `apps/saas/services.py`; both single-create and bulk operations call this function; response is HTTP 403 `PLAN_LIMIT_EXCEEDED`.
FR62: `apps/ai/` shall exist from day one with `models.py`, `services.py`, `views.py`; all endpoints return HTTP 501 at MVP, gated behind `plan.features.has_ai == True`.
FR63: Merchant onboarding shall complete in under 24 hours; provisioning sequence runbook must exist before go-live.

#### Platform Infrastructure

FR64: Docker Compose shall orchestrate: Django API, PostgreSQL, Redis, Celery worker, Celery Beat, Celery Flower, storefront (Next.js), admin (Next.js), Nginx.
FR65: Nginx shall route per-tenant domains to the shared storefront/admin Next.js apps; new tenant domains added to `nginx/conf.d/tenants/` (manual step at MVP).
FR66: `scripts/preflight.sh` shall be run before every `docker compose up` (including `--build` and `-d`); pre-flight failure is a hard stop.
FR67: GitHub Actions CI shall run on every PR: `flake8` + `black` + `isort` + TypeScript strict compile + `pytest` full suite; CD deploys via SSH on merge to main.
FR68: `scripts/backup.sh` shall run daily via Celery Beat: `pg_dump` → `/backups/$(date).sql.gz`, 7-day rotation.
FR69: Redis AOF persistence shall be enabled in Docker Compose to prevent cart data loss on container restart.
FR70: OpenAPI schema shall be auto-generated via `drf-spectacular` for all API endpoints.

### NonFunctional Requirements

NFR1: API response time p95 < 300ms at MVP, < 150ms at Month 12.
NFR2: API uptime 99.5% at MVP, 99.9% at Month 12.
NFR3: Zero cross-tenant data incidents — enforced at queryset and permission layer; `pytest -k "cross_tenant"` must pass on every PR touching models or views.
NFR4: M-Pesa STK Push delivery success > 98% on valid Kenyan phone numbers.
NFR5: Celery task delivery > 99% with DLQ + retry; Celery Flower operational from Day 1.
NFR6: Cart persistence: 30-day Redis TTL; cart state written to PostgreSQL on payment initiation as safety net.
NFR7: QR dine-in menu load < 2 seconds on 3G mobile.
NFR8: Mobile checkout: full flow operable on 320px viewport minimum on 3G (1–2 Mbps).
NFR9: Storefront first page load < 200KB total initial payload.
NFR10: OWASP Top 10 addressed; pen-test checklist passed before production launch.
NFR11: Kenya DPA 2019 compliance: VPS Kenya/EAC-hosted; PII encrypted at rest (django-encrypted-fields); audit log on all admin PII access; 72-hour breach notification window; soft-delete + PII anonymisation on deletion.
NFR12: Daraja API rules compliance: HTTPS webhook endpoints with valid SSL; sandbox-first testing; API credentials encrypted, never in source code; transaction logs retained 12 months minimum.
NFR13: Age-restriction enforcement: alcoholic items require `AgeRestrictionLog` entry per order; compliance warning displayed at menu view.
NFR14: Touch targets: 44×44px minimum on storefront; 48×48px in kitchen display, bar admin, and store admin contexts.
NFR15: All list endpoints use `StoreCursorPagination` (cursor-based) — no unbounded list responses, including internal autocomplete and search endpoints.
NFR16: Backend logging: `structlog` only (never `print()` or bare `logging.info()`); PII (phone, email) masked to last 4 digits / hash in all log output.
NFR17: Money stored as `DecimalField(max_digits=10, decimal_places=2)` in DB and as string `"1500.00"` in API responses — never `float`.
NFR18: Datetimes as ISO 8601 UTC in DB and API; never Unix timestamps.
NFR19: Above-fold storefront content (logo, store name, tagline, hero) served SSR/SSG — first painted frame is branded, never a skeleton (trust requirement).
NFR20: No autoplay video on any storefront page.
NFR21: Storefront progressive loading: sections loaded first, menu items lazy-loaded on expand (QR dine-in).
NFR22: Kitchen view response time < 50ms (no multi-table joins; denormalized KitchenTicket JSON).

### Additional Requirements

#### From Architecture

- **Starter template (Epic 1, Story 1):** Backend initialized via `cookiecutter/cookiecutter-django`; storefront and admin each via `npx create-next-app@latest --typescript --tailwind --eslint --app`.
- **Monorepo structure:** `joat_stores/` → `backend/`, `storefront/`, `admin/`, `nginx/`, `scripts/`, `docker-compose.yml`, `docker-compose.prod.yml`.
- **Implementation sequence constraint:** `core/` (TenantModel, TenantQuerySet, TenantMiddleware, JWT) must be fully implemented before any domain app (`store`, `product`, `order`, etc.).
- **Django settings split:** `config/settings/base.py`, `local.py`, `production.py` — never a single `settings.py`.
- **PII encryption:** `django-encrypted-fields` at field level; never encrypt in serializer logic.
- **Soft delete:** `django-safedelete`; PII anonymisation triggered via safedelete hook (never manual override of `delete()`).
- **structlog PII scrubber processor:** Custom processor masks phone/email in all log output.
- **Sentry SDK:** Free tier; exception tracking + async task failure visibility from Day 1.
- **Pillow image pipeline:** Server-side WebP compression; original file deleted from temp storage after compression; only WebP saved to disk.
- **Media storage at MVP:** Local VPS volume + Nginx serving; S3/R2 migration deferred to Phase 2.
- **Per-tenant theming:** CSS variables set by `TenantThemeProvider` from hostname context; never hardcode brand colours in components.
- **Real-time updates (MVP):** Polling only (TanStack Query `refetchInterval: 5000` for kitchen view); no ASGI/WebSockets at MVP. SSE upgrade in Phase 2.
- **Celery task dispatch:** Always `transaction.on_commit(lambda: task.delay(...))` — never call `.delay()` inside an open transaction.
- **Cross-tenant isolation test suite:** Lives in `apps/store/tests/test_middleware.py`; run with `pytest -k "cross_tenant"` as a CI gate.

#### From UX Design

- **M-Pesa STK Push waiting state:** Full-screen modal lock from first "Pay" tap; merchant brand color pulse animation; cycling reassurances ("✓ Your cart is saved" → "✓ Your order number is ready" → "✓ Check your Safaricom phone"); "don't tap again" message; pay button disabled on first tap.
- **Confirmation screen self-recovery:** On any page load post-payment, check localStorage for `pending_payment_order_id`; if found and DB-confirmed, render confirmation screen regardless of navigation path.
- **Idempotent confirmation UI:** Double-landing on confirmation screen shows same order with "Payment already confirmed at [HH:MM]".
- **M-Pesa receipt card UX:** M-Pesa green visual language, transaction ID prominent, screenshot-ready; "Share on WhatsApp" as primary CTA; copyable order summary pre-formatted as WhatsApp commerce message.
- **In-app browser detection:** Detect WhatsApp/Facebook in-app browser; localStorage cart fallback + "open in Chrome" prompt before checkout.
- **QR scan table confirmation:** Always show "You're joining Table [N]'s session at [Store Name]. Is this correct?" before joining — wrong-table guard, not friction.
- **Kitchen display offline states:** "Last updated X seconds ago" timestamp always visible; amber at 15s; full-screen red "CONNECTION LOST — REFRESH NOW" + optional audible alert at 30s; reconnect banner "X orders received while offline".
- **Split-variant ordering:** Quantity > 1 on a menu item surfaces split-variant control ("How do you want these split?") for group dining modifier attribution.
- **Admin mobile-first (budget Android):** Store manager UI primary device is budget Android (Tecno, Infinix, Samsung A-series); 3G-capable; 48×48px tap targets; aggressive data caching.
- **Platform admin desktop-first:** ≥ 1024px breakpoint for investor demo multi-column layout; tenant health grid + GMV chart + onboarding wizard side-by-side.
- **Merchant onboarding "go live" reveal:** Step-by-step narrative flow ending with reveal animation + auto-navigate to new store URL; "first order" milestone highlighted in platform dashboard.
- **Empty states as onboarding:** Every zero-state (empty catalog, no orders, blank kitchen, first admin login) is a teaching moment with a forward-moving CTA.
- **Bar tab audit trail customer-facing:** Item removals show "removed by [staff name]" with timestamp visible to the customer in the bill view.

### FR Coverage Map

```
FR1–FR8:    Epic 1  — Tenant lifecycle, provisioning, middleware, Docker, OpenAPI
FR4:        ⚠️  CROSS-EPIC TEST — Epic 1 implements tenant_type lock guard; Epic 3 must include a test that verifies the guard fires on first order
FR9–FR13:   Epic 4  — Retail catalog, variants, cart (Redis), order lifecycle
FR14:       Epic 2  — M-Pesa STK Push (first defined in Payments Engine epic)
FR15–FR18:  Epic 4  — Guest checkout, confirmation email, image pipeline, card scaffold
FR19–FR27:  Epic 3  — Restaurant: QR tokens, table sessions, menu, kitchen tickets, time-scheduling
FR28–FR33:  Epic 5  — Bar: tabs, rounds, age restriction, happy hour pricing, split settlement
FR34–FR40:  Epic 2  — Payments Engine: idempotency, Daraja webhooks, reconciliation, token cache
FR41–FR45:  Epic 1  — JWT auth, RBAC roles (4 role types), PII audit log
FR46–FR50:  Epic 6  — Celery: 5 named queues, DLQ, exponential backoff, Beat jobs, Flower, health endpoint
            ⚠️  Celery baseline (queues registered + DLQ stub + Flower container) must be in Epic 1 Story 1 before any commerce story ships
FR51–FR57:  Epic 7  — Analytics: daily summaries, peak hours, GMV, TenantHealthSnapshot, AIEvent
FR58–FR63:  Epic 8  — Plans, StoreSubscription lifecycle, usage enforcement, AI scaffold (501s)
FR64–FR66:  Epic 1  — Docker Compose (all services), Nginx per-tenant routing, preflight script
FR67:       Epic 1 (Story 1.1c) — minimal CI gate (linting + tests on PR); full CI/CD pipeline (SSH CD on merge) in Epic 12 (Story 12.1)
FR68:       Epic 12 — Daily pg_dump backup, 7-day rotation
FR69:       Epic 1 (Story 1.1b) — Redis AOF persistence; verified in Epic 12 (Story 12.2)
FR70:       Epic 1  — OpenAPI schema via drf-spectacular

--- New FRs (surfaced in elicitation) ---
FR71:       Epic 1  — Store.currency + Store.payment_methods[] + Store.country + Store.timezone
FR72:       Epic 2  — Payment routing by store.payment_methods (M-Pesa / Stripe / Flutterwave / Cash)
FR73:       Epic 2  — Card payment (Stripe + Flutterwave) live for card-enabled stores
FR74:       Epic 3  — Public menu URL — no QR scan, no table session required
FR75:       Epic 3  — PendingOrder — pre-arrival selection linked to phone/PIN, converts to DineInOrder on seating
FR76:       Epic 3  — Pre-order + advance payment — kitchen fires on waiter seating confirmation
FR77:       Epic 3  — Reservation model — time slot, party size, WhatsApp/SMS confirmation
FR78:       Epic 3  — TableSession.assigned_waiter FK — waiter name on kitchen ticket
FR79:       Epic 6  — Contracting tenant type activates service catalogue, booking, quote flow, job tracking
FR80:       Epic 6  — Service model — fixed price, time slot availability calendar
FR81:       Epic 6  — QuoteRequest → Quote → Job workflow with customer acceptance gate
FR82:       Epic 6  — Job milestones with completion photo upload
FR83:       Epic 6  — Invoice generation from completed job — M-Pesa or card settlement
FR84:       Epic 10 — LoyaltyAccount per customer per store — points balance + history
FR85:       Epic 10 — StampCard — configurable threshold, auto-reward trigger
FR86:       Epic 10 — WhatsApp notifications via Celery engagement queue
FR87:       Epic 10 — Unified customer account — orders, reservations, jobs across all stores
FR88:       Epic 11 — RecommendationEngine using AIEvent history
FR89:       Epic 11 — Peak hour predictions from HourlyOrderSummary
FR90:       Epic 11 — NLP menu search endpoint
FR91:       Epic 2  — Stripe sandbox E2E tests with store currency amounts — Epic 2 acceptance gate
FR92:       Epic 3  — Waiter-facing PendingOrder screen — pull by phone/PIN, one-tap convert
FR93:       Epic 10 — WhatsApp ordering bridge — bot creates PendingOrder, customer gets PIN in reply
FR94:       Epic 3  — Public menu Lighthouse CI gate — < 1.5s on simulated 3G
FR95:       Epic 8  — DailyRevenueSummary.amount_usd — USD normalisation for cross-tenant GMV
FR96:       Epic 9  — Store admin PWA — offline inventory count, sync on reconnect
FR97:       Epic 6  — Quote PDF generation — branded, line-itemised, WhatsApp-shareable
FR98:       Epic 9  — "Powered by joat_stores" viral footer — togglable per plan tier
FR99:       Epic 9  — Data export plan-gated — raw export enterprise-only
FR100:      Epic 1  — Merchant daily view — orders + revenue + pending actions, zero navigation required
FR101:      Epic 3  — PendingOrder.expires_at — 24hr TTL, hourly Celery purge task
```

---

## Epic List

### Epic 1: Multi-Tenant Platform Foundation + Auth
Platform admins can provision stores, configure tenant type, and manage tenant lifecycle. Store staff can authenticate via JWT with role-based access. The full local dev infrastructure (Docker Compose, Nginx, Postgres, Redis) runs from a single command.

**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8, FR41, FR42, FR43, FR44, FR45, FR64, FR65, FR66, FR69, FR70, FR71, FR100
**Key deliverables:** TenantModel + TenantQuerySet + TenantMiddleware, Store provisioning (atomic transaction), stub StoreSubscription + Plan models, JWT with `store_id` + `role` claims, IsStoreScoped permission, Docker Compose (all 9 services), Nginx routing, Redis AOF persistence, preflight script, OpenAPI schema, storefront Next.js shell, admin Next.js shell, minimal CI pipeline (flake8 + black + isort + tsc + pytest on every PR)
**Celery baseline (must ship in Epic 1 Story 1):** Celery app initialized, 5 named queues registered (`order.notifications`, `inventory.alerts`, `billing.reminders`, `payments.reconciliation`, `analytics.reports`), DLQ stub configured, Celery Flower container running — required before any commerce epic can wire async tasks
**FR4 cross-epic note:** `Store.save()` guard implemented here; acceptance test for the guard firing on first order lives in Epic 3

---

### Epic 2: Multi-Provider Payments Engine
Any store can initiate a payment via the correct provider for their country and configuration. Kenya stores use M-Pesa STK Push. Jamaica and international stores use Stripe or Flutterwave card payments. Cash payments are manually confirmed by staff. All paths are idempotent, webhook-verified, and reconciled automatically.

**FRs covered:** FR14, FR34, FR35, FR36, FR37, FR38, FR39, FR40, FR71, FR72, FR73, FR91
**Key deliverables:**
- `apps/payment/providers/` — `mpesa.py` (Daraja), `stripe.py`, `flutterwave.py`, `cash.py`
- `apps/payment/services.py` — `initiate_payment(store, method, amount, reference)` routes to correct provider based on `store.payment_methods`
- `MpesaTransaction` model (unique receipt, EXPIRED vs FAILED logic, Redis token cache TTL 3500s)
- HMAC webhook verification for all provider callbacks
- Celery Beat `reconcile_payments` task
- Reversal endpoint (24hr window)
- Stripe sandbox E2E tests with JMD amounts before epic closes (FR91)
- Multi-currency: amounts stored and returned in `store.currency`
- Split payment across methods (e.g. half M-Pesa, half card)
**Payment service interface (explicit deliverable):** `initiate_payment()` is the ONLY entry point for all commerce verticals. Epics 3, 4, 5, and 6 never call provider clients directly.
**Note:** Epics 3, 4, 5, and 6 all depend on this epic being complete.

---

### Epic 3: Restaurant Full-Service
A customer's full restaurant journey — from browsing the menu at home before arriving, to pre-selecting items, booking a table, being seated by an assigned waiter, ordering, kitchen processing, and paying the bill. Supports QR walk-in, pre-arrival, and takeaway order types across Kenya (M-Pesa) and Jamaica (card).

**FRs covered:** FR19, FR20, FR21, FR22, FR23, FR24, FR25, FR26, FR27, FR74, FR75, FR76, FR77, FR78, FR92, FR94, FR101
**Key deliverables:**
- HMAC-signed QR token generation + validation
- `Table` + `TableSession` state machine (OPEN→BILL_REQUESTED→CLOSED)
- `TableSession.assigned_waiter` FK — kitchen ticket includes waiter name (FR78)
- `MenuSection` + `MenuItem` + `ModifierGroup` + `Modifier` models — modifier flags BOLD above item name on ticket
- `DineInOrder` + `DineInOrderItem` + `KitchenTicket` (denormalized JSON, < 50ms)
- Time-based menu scheduling — out-of-window items auto-hidden
- **Public menu URL** `/{store_slug}/menu/` — no QR, no session, browsable by anyone (FR74)
- **`PendingOrder` model** — pre-arrival selection linked to phone + 6-digit PIN, 24hr TTL (FR75, FR101)
- **Waiter screen** — pull PendingOrder by phone/PIN, one-tap convert to `DineInOrder` (FR92)
- **Pre-order + advance pay** — full order + payment before arriving, kitchen fires on waiter confirmation (FR76)
- **`Reservation` model** — time slot, party size, PENDING/CONFIRMED/SEATED/NO_SHOW, WhatsApp/SMS confirmation (FR77)
- **Takeaway order type** — online order + pay, pickup reference number (FR21)
- Public menu Lighthouse CI gate — < 1.5s on simulated 3G (FR94)
- Celery Beat hourly purge of expired PendingOrders (FR101)
**QR wrong-table path (dedicated story):** invalid token → friendly error, expired → re-scan prompt, "No, wrong table" → correction flow with fallback URL `/t/{table_id}`. Trust-critical — never bundle into happy path story.
**FR4 cross-epic test:** Test that `Store.save()` raises `IntegrityError` when `tenant_type` changes after first `DineInOrder`.
**Depends on:** Epic 1 (platform foundation), Epic 2 (payments engine)

---

### Epic 4: Retail Store Commerce
A retail customer browses a product catalog with variants, adds items to a persistent cart (Redis, 30-day TTL), and completes checkout as a guest or authenticated user via M-Pesa STK Push.

**FRs covered:** FR9, FR10, FR11, FR12, FR13, FR15, FR16, FR17, FR18
**Key deliverables:** Product + Category + Variant + Inventory models, Redis cart (30-day TTL, guest + auth), Order lifecycle state machine (pending→confirmed→fulfilled→completed), guest checkout, Google OAuth2 PKCE, order confirmation email (Celery), low-stock alerts (Celery), Pillow WebP image pipeline, card payment scaffold (501)
**Depends on:** Epic 1 (platform foundation), Epic 2 (M-Pesa engine)

---

### Epic 5: Bar Tab Management
A bar customer opens a tab, orders rounds without re-authentication, age-restricted items require acknowledgement, happy hour pricing is snapshotted at add-time, and the final bill can be split across multiple payers via M-Pesa.

**FRs covered:** FR28, FR29, FR30, FR31, FR32, FR33
**Key deliverables:** Tab state machine (OPEN→BILL_REQUESTED→SETTLED), round ordering on existing tab, AgeRestrictionLog model + enforcement, HappyHour pricing model + snapshot logic (never recalculate at settlement), split-pay M-Pesa (individual STK Push per person), "HH" badge + first full-price item notice, item removal audit trail (visible to customer in bill)
**Depends on:** Epic 1 (platform foundation), Epic 2 (M-Pesa engine), Epic 3 (restaurant base — `apps/restaurant/` must be active)

---

### Epic 6: Contracting Module
A contractor lists services and sets availability. Customers book fixed-price jobs or request quotes with photos. Contractor accepts, tracks milestones, uploads completion photos, and collects payment via M-Pesa or card. Branded PDF invoices are WhatsApp-shareable.

**FRs covered:** FR79, FR80, FR81, FR82, FR83, FR97
**Key deliverables:**
- `contracting` as 4th tenant type activating this module
- `Service` model — name, description, base_price, duration_estimate, category, time slot availability calendar
- `ServiceBooking` model — customer, service, time_slot, status (PENDING/CONFIRMED/IN_PROGRESS/COMPLETED)
- `QuoteRequest` model — customer description + photo uploads, status (OPEN/QUOTED/ACCEPTED/REJECTED)
- `Quote` model — line items, total, valid_until date
- `Job` model — from booking or quote, assigned_worker, milestones, status
- `JobMilestone` model — description, due_date, completion_photo, status
- `Invoice` model — job, line items, total, payment_status — generates branded PDF (FR97)
- PDF generation via WeasyPrint/ReportLab with store logo + line items — WhatsApp-shareable link
- Payment collection via `initiate_payment()` (Epic 2 service interface)
**Depends on:** Epic 1 (platform foundation), Epic 2 (payments engine)

---

### Epic 7: Reliable Async Operations
Order confirmations, inventory alerts, billing reminders, and payment reconciliation are delivered reliably via named Celery queues with DLQ protection, exponential backoff, and full operational visibility through Celery Flower.

**FRs covered:** FR46, FR47, FR48, FR49, FR50
**Key deliverables:** 5 named queues (`order.notifications`, `inventory.alerts`, `billing.reminders`, `payments.reconciliation`, `analytics.reports`), DLQ configuration, exponential backoff (max 5 retries, `60 * 2**retries`), Celery Beat schedule (daily reconciliation, weekly digest, renewal reminder), `/health/workers/` endpoint (queue depth + last heartbeat), Celery Flower Docker service
**Note:** Basic Celery wiring exists in Epics 2–4 (STK callbacks, notifications). This epic adds full production hardening.

---

### Epic 8: Merchant Analytics Dashboard
Store owners see yesterday's revenue, order count, AOV, and top products. Restaurant owners see peak hours and table turn rate. Bar owners see tab completion rate and occupancy. Platform admin sees combined GMV, per-tenant health snapshots, and unit economics.

**FRs covered:** FR51, FR52, FR53, FR54, FR55, FR56, FR57, FR95
**Key deliverables:** `DailyRevenueSummary` + `HourlyOrderSummary` pre-aggregated models, Celery Beat `generate_daily_summary` (runs 00:05 daily), `TenantHealthSnapshot` model, `AIEvent` append-only capture (product views, cart adds, searches, order completions), analytics API endpoints (read from pre-aggregated tables — no live ORM joins), per-store and platform-admin dashboard views

---

### Epic 9: SaaS Plans + Subscription Management
Merchants subscribe to a plan that enforces feature limits server-side on every request. Trial, grace period, suspension, and cancellation are fully automated. M-Pesa subscription renewal is triggered via Celery Beat.

**FRs covered:** FR58, FR59, FR60, FR61, FR62, FR63
**Key deliverables:** `Plan` model (all 10 fields), `StoreSubscription` state machine (trial→active→past_due→suspended→cancelled), 14-day trial + 7-day grace period, `enforce_plan_limit()` in `apps/saas/services.py`, M-Pesa subscription renewal flow (separate callback + Celery queue from customer checkout), `apps/ai/` scaffold with 501 endpoints gated on `plan.features.has_ai`, merchant onboarding runbook

---

### Epic 10: Customer Loyalty + Engagement
Repeat customers earn points and stamp rewards at any store. A unified customer account shows all their orders, reservations, and jobs across stores. WhatsApp notifications keep them informed without requiring app downloads. A WhatsApp ordering bridge lets customers order by message.

**FRs covered:** FR84, FR85, FR86, FR87, FR93, FR98
**Key deliverables:**
- `LoyaltyAccount` model per customer per store — points balance + transaction history (FR84)
- `StampCard` model — configurable threshold, auto-reward trigger on completion (FR85)
- WhatsApp notification dispatch via Celery `engagement.notifications` queue (FR86)
- Unified customer account — single login, view all orders/reservations/jobs across all stores (FR87)
- WhatsApp ordering bridge — bot creates `PendingOrder` from menu item name, returns 6-digit PIN (FR93)
- "Powered by joat_stores" viral footer — togglable per plan tier, links to merchant signup (FR98)
**Depends on:** Epic 1, Epic 2, Epic 3

---

### Epic 11: AI + Personalization
Menu recommendations, peak hour predictions, and natural language menu search — all gated behind `plan.features.has_ai`. Built on the `AIEvent` data captured from day one.

**FRs covered:** FR88, FR89, FR90
**Key deliverables:**
- `RecommendationEngine` — uses `AIEvent` history to suggest menu items per customer (FR88)
- Peak hour predictions from `HourlyOrderSummary` — staffing suggestions in merchant analytics (FR89)
- NLP menu search `GET /api/v1/restaurant/menu/search/?q=` — natural language query (FR90)
- All endpoints gated on `plan.features.has_ai == True` — returns 403 for non-AI plans
**Depends on:** Epic 7 (async), Epic 8 (analytics data), Epic 9 (plan gating)

---

### Epic 12: Production Hardening
Every PR runs a full CI gate (lint + types + tests). Deployments are automated on merge. Daily backups run with 7-day rotation. The platform passes an OWASP Top 10 checklist and Kenya DPA 2019 compliance review.

**FRs covered:** FR67, FR68, FR96, FR99, FR100
**Note:** FR69 (Redis AOF persistence) is implemented in Epic 1 Story 1.1b and verified here in Story 12.2
**NFRs addressed:** NFR1–NFR22 (full non-functional requirement coverage)
**Key deliverables:**
- GitHub Actions CI (`flake8` + `black` + `isort` + TypeScript strict + `pytest`), SSH CD on merge to main
- `scripts/backup.sh` (pg_dump → gzip, 7-day rotation, Celery Beat triggered)
- Redis AOF persistence enabled
- Cross-tenant isolation test suite (`pytest -k "cross_tenant"` as CI gate)
- OWASP Top 10 checklist + Kenya DPA 2019 compliance (PII encryption, 72hr breach window, soft-delete + anonymisation)
- Sentry SDK + structlog PII scrubber processor
- Store admin PWA — offline inventory count, sync on reconnect (FR96)
- Data export plan-gated — raw export enterprise-only (FR99)
- Merchant daily view — orders + revenue + pending actions, zero navigation (FR100)

---

## Epic 1: Multi-Tenant Platform Foundation + Auth

Platform admins can provision stores, configure tenant type, and manage tenant lifecycle. Store staff can authenticate via JWT with role-based access. The full local dev infrastructure (Docker Compose, Nginx, Postgres, Redis) runs from a single command.

### Story 1.1: Monorepo Scaffold + App Bootstrapping

As a platform engineer,
I want the monorepo structure and all three applications initialized from canonical templates,
So that the codebase starts from a clean, convention-compliant foundation before any Docker or infrastructure work begins.

**Acceptance Criteria:**

**Given** the monorepo root is created
**When** the directory structure is inspected
**Then** the following exist: `backend/`, `storefront/`, `admin/`, `nginx/`, `scripts/`, `docker-compose.yml`, `docker-compose.prod.yml`

**Given** `backend/` is initialized
**When** the Django project is bootstrapped
**Then** `cookiecutter-django` is used and the settings are split into `config/settings/base.py`, `config/settings/local.py`, `config/settings/production.py` — never a single `settings.py`
**And** `apps/` directory exists with placeholder packages for: `store`, `payment`, `product`, `order`, `restaurant`, `bar`, `contracting`, `saas`, `analytics`, `ai`, `loyalty`

**Given** `storefront/` and `admin/` are initialized
**When** each is bootstrapped
**Then** each uses `npx create-next-app@latest --typescript --tailwind --eslint --app`
**And** `storefront/` has a `TenantThemeProvider` shell that reads CSS variables from hostname context — brand colours never hardcoded in components

**Given** `scripts/preflight.sh` is created
**When** inspected
**Then** it checks for all required env vars (`DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `DARAJA_CONSUMER_KEY`, `DARAJA_CONSUMER_SECRET`) and exits non-zero with the missing variable name if any are absent

### Story 1.1b: Docker Compose + All Services + Celery Baseline

As a platform engineer,
I want the full local development environment to start from a single `docker compose up` command with Celery fully wired,
So that any developer can onboard without manual environment configuration and all commerce epics can immediately wire async tasks.

**Acceptance Criteria:**

**Given** `scripts/preflight.sh` passes and `docker compose up --build` is run
**When** all containers start
**Then** all 9 services are healthy: Django API (port 8000), PostgreSQL, Redis, Celery worker, Celery Beat, Celery Flower (port 5555), Next.js storefront (port 3000), Next.js admin (port 3001), Nginx (port 80)
**And** `GET http://localhost/health/` returns HTTP 200

**Given** the Celery configuration in `backend/`
**When** the Celery worker starts
**Then** all 5 named queues are registered and visible in Celery Flower: `order.notifications`, `inventory.alerts`, `billing.reminders`, `payments.reconciliation`, `analytics.reports`
**And** a DLQ stub is configured with exponential backoff policy (max 5 retries, `countdown = 60 * (2 ** retries)`)
**And** Celery Flower is accessible at `http://localhost:5555`

**Given** `scripts/preflight.sh` is run before `docker compose up`
**When** any required env var is missing
**Then** the script exits non-zero and `docker compose up` is blocked until preflight passes

**Given** a new tenant domain config file is added to `nginx/conf.d/tenants/` and Nginx is reloaded
**When** a request arrives for that domain
**Then** it is proxied to the shared Next.js storefront

**Given** Redis is running in Docker
**When** the Redis container restarts
**Then** AOF persistence (`appendonly yes`, `appendfsync everysec`) is enabled and data is not lost

### Story 1.1c: Minimal CI Pipeline (Linting + Tests on PR)

As a developer,
I want every pull request to run automated linting and tests,
So that code quality is enforced from the first commit and regressions are caught before they reach main.

**Acceptance Criteria:**

**Given** a pull request is opened or updated against `main`
**When** the GitHub Actions CI workflow runs
**Then** the following steps execute in order: `flake8` (Python linting), `black --check` (formatting), `isort --check` (import order), TypeScript strict compile (`tsc --noEmit` on both `storefront/` and `admin/`), `pytest` (full Django test suite)
**And** the PR is blocked from merging if any step fails

**Given** a `flake8` violation is introduced in any Python file
**When** CI runs
**Then** the pipeline fails with a clear error identifying the file and line number

**Given** `black --check` detects unformatted Python code
**When** CI runs
**Then** the pipeline fails — developers must run `black .` locally before pushing

**Given** the TypeScript compiler detects a type error in `storefront/` or `admin/`
**When** CI runs
**Then** the pipeline fails with the TypeScript error output

**Given** a `pytest` test fails
**When** CI runs
**Then** the pipeline fails and the failing test name and traceback are visible in the CI log

**Note:** This story covers linting + test gates only. SSH-based CD (deploy on merge to main) and the full pipeline (including `docker compose` rollout) are implemented in Epic 12 Story 12.1. A `.pre-commit-config.yaml` with matching hooks may optionally be added locally — not a CI requirement but recommended for solo developers.

### Story 1.2: Core Store Model + Tenant Middleware

As a platform engineer,
I want every incoming request to have `request.store` resolved before any business logic executes,
So that all downstream code can trust the tenant context without re-querying.

**Acceptance Criteria:**

**Given** the `Store` model is created
**When** the schema is inspected
**Then** it has fields: `name`, `slug`, `domain`, `tenant_type` (choices: `retail`, `restaurant`, `bar`, `contracting`), `status` (choices: `pending`, `active`, `suspended`, `cancelled`), `currency` (ISO 4217), `payment_methods` (ArrayField), `country` (ISO 3166-1 alpha-2), `timezone` (IANA tz string)
**And** `TenantQuerySet` is set as the default manager
**And** `Store` uses `django-safedelete` for soft deletion with PII anonymisation triggered via safedelete hook

**Given** a request arrives with `Host: techstore.joat.com`
**When** `TenantMiddleware` processes it
**Then** `request.store` is set to the matching `Store` object before any view logic runs

**Given** a request arrives with header `X-Store-ID: <uuid>`
**When** `TenantMiddleware` processes it
**Then** `request.store` is resolved from the UUID and set on the request

**Given** no matching store is found for the domain or header
**When** `TenantMiddleware` processes the request
**Then** HTTP 404 is returned before any view is reached

**Given** a `Store` with `status = 'suspended'`
**When** a request arrives for that store's domain
**Then** the storefront returns HTTP 503

**Given** `Store.save()` is called to change `tenant_type`
**When** that store already has at least one associated order of any type
**Then** `IntegrityError` is raised and the save is aborted
**And** the `tenant_type` value in the database remains unchanged

**Given** a request arrives for `admin.joat.com`, `api.joat.com`, or any platform-level subdomain
**When** `TenantMiddleware` processes it
**Then** store resolution is skipped entirely — these subdomains are identified by a configurable prefix allowlist and routed directly to platform views
**And** no `Store` lookup is performed and `request.store` is not set

### Story 1.3: Tenant Isolation Layers

As a store staff member,
I want all API responses to only ever contain data belonging to my store,
So that I can never accidentally see or modify another tenant's data.

**Acceptance Criteria:**

**Given** any API endpoint that returns store-scoped data
**When** `IsStoreScoped` permission class is applied and the authenticated user's `store_id` JWT claim does not match `request.store.id`
**Then** HTTP 403 is returned

**Given** any DRF serializer inheriting from the store-scoped serializer mixin
**When** a create or update operation is performed
**Then** the `store` field is automatically populated from `request.store` and cannot be overridden by client-supplied data

**Given** any Django admin class inheriting from `StoreAdmin`
**When** a store staff member views any list or detail page
**Then** only records belonging to their own store are returned — no cross-tenant data ever visible

**Given** a `TenantQuerySet` applied as default manager on any model
**When** a cross-tenant `.get(id=<other_store_record_id>)` is attempted
**Then** `DoesNotExist` is raised rather than the record being returned

**Given** the cross-tenant isolation test suite at `apps/store/tests/test_middleware.py`
**When** `pytest -k "cross_tenant"` is run
**Then** all tests pass, covering: middleware resolution, queryset filtering, permission enforcement, serializer auto-population
**And** this suite is registered as a CI gate on every PR touching models or views

**Given** any model that is accessible via a public-facing API endpoint
**When** its primary key is inspected
**Then** it is a UUID — auto-incrementing integer IDs are never exposed in any API response or URL path
**And** this is enforced by a base `TenantModel` class that sets `id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`

### Story 1.4: Atomic Store Provisioning API

As a platform admin,
I want to provision a new store through a single API call that either fully succeeds or fully rolls back,
So that the platform never has stores in a partially configured state.

**Acceptance Criteria:**

**Given** a `POST /api/v1/platform/stores/` request with valid payload (name, domain, tenant_type, currency, country, timezone, payment_methods, owner email)
**When** the provisioning sequence runs inside `transaction.atomic()`
**Then** all of the following are created atomically: `Store` record, domain assignment, `StoreSubscription` (status: `trial`), `store_owner` user with `store_owner` role
**And** HTTP 201 is returned with the full store detail

**Given** any step in the provisioning sequence fails (e.g. domain conflict, invalid email)
**When** the transaction rolls back
**Then** no partial records exist in the database
**And** HTTP 400 or HTTP 409 is returned with a specific error identifying the failure point

**Given** `GET /api/v1/platform/stores/` accessed by a platform admin
**When** the response is returned
**Then** all tenants are listed with: name, domain, tenant_type, status, subscription status
**And** no store-scoped user (store_owner, store_manager, customer) can access this endpoint — HTTP 403

**Given** `PATCH /api/v1/platform/stores/{id}/status/` with a valid transition (`pending→active`, `active→suspended`, `suspended→cancelled`)
**When** the transition is applied
**Then** the status is updated and a `StoreStatusChanged` event is logged
**And** invalid transitions return HTTP 422 with `INVALID_STATUS_TRANSITION`

**Given** this is the first story that creates `StoreSubscription` records, and `StoreSubscription` + `Plan` are formally completed in Epic 9,
**When** this story is implemented
**Then** a stub `StoreSubscription` model is created in `apps/saas/models.py` with fields: `store` (OneToOneField), `status` (CharField, default='trial')
**And** a stub `Plan` model is created with field: `api_rate_limit` (IntegerField, default=100) — nullable FK from StoreSubscription
**And** these stubs are intentionally minimal; Epic 9 adds the full lifecycle (trial→active→past_due→suspended→cancelled), all remaining Plan fields, and `enforce_plan_limit()` service
**And** `request.store.subscription.plan.api_rate_limit` in Story 1.5 returns the plan value or the default 100 when plan is null

### Story 1.5: JWT Auth + RBAC (4 Roles)

As a store staff member or customer,
I want to authenticate and receive a JWT that encodes my role and store context,
So that every API request I make is automatically scoped to the correct permissions.

**Acceptance Criteria:**

**Given** a valid `POST /api/v1/auth/token/` request
**When** credentials are verified
**Then** an access token is returned in the response body and a refresh token is set as an `httpOnly` cookie — never in the response body
**And** the access token payload contains `store_id` and `role` claims
**And** `role` is one of: `platform_admin`, `store_owner`, `store_manager`, `customer`

**Given** an authenticated request with a valid JWT
**When** any protected endpoint is accessed
**Then** RBAC is enforced from JWT claims only — never from `is_staff`, Django groups, or session data

**Given** a `platform_admin` JWT (no `store_id` claim)
**When** the request is processed by `TenantMiddleware`
**Then** store resolution is skipped and the request proceeds with full platform visibility

**Given** `request.store.subscription.plan.api_rate_limit`
**When** any API request is made
**Then** rate limiting is enforced server-side from the plan value — never hardcoded
**And** exceeding the limit returns HTTP 429 with `RATE_LIMIT_EXCEEDED`

**Given** a plan-gated feature is accessed (e.g. analytics, AI, custom domain)
**When** the feature is not available on the store's current plan
**Then** HTTP 403 is returned with `PLAN_FEATURE_UNAVAILABLE`
**And** the feature flag is evaluated from `request.store.subscription.plan` on every request — never from a cached JWT claim

**Given** `POST /api/v1/auth/token/refresh/` with a valid refresh token cookie
**When** the token is refreshed
**Then** a new access token is returned and the refresh token cookie is rotated
**And** absent, expired, or tampered refresh tokens return HTTP 401

**Given** a refresh token is used more than once (detected via token family tracking)
**When** the second use is detected
**Then** all refresh tokens in that family are immediately invalidated (token family invalidation)
**And** the user is forced to re-authenticate — this is the primary stolen-token defence

**Given** `POST /api/v1/auth/logout-all/` is called by an authenticated user
**When** the request is processed
**Then** all active refresh tokens for that user across all devices are invalidated
**And** subsequent refresh attempts with any of the invalidated tokens return HTTP 401

### Story 1.6: PII Audit Log + OpenAPI Schema

As a platform admin responsible for Kenya DPA 2019 compliance,
I want every admin access to customer PII to be automatically logged and every API endpoint to be documented via OpenAPI,
So that we have a full audit trail and developer-facing API documentation from day one.

**Acceptance Criteria:**

**Given** an admin user accesses any endpoint or admin action returning customer PII (phone, email, address)
**When** the request is processed
**Then** an `AdminPIIAccessLog(user, store, record_type, record_id, accessed_at)` record is created automatically via signal or decorator — never manual per-view code
**And** the log entry is created even if the request returns an error

**Given** any log output from structlog anywhere in the backend
**When** a customer phone number or email address would appear
**Then** the structlog PII scrubber processor masks it: phone → last 4 digits (`****1234`), email → hashed prefix (`a3f2...@domain.com`)
**And** `print()` and bare `logging.info()` calls are forbidden and enforced via `flake8` in CI

**Given** `drf-spectacular` is installed and configured
**When** `GET /api/schema/` is accessed
**Then** a valid OpenAPI 3.x schema is returned covering all registered endpoints
**And** `GET /api/docs/` serves the Swagger UI

**Given** any new API endpoint is added
**When** `./manage.py spectacular --validate` is run in CI
**Then** the schema validates without errors

**Given** the `AdminPIIAccessLog` table exists in PostgreSQL
**When** the DB role used by the Django application is inspected
**Then** it has INSERT-only privileges on `AdminPIIAccessLog` — no UPDATE or DELETE granted to any application role
**And** this constraint is verified in the Story 12.3 compliance review as a Kenya DPA 2019 audit integrity control

### Story 1.7: Storefront Next.js Shell + Tenant Branding

As a customer visiting any joat_stores-powered storefront,
I want to land on a fully branded page that loads the correct store's identity immediately,
So that I trust I am in the right place before I see a single product.

**Acceptance Criteria:**

**Given** `GET /api/v1/store/branding/` is called (resolved by `TenantMiddleware` from the incoming domain)
**When** the response is returned
**Then** it includes: `store_name`, `logo_url` (WebP), `tagline`, `primary_color`, `secondary_color`, `currency`, `country`
**And** this endpoint requires no authentication — publicly accessible for SSR

**Given** the storefront `app/layout.tsx` renders
**When** the page is server-side rendered
**Then** `TenantThemeProvider` injects CSS variables (`--color-primary`, `--color-secondary`, `--font-family`) from the branding API response
**And** above-fold content (store name, logo, tagline) is painted on the first server-rendered frame — never a skeleton or blank white flash

**Given** a `Store` with `status='suspended'`
**When** its storefront domain is visited
**Then** a branded 503 page is rendered SSR with the store name visible — never a generic server error

**Given** the storefront base layout renders on any page
**When** inspected
**Then** it includes: persistent header (logo + store name + cart icon), main content slot, footer with plan-gated "Powered by joat_stores" slot (empty if plan disables it)
**And** the layout is fully responsive from 320px to 1440px with no horizontal overflow at any breakpoint
**And** no autoplay video exists on any storefront page — enforced via code review checklist in CI

**Given** the product listing page shell (`/` or `/products/`) renders
**When** no products exist yet
**Then** an empty state is shown: "Products coming soon — check back shortly." with the store logo visible
**And** the page structure (grid slots) is present so product cards snap in without layout shift when Story 4.1 is implemented

**Given** the storefront is accessed on a 3G connection
**When** the initial page load completes
**Then** total initial payload is under 200KB (SSR HTML + critical CSS + no blocking JS)

### Story 1.8: Admin Next.js Shell + Authenticated Layout

As a store owner, store manager, or platform admin,
I want a secure login page and a role-aware admin shell that I land in immediately after authentication,
So that I can access my tools without friction and without ever seeing another tenant's navigation.

**Acceptance Criteria:**

**Given** an unauthenticated user visits any admin route
**When** the request is processed
**Then** they are redirected to `/login` immediately — no admin content is rendered or leaked

**Given** the login page at `/login` renders
**When** a store staff member submits valid credentials
**Then** `POST /api/v1/auth/token/` is called, the access token is stored in memory (never `localStorage`), and the `httpOnly` refresh token cookie is set
**And** the user is redirected to the dashboard appropriate for their role: `platform_admin` → `/platform/`, `store_owner` / `store_manager` → `/dashboard/`

**Given** invalid credentials are submitted
**When** the login request returns HTTP 401
**Then** the error message is: "Incorrect email or password." — no indication of whether the email exists (prevents enumeration)

**Given** an authenticated `store_owner` or `store_manager` views the admin shell
**When** the layout renders
**Then** the sidebar shows only store-scoped navigation items: Dashboard, Orders, Products, Customers, Analytics, Settings
**And** the header displays the store name and a Logout button

**Given** an authenticated `platform_admin` views the admin shell
**When** the layout renders
**Then** the sidebar shows platform-scoped navigation: Stores, Analytics, Plans, System Health
**And** no store-specific items appear — platform admin has no store context

**Given** the Logout button is tapped
**When** clicked
**Then** `POST /api/v1/auth/logout-all/` is called, the access token is cleared from memory, the refresh cookie is cleared, and the user is redirected to `/login`

**Given** an API call returns HTTP 401 (expired access token)
**When** detected by the frontend API client
**Then** `POST /api/v1/auth/token/refresh/` is called automatically using the refresh cookie
**And** if refresh also fails (cookie expired or revoked), the user is redirected to `/login` with session expiry message

**Given** the admin shell loads on a budget Android device (Tecno, Infinix, Samsung A-series)
**When** rendered
**Then** all sidebar navigation items have minimum 48×48px tap targets
**And** the layout is usable at 320px width — sidebar collapses to a hamburger menu on mobile

---

## Epic 2: Multi-Provider Payments Engine

Any store can initiate a payment via the correct provider for their country and configuration. Kenya stores use M-Pesa STK Push. International stores use Stripe or Flutterwave card payments. Cash payments are manually confirmed by staff. All paths are idempotent, webhook-verified, and reconciled automatically.

### Story 2.0: Phone Number Normalization + Validation Service

As a payment system,
I want all phone numbers normalized to E.164 format before any M-Pesa or SMS operation,
So that Kenyan numbers in any local format (`07XX`, `+254XX`, `254XX`) always reach Daraja correctly.

**Acceptance Criteria:**

**Given** `normalize_phone(raw_phone, country_code='KE')` is called in `apps/payment/phone.py`
**When** the input is `0712345678`
**Then** the output is `+254712345678`

**Given** the input is `254712345678` (without leading `+`)
**When** normalized
**Then** the output is `+254712345678`

**Given** the input is `+254712345678` (already E.164)
**When** normalized
**Then** the output is `+254712345678` unchanged

**Given** the input is `0812345678` (invalid Kenyan prefix)
**When** normalized
**Then** `PhoneNormalizationError` is raised with a descriptive message — never passed to Daraja

**Given** a Jamaican store with `country='JM'`
**When** `normalize_phone('8761234567', country_code='JM')` is called
**Then** the output is `+18761234567` (JM country code +1-876)

**Given** `normalize_phone()` is called
**When** any payment or SMS notification flow passes a phone number
**Then** it always passes through `normalize_phone()` first — raw phone strings never reach Daraja, WhatsApp, or SMS APIs directly

### Story 2.1: Daraja Client + OAuth Token Cache

As a payment system,
I want the Daraja OAuth2 access token to be cached in Redis rather than fetched per transaction,
So that every STK Push is fast and we never hit Daraja rate limits on token endpoints.

**Acceptance Criteria:**

**Given** the Daraja client in `apps/payment/daraja.py` is initialized
**When** an access token is needed for any Daraja API call
**Then** the token is fetched from Redis at key `daraja:access_token:{env}` with TTL 3500s
**And** if the key is missing or expired, a new token is fetched from Daraja OAuth2 and cached — never fetched per STK Push call

**Given** the Daraja client is called simultaneously by multiple Celery workers
**When** the Redis token key is absent
**Then** only one worker fetches a new token (Redis SET NX or equivalent lock) and the others wait then read from cache

**Given** the Daraja sandbox environment is configured (`env=sandbox`)
**When** the client initializes
**Then** all API calls target `sandbox.safaricom.co.ke` endpoints
**And** switching to `env=production` targets `api.safaricom.co.ke` with no code changes

**Given** Daraja API credentials (consumer key, consumer secret)
**When** they are loaded by the client
**Then** they are read from environment variables — never hardcoded in source code

**Given** Redis is unavailable when the Daraja client needs an access token
**When** the token fetch is attempted
**Then** the client falls back to a single direct token fetch from Daraja with a 5-second timeout
**And** a Sentry alert is raised immediately noting Redis unavailability — never a silent failure
**And** the fallback token is not cached (no Redis write attempted during the outage)

### Story 2.2: M-Pesa STK Push Initiation + Idempotency

As a customer at checkout,
I want a payment prompt sent to my Safaricom phone immediately when I tap Pay,
So that I can authorize payment without leaving the storefront.

**Acceptance Criteria:**

**Given** `initiate_payment(store, method='mpesa', amount, phone, reference)` is called
**When** an existing `MpesaTransaction` for the same `reference` is in `pending` or `confirmed` status
**Then** no new STK Push is initiated and the existing payment record is returned
**And** the response includes the existing transaction ID and status

**Given** no existing pending transaction exists for the reference
**When** `initiate_payment()` is called with `method='mpesa'`
**Then** a Daraja STK Push request is initiated
**And** a `MpesaTransaction` record is created with status `STK_PUSH_INITIATED`
**And** the customer receives a payment prompt on their Safaricom phone within 5 seconds

**Given** the STK Push is initiated successfully
**When** the Daraja API returns a `CheckoutRequestID`
**Then** it is stored on the `MpesaTransaction` record for webhook correlation

**Given** `initiate_payment()` is the ONLY entry point for all payment flows
**When** any commerce vertical (retail checkout, restaurant bill, bar tab, subscription renewal) initiates a payment
**Then** it calls `apps/payment/services.initiate_payment()` — never calling Daraja or any provider client directly

**Given** the idempotency check in `initiate_payment()` for an existing pending transaction
**When** two concurrent requests for the same order reference arrive simultaneously
**Then** the check uses `SELECT FOR UPDATE` (or equivalent DB-level lock) to prevent a race condition that would create two STK Push initiations
**And** only one `MpesaTransaction` record is ever created per order reference

**Given** a phone number is supplied to `initiate_payment()`
**When** it is passed to the phone normalization service (Story 2.7)
**Then** it is normalized to E.164 format (`+254XXXXXXXXX`) before being sent to Daraja
**And** if normalization fails (unrecognizable format), HTTP 422 is returned with `INVALID_PHONE_NUMBER` before any Daraja call is made

**Given** a customer initiates STK Push for the same order more than 3 times within one hour
**When** the 4th initiation attempt is made
**Then** HTTP 429 is returned with `STK_PUSH_RATE_LIMITED` and a retry-after timestamp
**And** no Daraja API call is made for the blocked request

### Story 2.3: Daraja Webhook Processing + Receipt Idempotency

As a payment system,
I want all Daraja webhook callbacks to be HMAC-verified and deduplicated,
So that duplicate callbacks never result in double-confirmed orders or retry storms.

**Acceptance Criteria:**

**Given** a webhook callback arrives at the Daraja callback endpoint
**When** the HMAC signature is verified
**Then** only callbacks with a valid signature are processed — `ResultCode == 0` alone is not sufficient for acceptance

**Given** a webhook with an invalid or missing HMAC signature arrives
**When** it is processed
**Then** HTTP 400 is returned and no payment record is updated

**Given** a successful callback (`ResultCode == 0`) with a valid `mpesa_receipt_number`
**When** the `MpesaTransaction` is updated
**Then** `MpesaTransaction.mpesa_receipt_number` is stored with `unique=True` DB constraint enforced
**And** the associated order or tab status is updated to `confirmed`

**Given** a duplicate webhook arrives with an already-stored `mpesa_receipt_number`
**When** it is processed
**Then** HTTP 200 is returned (never 4xx) to prevent Daraja retry storms
**And** no duplicate payment record or status change occurs

### Story 2.4: STK Push Timeout + EXPIRED Status

As a customer,
I want to see a clear retry prompt if my M-Pesa payment times out,
So that I know my cart is safe and can try again without re-entering my details.

**Acceptance Criteria:**

**Given** a Daraja callback arrives with `ResultCode: 1032` (user cancelled) or `ResultCode: 1037` (timeout)
**When** the `MpesaTransaction` is updated
**Then** the status is set to `EXPIRED` — never `FAILED`
**And** the associated order status remains `PENDING` — not cancelled

**Given** a `MpesaTransaction` is in `EXPIRED` status
**When** the customer views the checkout or order status page
**Then** a retry prompt is displayed: "Payment timed out — tap to try again"
**And** tapping retry calls `initiate_payment()` which initiates a fresh STK Push for the same order

**Given** a `MpesaTransaction` in `STK_PUSH_INITIATED` status older than 2 hours
**When** the Celery Beat `reconcile_payments` task runs
**Then** its status is updated by querying the Daraja Transaction Status API
**And** if Daraja confirms timeout, the status is updated to `EXPIRED`

### Story 2.5: Payment Reconciliation + Reversal

As a platform operator,
I want failed or stale payment records to be automatically reconciled daily and reversals to create a clean audit trail,
So that our payment ledger is always accurate without manual intervention.

**Acceptance Criteria:**

**Given** the Celery Beat schedule is configured
**When** the daily `reconcile_payments` task runs
**Then** all `MpesaTransaction` records in `STK_PUSH_INITIATED` status older than 2 hours are queried against the Daraja Transaction Status API
**And** each is updated to its correct final status (`confirmed`, `EXPIRED`, or `FAILED`)

**Given** a `POST /api/v1/payments/{id}/reverse/` request within 24 hours of the original payment
**When** the reversal is processed
**Then** a new `Payment(type='REVERSAL')` record is created linked to the original payment
**And** the original `Payment` record is never mutated

**Given** a reversal is requested more than 24 hours after the original payment
**When** the endpoint is called
**Then** HTTP 422 is returned with `REVERSAL_WINDOW_EXPIRED`

### Story 2.6: Multi-Provider Payment Routing + Card Payments

As a store owner,
I want payments automatically routed to the correct provider based on my store's configuration,
So that Kenya stores use M-Pesa and international stores use card payment without any code changes.

**Acceptance Criteria:**

**Given** `initiate_payment(store, method, amount, reference)` is called
**When** `store.payment_methods` is inspected
**Then** the call is routed to the matching provider: `apps/payment/providers/mpesa.py`, `stripe.py`, `flutterwave.py`, or `cash.py`
**And** if `method` is not in `store.payment_methods`, HTTP 422 is returned with `PAYMENT_METHOD_NOT_ENABLED`

**Given** a store with `currency='JMD'` and `payment_methods=['stripe']`
**When** a Stripe payment is initiated
**Then** the amount is sent to Stripe in JMD and the `PaymentIntent` is created in the store's currency

**Given** a cash payment is initiated by staff (`method='cash'`)
**When** the `cash` provider is called
**Then** a `Payment(type='CASH', status='pending')` record is created
**And** a staff member must call `POST /api/v1/payments/{id}/confirm-cash/` to mark it `confirmed`

**Given** Stripe sandbox E2E tests
**When** the test suite runs with `store.currency='JMD'`
**Then** a test payment intent is created, confirmed, and the webhook callback updates the order to `confirmed`
**And** these tests are required to pass before Epic 2 can be marked complete (FR91 acceptance gate)

---

## Epic 3: Restaurant Full-Service

A customer's full restaurant journey — from browsing the menu at home before arriving, to pre-selecting items, booking a table, being seated by an assigned waiter, ordering, kitchen processing, and paying the bill.

### Story 3.1: Menu Management API

As a restaurant store owner,
I want to manage my menu with sections, items, modifiers, allergen flags, and time-based scheduling,
So that my customers always see an accurate, correctly priced menu for the current service period.

**Acceptance Criteria:**

**Given** a restaurant store owner is authenticated
**When** they create a `MenuSection` (e.g. "Starters"), `MenuItem` under it, and `ModifierGroup` with `Modifier` items
**Then** all are stored scoped to their store and `ModifierGroup` min/max selection rules are enforced on order submission

**Given** a `MenuItem` has `available_from` and `available_until` times set (e.g. breakfast 06:00–11:00)
**When** a customer views the menu outside that window
**Then** the item is automatically hidden from the API response — no client-side filtering required

**Given** a `MenuItem` has `contains_allergens=True`
**When** it is returned via any menu API endpoint
**Then** an allergen flag is included in the response and displayed on the storefront

**Given** a `Modifier` has `price_addition > 0`
**When** a customer selects it
**Then** the modifier price is added to the item price and the total is recalculated

### Story 3.2: Public Menu URL

As a potential customer,
I want to browse a restaurant's full menu from a shareable link without scanning a QR code or joining a table session,
So that I can decide what to order before I arrive.

**Acceptance Criteria:**

**Given** `GET /{store_slug}/menu/` is accessed by anyone (no authentication, no QR, no session)
**When** the page loads
**Then** the full menu with sections and items is rendered SSR for the current service window
**And** out-of-schedule items are hidden automatically

**Given** the public menu page is tested in CI with Lighthouse
**When** the Lighthouse CI job runs against a simulated 3G connection
**Then** the page scores < 1.5s interactive time
**And** this Lighthouse CI gate blocks merges that regress the score (FR94)

**Given** the public menu page is loaded on a 320px viewport
**When** rendered on mobile
**Then** all menu items, prices, and allergen flags are readable without horizontal scrolling

### Story 3.3: HMAC QR Table Token Generation + Validation

As a restaurant operator,
I want each table's QR code to be cryptographically signed,
So that customers cannot forge a QR code to join a table they are not at.

**Acceptance Criteria:**

**Given** `POST /api/v1/restaurant/tables/{id}/qr-token/` is called by a store manager
**When** the token is generated
**Then** it encodes `store_id` + `table_id` + `timestamp` signed with HMAC-SHA256 using a store-specific secret
**And** the token is valid for a configurable TTL (default: 24 hours)

**Given** a QR code token arrives at `GET /api/v1/restaurant/qr/validate/?token=`
**When** the HMAC signature is verified
**Then** a valid, unexpired token returns the table and store details
**And** an unsigned or tampered token returns HTTP 400 with `INVALID_QR_TOKEN`
**And** an expired token returns HTTP 400 with `QR_TOKEN_EXPIRED`

**Given** a valid QR token is successfully validated
**When** the validation completes
**Then** the token is marked as `used` in Redis (key: `qr:used:{token_hash}`, TTL matching token TTL)
**And** a second validation attempt with the same token returns HTTP 400 with `QR_TOKEN_ALREADY_USED` — preventing replay attacks where multiple customers photograph the same QR code

### Story 3.4: Table + TableSession State Machine + Waiter Assignment

As a restaurant waiter,
I want to open a table session when customers are seated and assign myself as the waiter,
So that all orders for that table are linked to me and visible on kitchen tickets.

**Acceptance Criteria:**

**Given** a valid QR token is scanned and validated
**When** no `OPEN` session exists for that table
**Then** a new `TableSession` is created with status `OPEN`
**And** `UniqueConstraint` enforces only one `OPEN` session per table — a second attempt returns HTTP 409

**Given** a `TableSession` in `OPEN` status
**When** a waiter calls `PATCH /api/v1/restaurant/sessions/{id}/assign-waiter/`
**Then** `TableSession.assigned_waiter` FK is set to the authenticated waiter user
**And** subsequent kitchen tickets for this session include the waiter's name

**Given** a `TableSession` transitions through its state machine
**When** the transition is `OPEN → BILL_REQUESTED → CLOSED`
**Then** each transition is enforced in code via a transition method — never direct field assignment
**And** invalid transitions return HTTP 422 with `INVALID_SESSION_TRANSITION`

### Story 3.5: QR Scan Errors + Wrong-Table Guard

As a customer,
I want a clear, friendly error if I scan the wrong table's QR code or a damaged/expired code,
So that I can correct the situation without frustration and without placing an order at the wrong table.

**Acceptance Criteria:**

**Given** a customer scans a QR code and the token is valid
**When** the confirmation screen loads
**Then** it displays: "You're joining Table [N]'s session at [Store Name]. Is this correct?" with Yes / No options — always shown, never skipped

**Given** the customer taps "No, wrong table"
**When** the correction flow activates
**Then** a fallback URL `/t/{table_id}` is displayed with instructions to ask staff for the correct table
**And** no session is created or joined

**Given** an expired QR token is scanned
**When** the validation endpoint is called
**Then** the customer sees: "This QR code has expired. Please ask your waiter to refresh it."

**Given** a tampered or unsigned QR token is scanned
**When** the validation endpoint is called
**Then** the customer sees a generic error — no technical details exposed

### Story 3.6: Dine-In Order + Denormalized Kitchen Ticket

As a kitchen worker,
I want to see new orders appear on the kitchen display within 5 seconds of being placed, with full item and modifier details, without navigating away from the screen,
So that I can prepare orders accurately and quickly.

**Acceptance Criteria:**

**Given** a customer submits a dine-in order with items and modifiers
**When** the `DineInOrder` is created
**Then** a `KitchenTicket` is created with a denormalized JSON snapshot of all items, quantities, modifiers, and the assigned waiter name
**And** `KitchenTicket` creation never requires joining more than one table at query time

**Given** the kitchen display polls `GET /api/v1/restaurant/kitchen/tickets/`
**When** the response is returned
**Then** it contains only `PENDING` and `IN_PROGRESS` tickets
**And** response time is < 50ms (enforced in the story's performance test)
**And** the frontend polls with TanStack Query `refetchInterval: 5000`

**Given** a kitchen ticket is displayed
**When** rendered on the kitchen display device
**Then** modifier flags that are bolded appear above the item name
**And** the assigned waiter name is visible on the ticket

**Given** the kitchen display loses connectivity for 15 seconds
**When** the polling interval fires and receives no response
**Then** the "Last updated X seconds ago" timestamp turns amber

**Given** connectivity is lost for 30 seconds
**When** the polling interval fires
**Then** a full-screen red banner displays "CONNECTION LOST — REFRESH NOW" with an optional audible alert

**Given** the kitchen display page loads on a tablet browser
**When** the Page Visibility API and Wake Lock API are available
**Then** `navigator.wakeLock.request('screen')` is called to prevent screen timeout during active service
**And** if Wake Lock is not supported by the browser, a persistent "Tap to keep screen on" banner is shown at the bottom of the display

### Story 3.6b: Customer Dine-In Order Confirmation + Live Status Screen

As a dine-in customer,
I want to see a confirmation screen immediately after placing my order with a live status showing when the kitchen accepts it,
So that I know my order was received and I'm not left staring at a blank screen wondering what happened.

**Acceptance Criteria:**

**Given** a customer submits a dine-in order successfully
**When** the API returns the created `DineInOrder`
**Then** the customer's screen transitions immediately to an order confirmation view showing: order number, itemized list with quantities and modifiers, table number, assigned waiter name, and total amount
**And** this screen renders within 1 second of order submission — no skeleton loader for above-fold content

**Given** the confirmation screen is displayed
**When** it renders
**Then** a live status indicator shows the current `KitchenTicket` state, polling `GET /api/v1/restaurant/orders/{id}/status/` every 10 seconds via TanStack Query `refetchInterval`
**And** the status progression shown to the customer is: "Order received ✓" → "Kitchen preparing 🍳" → "Order ready 🎉"

**Given** the `KitchenTicket` status transitions to `IN_PROGRESS`
**When** the next poll returns the updated status
**Then** the status indicator updates to "Kitchen preparing 🍳" without a full page reload

**Given** the `KitchenTicket` status transitions to `COMPLETED` (food ready for service)
**When** the next poll returns
**Then** the status updates to "Order ready 🎉" and a subtle animation or sound cue fires (respecting device silent mode)

**Given** the customer navigates away from the confirmation screen and returns
**When** the page reloads
**Then** the same order confirmation is displayed with the current live status — never an error or empty state
**And** the order ID is stored in `sessionStorage` as `current_dine_in_order_id` to enable this recovery

**Given** the page renders on a 320px viewport on a budget Android device (Tecno, Infinix)
**When** all content is displayed
**Then** all tap targets are minimum 44×44px, text is legible at 16px base size, and no content requires horizontal scrolling

### Story 3.7: PendingOrder + Waiter Convert Screen

As a customer who wants to pre-select their order before arriving,
I want to browse the menu, choose items, and receive a PIN I can give my waiter when seated,
So that my order is ready to fire the moment I sit down.

**Acceptance Criteria:**

**Given** a customer on the public menu URL selects items and submits a `PendingOrder`
**When** a phone number is provided
**Then** a `PendingOrder` record is created with a 6-digit PIN, linked to the phone number
**And** the PIN and order summary are displayed to the customer

**Given** a `PendingOrder` is created
**When** `PendingOrder.expires_at` is set
**Then** it is 24 hours from creation time

**Given** the Celery Beat hourly purge task runs
**When** any `PendingOrder` has passed its `expires_at`
**Then** it is soft-deleted and no longer retrievable

**Given** a waiter on the waiter screen enters a customer's phone number or PIN
**When** a matching `PendingOrder` is found
**Then** the order summary is displayed with a one-tap "Seat & Convert" button

**Given** the waiter taps "Seat & Convert" on an open `TableSession`
**When** the conversion runs
**Then** the `PendingOrder` is converted to a `DineInOrder` linked to the active `TableSession`
**And** a `KitchenTicket` is created immediately
**And** the `PendingOrder` is marked `CONVERTED` and no longer retrievable via PIN

### Story 3.8: Pre-Order + Advance Payment

As a customer who wants their food ready the moment they arrive,
I want to pay for my order in advance online,
So that the kitchen starts preparation on confirmation of my seating without any delay.

**Acceptance Criteria:**

**Given** a customer has an unpaid `PendingOrder`
**When** they choose to pay in advance via M-Pesa
**Then** `initiate_payment()` is called and an STK Push is sent to their phone
**And** the `PendingOrder` status transitions to `PAID` on payment confirmation

**Given** a `PendingOrder` in `PAID` status and a waiter has confirmed the customer's seating
**When** the waiter converts the `PendingOrder` to a `DineInOrder`
**Then** a `KitchenTicket` is created immediately — kitchen fires on waiter confirmation, not on payment
**And** the payment is linked to the resulting `DineInOrder`

**Given** a `PendingOrder` in `PAID` status expires without being converted
**When** the hourly purge task runs
**Then** the `PendingOrder` is flagged for manual review — not auto-deleted
**And** an alert is dispatched via `billing.reminders` Celery queue for operator review

### Story 3.9: Reservation Model

As a customer,
I want to book a table at a restaurant for a specific time and party size and receive a confirmation via WhatsApp or SMS,
So that I have a guaranteed seat when I arrive.

**Acceptance Criteria:**

**Given** `POST /api/v1/restaurant/reservations/` with time slot, party size, and customer phone
**When** the reservation is created
**Then** a `Reservation` record is created with status `PENDING` and the requested time slot
**And** a WhatsApp or SMS confirmation is dispatched via Celery within 60 seconds

**Given** a store manager calls `PATCH /api/v1/restaurant/reservations/{id}/confirm/`
**When** the reservation is confirmed
**Then** status transitions to `CONFIRMED` and a confirmation message is sent to the customer

**Given** a confirmed customer arrives and is seated
**When** the waiter calls `PATCH /api/v1/restaurant/reservations/{id}/seat/`
**Then** status transitions to `SEATED` and a `TableSession` is automatically opened for the reserved table

**Given** a reservation that was `CONFIRMED` but the customer never arrived
**When** a store manager marks it as no-show
**Then** status transitions to `NO_SHOW` and the table is freed

### Story 3.10: Takeaway Order Type

As a customer who wants to order ahead for pickup,
I want to place and pay for a takeaway order online and receive a pickup reference number,
So that I can collect my order without waiting in a queue.

**Acceptance Criteria:**

**Given** `POST /api/v1/restaurant/orders/takeaway/` with items and customer phone
**When** the order is submitted
**Then** a `DineInOrder` with `order_type='takeaway'` is created
**And** a `KitchenTicket` is created immediately

**Given** payment is completed via `initiate_payment()`
**When** the payment is confirmed
**Then** a unique pickup reference number (e.g. `TKW-0042`) is generated and displayed to the customer
**And** an SMS or WhatsApp notification with the reference is dispatched via Celery

**Given** the kitchen marks the takeaway order as ready
**When** status transitions to `READY`
**Then** the customer receives a "Your order is ready for pickup" notification

### Story 3.11: Restaurant Bill Payment + Split Bill

As a customer finishing a dine-in meal,
I want to pay my bill via M-Pesa and split it with my tablemates if needed,
So that settlement is fast and each person pays only their share.

**Acceptance Criteria:**

**Given** a customer requests the bill (`PATCH /api/v1/restaurant/sessions/{id}/request-bill/`)
**When** the session transitions to `BILL_REQUESTED`
**Then** the itemized bill is available at `GET /api/v1/restaurant/sessions/{id}/bill/`

**Given** a single-payer bill settlement
**When** `initiate_payment()` is called for the full amount
**Then** an STK Push is sent to the customer's phone

**Given** a split bill with multiple payers
**When** each payer selects their items and confirms
**Then** individual STK Push payments are initiated per person via `initiate_payment()`
**And** each person's itemized share is shown before they confirm

**Given** all payers have confirmed their payments
**When** the last payment is confirmed
**Then** the `TableSession` transitions to `CLOSED` automatically

### Story 3.12: FR4 Cross-Epic Tenant Type Lock Test

As a platform engineer,
I want a test that explicitly verifies the tenant_type lock guard fires after the first dine-in order is placed,
So that the guard is proven end-to-end across the Epic 1 model and Epic 3 commerce layer.

**Acceptance Criteria:**

**Given** a `Store` with `tenant_type='restaurant'`
**When** a `DineInOrder` is successfully created for that store
**Then** a subsequent `Store.save()` call attempting to change `tenant_type` to any other value raises `IntegrityError`
**And** this test lives in `apps/restaurant/tests/test_tenant_lock.py` and runs in the CI cross-tenant gate (`pytest -k "cross_tenant"`)

---

## Epic 4: Retail Store Commerce

A retail customer browses a product catalog with variants, adds items to a persistent cart, and completes checkout as a guest or authenticated user.

### Story 4.1: Product Catalog (Categories, Variants, Inventory, Images)

As a retail store owner,
I want to manage a product catalog with categories, variants, per-variant inventory, and multiple images,
So that customers can browse accurate stock and see the product correctly.

**Acceptance Criteria:**

**Given** a store owner creates a `Product` with `Category`, `ProductAttribute` (e.g. "Size"), and `Variant` combinations (e.g. S×Red, M×Blue)
**When** the product is saved
**Then** each variant has its own `inventory_count` tracked independently

**Given** a product image is uploaded
**When** it is processed by the Pillow pipeline
**Then** it is compressed to WebP format at max 800KB
**And** the original file is deleted from temp storage immediately after compression
**And** only the WebP file is saved to disk

**Given** `GET /api/v1/store/products/` is called
**When** the response is returned
**Then** products are paginated using `StoreCursorPagination` — no unbounded list response

**Given** a variant's `inventory_count` falls below the store's configured low-stock threshold
**When** the inventory is saved
**Then** a low-stock alert task is dispatched to the `inventory.alerts` Celery queue via `transaction.on_commit`

**Given** `GET /api/v1/store/products/{id}/` is called for a product with variants
**When** the response is returned
**Then** it includes: `attributes` (list of attribute names e.g. ["Size", "Colour"]), `variants` (list of variant objects each with: `id`, `attribute_values` e.g. `{"Size": "M", "Colour": "Red"}`, `price`, `inventory_count`, `images`)

**Given** a customer opens a product detail page on the storefront
**When** the page renders
**Then** each product attribute is displayed as an interactive selector: pill/chip group for non-colour attributes (e.g. Size: S M L XL), colour swatches for any attribute named "Colour" or "Color"
**And** the initially selected variant defaults to the first in-stock combination

**Given** a customer selects a variant combination (e.g. Size=L + Colour=Red)
**When** the selection changes
**Then** the product image gallery updates immediately (no page reload) to show images for that specific variant, falling back to the product's default images if no variant-specific images exist
**And** the displayed price updates to the selected variant's price
**And** the stock status updates: "In Stock", "Low Stock (N left)", or "Out of Stock"

**Given** a variant combination has `inventory_count = 0`
**When** it is displayed in the variant selector
**Then** the corresponding chip or colour swatch is visually disabled — greyed out with a strikethrough — and cannot be tapped or selected
**And** the "Add to Cart" button remains disabled until an in-stock combination is selected

**Given** a product has a variant where a specific attribute has only one value (e.g. one colour, multiple sizes)
**When** the product detail page renders
**Then** only the attributes with more than one option are shown as selectors — single-option attributes are not rendered as a picker

**Given** a variant's price differs from another variant's price (e.g. 256GB phone costs more than 128GB)
**When** a customer switches between variants
**Then** the displayed price updates instantly client-side — no API call required for the price update (prices are pre-loaded in the page payload)

**Given** a store owner generates a product QR code via `GET /api/v1/store/products/{id}/qr/`
**When** the QR is generated
**Then** it encodes `store_id + product_id + HMAC` (same signing scheme as restaurant table QR, FR22) and is returned as a PNG download
**And** the HMAC signature is verified when the QR URL is resolved — unsigned QR codes return HTTP 403

**Given** a customer scans a product QR code (e.g. placed on a shelf display in a tech store or clothes rack)
**When** the QR link is opened
**Then** the storefront loads directly to that product's detail page with the full variant selector pre-loaded
**And** the customer can select their variant (e.g. "128GB · Black"), add to cart, and complete checkout without any prior navigation

**Given** a product QR is scanned and the product is out of stock in all variants
**When** the product detail page loads
**Then** all variant selectors are disabled, "Out of Stock" is shown, and a "Notify me" prompt is offered (captures phone number for WhatsApp restock alert)

### Story 4.2: Redis Cart (30-Day TTL, Guest + Auth)

As a customer,
I want my cart to persist across browser sessions and device restarts for 30 days,
So that I never lose my selections even if I close the browser.

**Acceptance Criteria:**

**Given** a guest customer adds items to the cart
**When** the cart is stored
**Then** it is persisted in Redis with a 30-day TTL keyed by an anonymous session ID stored in a cookie

**Given** a guest customer closes and reopens the browser
**When** they return to the store
**Then** their cart is restored from Redis using the session cookie

**Given** a guest customer logs in after adding items to the cart
**When** authentication completes
**Then** the guest cart is merged with any existing authenticated cart and the Redis key is updated to the user ID

**Given** a payment is initiated for a cart
**When** `initiate_payment()` is called
**Then** the cart state is written to PostgreSQL as a safety net before the STK Push is sent

**Given** the Redis container restarts
**When** AOF persistence is enabled
**Then** cart data is not lost

**Given** a guest customer is browsing on Safari iOS or any browser with ITP (Intelligent Tracking Prevention) that blocks the session cookie
**When** the cart is written
**Then** the cart falls back to `sessionStorage` automatically — the same cart key format is used
**And** a non-blocking banner informs the customer: "Your cart will clear if you close this tab. Sign in to save it."

**Given** a customer is browsing inside WhatsApp's or Facebook's in-app browser
**When** an attempt to write to `localStorage` or `sessionStorage` fails or is detected as in-app
**Then** a prominent prompt is shown: "For the best checkout experience, open in Chrome or Safari"
**And** a one-tap "Open in Chrome" deep-link button is displayed before the checkout step

**Given** a customer taps "Add to Cart" on a product detail page with a selected variant
**When** the cart item is written to Redis
**Then** the cart line item stores: `product_id`, `variant_id`, `quantity` — never just `product_id`
**And** two different variants of the same product (e.g. Size M Red and Size L Red) are stored as two separate line items

**Given** a customer views their cart
**When** the cart is rendered
**Then** each line item displays: product name, selected variant details (e.g. "Size: M · Colour: Red"), unit price, quantity controls, and line total
**And** the variant details are fetched from the pre-loaded product payload — no extra API call per cart item

**Given** a variant becomes out of stock between the time a customer adds it to their cart and the time they reach checkout
**When** checkout is initiated
**Then** the API returns HTTP 409 with `VARIANT_OUT_OF_STOCK` identifying the affected line item
**And** the storefront highlights the affected item in the cart and prompts the customer to remove it or select an alternative variant

### Story 4.3: Order Lifecycle State Machine

As a retail store owner,
I want every order to follow a defined lifecycle with enforced transitions,
So that orders can never be in an ambiguous or invalid state.

**Acceptance Criteria:**

**Given** a new order is created at checkout
**When** the order is initialized
**Then** its status starts at `pending`

**Given** `order.transition_status(new_status)` is called
**When** valid transitions are `pending→confirmed`, `confirmed→fulfilled`, `fulfilled→completed`, and `pending→cancelled` or `confirmed→cancelled`
**Then** the status is updated and a timestamp is recorded for the transition

**Given** an invalid transition is attempted (e.g. `completed→pending`)
**When** `transition_status()` is called
**Then** an exception is raised and the status is not changed — direct field assignment to `status` is never used

**Given** an order transitions to `confirmed`
**When** the transition completes
**Then** an order confirmation email task is dispatched to `order.notifications` Celery queue via `transaction.on_commit`
**And** the email is sent within 60 seconds of confirmation

### Story 4.3b: Merchant Daily View — Zero Navigation Dashboard

As a store owner or manager,
I want to see today's critical numbers and pending actions the moment I open the admin — without tapping a single navigation item,
So that I can assess my store's health and act on urgent items in under 30 seconds.

**Acceptance Criteria:**

**Given** a store owner or manager authenticates and the admin dashboard loads
**When** the first screen renders
**Then** it displays without any navigation required: today's order count, today's total revenue (in store currency), count of orders in `pending` status requiring action, and count of active low-stock alerts
**And** all four metrics are rendered SSR — no skeleton loader, no loading spinner on the first meaningful paint

**Given** a `pending` order exists requiring confirmation
**When** the merchant views the daily dashboard
**Then** each pending order is listed with: order number, customer name (masked to first name only), total amount, and a one-tap "Confirm" action button
**And** tapping "Confirm" calls `order.transition_status('confirmed')` and removes the order from the pending list without a page reload

**Given** a low-stock alert exists
**When** the merchant views the dashboard
**Then** each alert shows: product name, variant, current count, and a one-tap "Reorder" link that opens the supplier contact or product edit view

**Given** the store has no orders or alerts today
**When** the dashboard renders
**Then** an empty state is shown for each section with a forward-moving CTA — not a blank space
**And** the first-login empty state shows: "Your store is live! Share your store link to get your first order." with the store URL as a copyable link

**Given** the dashboard is accessed on a budget Android device on 3G
**When** it loads
**Then** time-to-interactive is under 3 seconds on a simulated 3G connection
**And** all tap targets are minimum 48×48px

**Given** a new day begins (midnight store timezone)
**When** the merchant opens the dashboard
**Then** all today's counters reset to reflect the new day's data — never showing yesterday's totals as today's

### Story 4.4: Guest Checkout + M-Pesa Payment

As a guest customer,
I want to complete a purchase without creating an account,
So that checkout is as fast as possible.

**Acceptance Criteria:**

**Given** a guest customer proceeds to checkout
**When** they provide a phone number and shipping details (no login required)
**Then** an order is created in `pending` status without requiring account creation

**Given** the guest submits checkout
**When** `initiate_payment(method='mpesa')` is called
**Then** an STK Push is sent to their phone

**Given** payment is confirmed via webhook
**When** the order transitions to `confirmed`
**Then** a confirmation email is sent to the guest's provided email address via Celery

**Given** a successful payment and order confirmation
**When** the confirmation screen loads
**Then** a post-payment registration prompt is shown as an optional offer — never blocking or mandatory

**Given** the M-Pesa STK Push waiting state begins
**When** the customer taps Pay
**Then** a full-screen modal locks the UI with: merchant brand color pulse animation, cycling reassurances ("Your cart is saved" → "Your order number is ready" → "Check your Safaricom phone"), "don't tap again" message, and the Pay button is disabled

**Given** payment is initiated and `pending_payment_order_id` is written to `localStorage`
**When** the customer navigates away, closes the tab, or the browser crashes
**Then** on any subsequent page load of the storefront, the frontend checks `localStorage` for `pending_payment_order_id`
**And** if found and the backend confirms the payment is completed, the order confirmation screen is rendered immediately regardless of URL
**And** if the payment is still pending, the STK Push waiting modal is re-shown with the same order context
**And** `pending_payment_order_id` is cleared from `localStorage` only after a confirmed or definitively failed status is received

### Story 4.5: Google OAuth2 PKCE (Authenticated Checkout)

As a returning customer,
I want to sign in with Google to access my order history and have my details pre-filled at checkout,
So that checkout is faster on repeat visits.

**Acceptance Criteria:**

**Given** a customer taps "Sign in with Google" on any storefront
**When** the OAuth2 PKCE flow completes
**Then** a store-scoped customer account is created or retrieved with `store_id` in scope during the OAuth callback
**And** a JWT with `role='customer'` and `store_id` is issued

**Given** an authenticated customer proceeds to checkout
**When** the checkout form loads
**Then** their phone number and delivery address are pre-filled from their stored profile

**Given** the same Google account is used on two different stores
**When** the OAuth callback is processed
**Then** two separate store-scoped customer accounts exist — no cross-tenant account merging

### Story 4.6: Order Confirmation Email + Low-Stock Alerts

As a retail store owner,
I want order confirmations sent to customers automatically and low-stock alerts sent to me when inventory is critical,
So that customers are informed and I can restock before running out.

**Acceptance Criteria:**

**Given** an order transitions to `confirmed`
**When** the Celery task in `order.notifications` queue runs
**Then** an order confirmation email is sent to the customer within 60 seconds
**And** the email includes: order number, itemized list with variant details, total paid, delivery/pickup details

**Given** a variant's `inventory_count` falls below the store's low-stock threshold
**When** the `inventory.alerts` Celery task runs (dispatched via `transaction.on_commit`)
**Then** a supplier notification email is sent to the store owner's configured supplier email
**And** the email includes the product name, variant, current count, and a reorder suggestion

**Given** the Celery task fails on first attempt
**When** it retries
**Then** exponential backoff is applied (`countdown = 60 * (2 ** retries)`, max 5 retries)
**And** after max retries the task is sent to the DLQ

### Story 4.7: Card Payment Scaffold

As a platform engineer,
I want Stripe and Flutterwave card payment endpoints to exist from day one but return 501,
So that the payment routing infrastructure is correct and card activation requires only implementation, not restructuring.

**Acceptance Criteria:**

**Given** `initiate_payment(store, method='stripe', ...)` is called on a card-enabled store
**When** the Stripe provider is invoked
**Then** HTTP 501 is returned with body `{"detail": "CARD_PAYMENT_NOT_LIVE"}`
**And** no charge is attempted

**Given** `initiate_payment(store, method='flutterwave', ...)` is called
**When** the Flutterwave provider is invoked
**Then** HTTP 501 is returned with the same format

**Given** the card scaffold endpoints are registered
**When** `./manage.py spectacular --validate` is run
**Then** the endpoints appear in the OpenAPI schema with their 501 response documented

### Story 4.8: Post-Payment Browser Recovery

As a customer,
I want to always land on my order confirmation — even if I closed the browser, refreshed, or navigated away during payment —
So that I never think my order was lost when it actually succeeded.

**Acceptance Criteria:**

**Given** a customer taps Pay and the STK Push is initiated
**When** the payment modal opens
**Then** `localStorage.setItem('pending_payment_order_id', orderId)` is written immediately

**Given** `pending_payment_order_id` exists in `localStorage`
**When** any page in the storefront loads (including the homepage, product pages, or a direct URL)
**Then** the frontend calls `GET /api/v1/orders/{id}/status/` silently in the background

**Given** the status check returns `confirmed`
**When** the result is received
**Then** the order confirmation screen is rendered immediately, overriding whatever page was loading
**And** `pending_payment_order_id` is removed from `localStorage`

**Given** the status check returns `pending`
**When** the result is received
**Then** the STK Push waiting modal is re-displayed with: "Your payment is still processing — check your Safaricom phone"
**And** the modal polls `GET /api/v1/orders/{id}/status/` every 5 seconds until status changes

**Given** the status check returns `cancelled` or `expired`
**When** the result is received
**Then** `pending_payment_order_id` is cleared and the customer sees: "Your payment didn't go through. Your cart is saved — try again."

**Given** double-landing on the confirmation screen (customer bookmarks it and returns)
**When** the page loads
**Then** the same order is shown with: "Payment confirmed at [HH:MM]" — never an error or empty state

### Story 4.9: In-App Browser Detection + Cart Fallback

As a customer opening the storefront from a WhatsApp link or Facebook post,
I want to be warned that my browser environment may cause checkout to fail and given an easy escape,
So that I never lose my cart or get stuck in a broken checkout flow.

**Acceptance Criteria:**

**Given** a customer opens the storefront inside WhatsApp's in-app browser
**When** the page loads
**Then** a non-blocking banner appears immediately: "For the best checkout experience, open in your browser"
**And** a one-tap "Open in Chrome" / "Open in Safari" button is shown using the appropriate OS deep-link

**Given** the customer taps "Open in Chrome"
**When** Chrome opens
**Then** the cart contents are preserved via URL parameters or a short-lived server-side cart token
**And** the customer lands on the same page they were viewing

**Given** a customer in an in-app browser proceeds to checkout anyway (dismisses the banner)
**When** `localStorage` write fails or is unavailable
**Then** cart state falls back to `sessionStorage`
**And** if both fail, the customer sees: "Your browser doesn't support saving your cart. Open in Chrome to checkout safely." before the Pay button is reachable — they cannot reach a broken checkout

**Given** user-agent detection is used
**When** implemented
**Then** it detects at minimum: WhatsApp iOS, WhatsApp Android, Facebook in-app browser, Instagram in-app browser
**And** detection is done server-side via `User-Agent` header parsing — not client-side JS sniffing alone

---

## Epic 5: Bar Tab Management

A bar customer opens a tab, orders rounds without re-authentication, age-restricted items require acknowledgement, happy hour pricing is snapshotted at add-time, and the final bill can be split across multiple payers.

### Story 5.1: Bar Tenant Type Activation + Tab State Machine

As a bar operator,
I want a customer tab to follow a strict lifecycle from open to settled,
So that bills are never closed without payment and the state is always auditable.

**Acceptance Criteria:**

**Given** a `Store` with `tenant_type='bar'`
**When** the bar module activates
**Then** tab management, round ordering, age-restricted item enforcement, and happy hour pricing are all available
**And** `apps/restaurant/` is confirmed active (bar requires it)

**Given** `POST /api/v1/bar/tabs/` is called by an authenticated customer or staff
**When** the tab is created
**Then** a `Tab` record is created with status `OPEN` linked to the customer

**Given** a `Tab` transitions through its lifecycle
**When** transitions are `OPEN → BILL_REQUESTED → SETTLED`
**Then** each transition is enforced via a transition method — never direct field assignment
**And** invalid transitions return HTTP 422 with `INVALID_TAB_TRANSITION`

### Story 5.2: Round Ordering on Open Tab

As a bar customer,
I want to add another round to my open tab without re-entering my card or phone details,
So that ordering the next round is as quick as a single tap.

**Acceptance Criteria:**

**Given** a `Tab` in `OPEN` status
**When** `POST /api/v1/bar/tabs/{id}/rounds/` is called
**Then** the new items are added to the existing tab without requiring re-authentication

**Given** a `Tab` in any status other than `OPEN`
**When** a round order is attempted
**Then** HTTP 422 is returned with `TAB_NOT_OPEN`

**Given** an item removal is performed by staff on an open tab
**When** the removal is confirmed
**Then** an audit entry is created recording: item removed, staff name, timestamp
**And** this entry is visible to the customer in the bill view as "removed by [staff name] at [HH:MM]"

### Story 5.3: Age-Restricted Items + AgeRestrictionLog

As a bar operator,
I want age-restricted items to require explicit customer acknowledgement before being added to a tab,
So that we maintain legal compliance and have an auditable record.

**Acceptance Criteria:**

**Given** a `MenuItem` has `is_age_restricted=True`
**When** it is displayed on the bar menu
**Then** a compliance warning is shown: "This item is age-restricted. You must be 18+ to order."

**Given** a customer attempts to add an age-restricted item to their tab
**When** no `AgeRestrictionLog` entry exists for this customer on this tab
**Then** an age acknowledgement prompt is shown before the item is added

**Given** the customer acknowledges the age restriction
**When** they confirm
**Then** an `AgeRestrictionLog(customer, tab, item, acknowledged_at)` entry is created
**And** the item is added to the tab

**Given** an `AgeRestrictionLog` entry already exists for this customer on this tab
**When** a second age-restricted item is added
**Then** no duplicate prompt is shown — the existing log entry covers the session

### Story 5.4: Happy Hour Pricing Snapshot

As a bar customer,
I want the discounted happy hour price locked in at the moment I add an item to my tab,
So that my bill reflects the price I saw when I ordered, not the price at settlement.

**Acceptance Criteria:**

**Given** a `HappyHour` window is active (configured by store manager with start/end times and discount)
**When** a customer adds an item to their tab during the happy hour window
**Then** the discounted price is snapshotted on the `TabItem` at add-time — never recalculated at settlement
**And** a "HH" badge is visible on the discounted item in the tab view

**Given** a customer adds the first full-price item after happy hour ends
**When** the item is added to the tab
**Then** an automatic notice appears: "Happy hour has ended — this item is at full price"

**Given** a tab is settled after happy hour ends
**When** the bill is calculated
**Then** happy-hour items retain their snapshotted discounted price — no recalculation occurs

### Story 5.5: Tab Split Settlement via M-Pesa

As a group of bar customers,
I want to split the tab and each pay my share via M-Pesa individually,
So that we settle quickly without anyone having to pay the whole bill and collect from others.

**Acceptance Criteria:**

**Given** a `Tab` in `BILL_REQUESTED` status
**When** a customer requests split payment
**Then** they can select which items or what percentage of the total they are paying

**Given** a payer confirms their share
**When** `initiate_payment(method='mpesa')` is called per person
**Then** an individual STK Push is sent to each payer's phone

**Given** all payers have completed their individual payments
**When** the last payment is confirmed
**Then** the `Tab` transitions to `SETTLED` automatically

**Given** a partial payment failure (one payer's STK Push times out)
**When** the timeout is received
**Then** the tab remains in `BILL_REQUESTED` and the failed payer sees a retry prompt
**And** confirmed payments from other payers are not reversed

---

## Epic 6: Contracting Module

A contractor lists services and sets availability. Customers book jobs or request quotes. Contractor accepts, tracks milestones, uploads completion photos, and collects payment. Branded PDF invoices are WhatsApp-shareable.

### Story 6.1: Contracting Tenant Type + Service Catalog

As a contractor,
I want to list my services with descriptions, base prices, and estimated durations,
So that customers can understand what I offer before booking.

**Acceptance Criteria:**

**Given** a `Store` with `tenant_type='contracting'`
**When** the contracting module activates
**Then** the service catalogue, booking, quote flow, job tracking, and invoicing features are all available

**Given** a contractor creates a `Service` via `POST /api/v1/contracting/services/`
**When** the service is saved
**Then** it has fields: `name`, `description`, `base_price`, `duration_estimate`, `category`
**And** it is scoped to the contractor's store via `IsStoreScoped`

**Given** `GET /api/v1/contracting/services/` is accessed by a customer
**When** the response is returned
**Then** only active services for the requested store are listed, paginated via `StoreCursorPagination`

### Story 6.2: Service Booking + Availability Calendar

As a customer,
I want to book a service at a specific time slot that is confirmed as available,
So that I don't book a time the contractor is already committed.

**Acceptance Criteria:**

**Given** a contractor has configured available time slots
**When** `GET /api/v1/contracting/services/{id}/availability/` is called
**Then** available slots for the next 30 days are returned

**Given** a customer submits `POST /api/v1/contracting/bookings/` with a service and time slot
**When** the slot is available
**Then** a `ServiceBooking` record is created with status `PENDING`
**And** the time slot is marked unavailable for other bookings

**Given** the contractor calls `PATCH /api/v1/contracting/bookings/{id}/confirm/`
**When** confirmed
**Then** status transitions to `CONFIRMED` and a confirmation notification is dispatched to the customer

### Story 6.3: Quote Request → Quote → Acceptance

As a customer with a custom job,
I want to describe my requirements and receive a formal quote before committing,
So that I know the cost before any work begins.

**Acceptance Criteria:**

**Given** a customer submits `POST /api/v1/contracting/quote-requests/` with a description and optional photos
**When** saved
**Then** a `QuoteRequest` with status `OPEN` is created and the contractor is notified

**Given** a contractor responds via `POST /api/v1/contracting/quote-requests/{id}/quote/`
**When** the quote is created with line items and `valid_until` date
**Then** a `Quote` record is created with status `QUOTED` and the customer is notified

**Given** a customer accepts the quote via `PATCH /api/v1/contracting/quotes/{id}/accept/`
**When** accepted
**Then** status transitions to `ACCEPTED` and a `Job` is automatically created from the quote

**Given** a customer rejects the quote
**When** `PATCH /api/v1/contracting/quotes/{id}/reject/` is called
**Then** status transitions to `REJECTED` and no `Job` is created

### Story 6.4: Job + Milestones + Completion Photos

As a contractor,
I want to track job progress through milestones and upload completion photos,
So that the customer has transparent visibility into the work.

**Acceptance Criteria:**

**Given** a `Job` is created (from booking or accepted quote)
**When** inspected
**Then** it has: `assigned_worker`, `milestones` (list of `JobMilestone`), `status` (`PENDING`, `IN_PROGRESS`, `COMPLETED`)

**Given** a contractor updates a `JobMilestone` via `PATCH /api/v1/contracting/milestones/{id}/`
**When** a `completion_photo` is uploaded
**Then** it is compressed to WebP via the Pillow pipeline and the original is deleted
**And** the milestone status transitions to `COMPLETED`

**Given** all milestones are `COMPLETED`
**When** the contractor marks the job complete
**Then** `Job.status` transitions to `COMPLETED` and the customer is notified

### Story 6.5: Invoice Generation + WhatsApp-Shareable PDF

As a contractor,
I want to generate a branded PDF invoice when a job is complete and share it via WhatsApp,
So that the customer has a professional record they can reference for payment.

**Acceptance Criteria:**

**Given** a `Job` transitions to `COMPLETED`
**When** `POST /api/v1/contracting/jobs/{id}/invoice/` is called
**Then** an `Invoice` record is created with line items from the job and the store's branding (logo, name)

**Given** an `Invoice` is created
**When** the PDF generation task runs
**Then** a branded, line-itemized PDF is generated via WeasyPrint and stored on the VPS
**And** a shareable link is returned that the contractor can send via WhatsApp

**Given** a customer opens the WhatsApp-shared PDF link
**When** the link is accessed
**Then** the PDF is served with correct `Content-Type: application/pdf` headers
**And** the PDF includes: store logo, contractor name, line items, totals, payment instructions

### Story 6.6: Invoice Payment Collection

As a customer,
I want to pay a contractor invoice via M-Pesa or card from the invoice link,
So that payment is settled immediately when I receive the invoice.

**Acceptance Criteria:**

**Given** a customer opens an invoice link
**When** they tap "Pay Now"
**Then** `initiate_payment(store, method, amount, reference=invoice_id)` is called with the correct provider for the store's configuration

**Given** payment is confirmed via webhook
**When** the `Invoice.payment_status` is updated
**Then** it transitions to `PAID` and the contractor receives a notification
**And** the `Job` record is marked `SETTLED`

---

## Epic 7: Reliable Async Operations

Order confirmations, inventory alerts, billing reminders, and payment reconciliation are delivered reliably with DLQ protection, exponential backoff, and full operational visibility through Celery Flower.

### Story 7.1: DLQ + Exponential Backoff Hardening on All Tasks

As a platform operator,
I want every Celery task to retry with exponential backoff and land in a dead-letter queue after max retries,
So that transient failures are automatically recovered and persistently failing tasks are visible for investigation.

**Acceptance Criteria:**

**Given** any Celery task across any queue fails on first attempt
**When** it retries
**Then** `countdown = 60 * (2 ** retries)` is applied (30s, 60s, 120s... up to max 5 retries)
**And** all existing tasks across all 5 queues use this retry policy — no task is exempt

**Given** a task reaches max retries (5)
**When** the final retry fails
**Then** the task is routed to the DLQ
**And** a Sentry error event is captured with the task name, queue, and exception details

**Given** any Celery task calls `.delay()` inside an open database transaction
**When** detected in code review or test
**Then** this is treated as a defect — all task dispatch must use `transaction.on_commit(lambda: task.delay(...))`
**And** a linting rule or test enforces this pattern

### Story 7.2: Celery Beat Full Schedule

As a platform operator,
I want all scheduled jobs to run automatically on their defined intervals,
So that reconciliation, merchant digests, and renewal reminders happen without manual intervention.

**Acceptance Criteria:**

**Given** the Celery Beat schedule is configured
**When** Beat runs
**Then** the following jobs are scheduled:
- `reconcile_payments` — daily (queries Daraja for stale transactions)
- `generate_daily_summary` — daily at 00:05 (populates `DailyRevenueSummary`)
- `send_merchant_weekly_digest` — weekly (summary email to store owners)
- `send_subscription_renewal_reminder` — 3 days before subscription period end

**Given** `generate_daily_summary` runs at 00:05
**When** it completes
**Then** `DailyRevenueSummary` records for the previous day are populated for all active stores
**And** the analytics dashboard shows "yesterday's data" with a note that data updates daily

**Given** `send_subscription_renewal_reminder` runs
**When** a store's subscription period ends in 3 days
**Then** a reminder email is dispatched to the `billing.reminders` queue
**And** stores in `trial` or `past_due` status also receive a reminder

### Story 7.3: Worker Health Endpoint

As a platform operator,
I want a health endpoint that exposes queue depth and last worker heartbeat,
So that I can detect worker failures before they impact customers.

**Acceptance Criteria:**

**Given** `GET /health/workers/` is called
**When** the response is returned
**Then** it includes per-queue: `queue_name`, `depth` (pending message count), `last_heartbeat` (ISO 8601 UTC)
**And** HTTP 200 is returned when all workers are healthy

**Given** a worker has not sent a heartbeat in over 60 seconds
**When** `/health/workers/` is called
**Then** that worker's entry includes `"status": "degraded"` and the response returns HTTP 503

**Given** the health endpoint is called by an unauthenticated client
**When** the request is processed
**Then** HTTP 200 or 503 is returned (no authentication required — used by infra monitoring)

### Story 7.4: Celery Flower Production Config

As a platform operator,
I want Celery Flower secured and persistent in production,
So that the task monitoring UI is accessible only to authorized operators and survives container restarts.

**Acceptance Criteria:**

**Given** Celery Flower is running as a Docker service
**When** accessed at its configured URL
**Then** HTTP Basic Auth is required (credentials from environment variables — never hardcoded)

**Given** the Flower container restarts
**When** it comes back up
**Then** task history is retained via persistent storage (Flower's built-in DB or external Redis)

**Given** a Celery task fails and lands in DLQ
**When** Flower is opened
**Then** the failed task appears in the task list with its exception and traceback visible

---

## Epic 8: Merchant Analytics Dashboard

Store owners see yesterday's revenue, order count, AOV, and top products. Restaurant owners see peak hours and table turn rate. Bar owners see tab completion rate. Platform admin sees combined GMV and per-tenant health.

### Story 8.1: Pre-Aggregated Summary Models + Daily Generation

As a platform engineer,
I want analytics data to be pre-aggregated daily rather than computed live from order tables,
So that dashboard queries are always fast regardless of order volume.

**Acceptance Criteria:**

**Given** `DailyRevenueSummary` and `HourlyOrderSummary` models are created
**When** the schema is inspected
**Then** `DailyRevenueSummary` has: `store`, `date`, `total_revenue`, `order_count`, `aov` (average order value), `amount_usd` (USD-normalized for cross-tenant GMV)
**And** `HourlyOrderSummary` has: `store`, `date`, `hour` (0–23), `order_count`, `revenue`

**Given** the Celery Beat `generate_daily_summary` task runs at 00:05
**When** it completes
**Then** one `DailyRevenueSummary` record per active store is created for the previous day
**And** `HourlyOrderSummary` records are populated for each hour with orders

**Given** an analytics endpoint is called
**When** it returns data
**Then** it reads exclusively from `DailyRevenueSummary` or `HourlyOrderSummary` — never from live `Order` or `Payment` table aggregations

**Given** a fresh deployment or demo environment where Celery Beat has not yet run its first `generate_daily_summary`
**When** `./manage.py backfill_analytics --days=30` is run
**Then** `DailyRevenueSummary` and `HourlyOrderSummary` records are generated retroactively for all active stores for the specified number of days
**And** the command is idempotent — running it twice for the same date range does not create duplicate records

**Given** a new store is provisioned and it has existing order history from a data migration
**When** `backfill_analytics` is run for that store
**Then** its summaries are generated correctly from historical `Order` and `Payment` data
**And** the analytics dashboard shows populated data immediately without waiting for the next midnight Celery Beat run

### Story 8.2: AIEvent Append-Only Capture

As a data engineer,
I want product views, cart interactions, searches, and order completions captured as events from day one,
So that the AI recommendation engine has a clean event history to train on.

**Acceptance Criteria:**

**Given** a customer views a product, adds/removes a cart item, performs a search, or completes an order
**When** the action occurs
**Then** an `AIEvent(store, customer, event_type, entity_id, metadata, occurred_at)` record is created as a side effect via `post_save` signal + `transaction.on_commit` Celery task
**And** this event capture never executes inside the primary business logic transaction

**Given** an `AIEvent` record is created
**When** any code attempts to update or delete it
**Then** the operation is rejected — `AIEvent` is append-only (enforced via model `save()` override)

**Given** `GET /api/v1/analytics/events/` is called by a platform admin
**When** the response is returned
**Then** events are paginated via `StoreCursorPagination` — no unbounded list

### Story 8.3: Per-Store Analytics API

As a store owner,
I want to see yesterday's revenue, order count, AOV, and top products in my dashboard,
So that I can make stock and pricing decisions each morning.

**Acceptance Criteria:**

**Given** `GET /api/v1/analytics/summary/?date=yesterday` is called by an authenticated store owner
**When** the response is returned
**Then** it includes: `total_revenue`, `order_count`, `aov`, `top_products` (top 5 by revenue)
**And** all values are read from `DailyRevenueSummary` — no live query

**Given** the admin dashboard displays analytics
**When** it renders
**Then** a note is visible: "Data reflects yesterday's activity. Updated daily at 00:05."

**Given** no `DailyRevenueSummary` record exists for a requested date
**When** the endpoint is called
**Then** zeros are returned (not an error) with a note that the day had no orders or data is pending

### Story 8.4: Restaurant Analytics (Peak Hours + Table Turn Rate)

As a restaurant owner,
I want to see peak ordering hours and how quickly tables are turning,
So that I can staff correctly during busy periods.

**Acceptance Criteria:**

**Given** `GET /api/v1/analytics/restaurant/peak-hours/` is called
**When** the response is returned
**Then** `HourlyOrderSummary` data is returned as a 24-slot array showing order count per hour for the past 7 days

**Given** `GET /api/v1/analytics/restaurant/table-turn-rate/` is called
**When** the response is returned
**Then** the average duration (in minutes) between `TableSession.status = 'OPEN'` and `TableSession.status = 'CLOSED'` is returned, calculated from closed sessions in the past 7 days

### Story 8.5: Bar Analytics

As a bar owner,
I want to see tab completion rates, average round sizes, and occupancy hours,
So that I can measure how efficiently my bar is operating.

**Acceptance Criteria:**

**Given** `GET /api/v1/analytics/bar/tab-metrics/` is called
**When** the response is returned
**Then** it includes: `tab_completion_rate` (settled tabs / opened tabs), `avg_round_size` (items per round), both sourced from `Tab.status = 'settled'` signal aggregations

**Given** `GET /api/v1/analytics/bar/occupancy/` is called
**When** the response is returned
**Then** it returns hours-per-day where at least one tab was `OPEN`, aggregated from the past 7 days

### Story 8.6: Platform Analytics + TenantHealthSnapshot

As a platform admin,
I want to see combined GMV across all tenants, per-tenant health, and unit economics in a single dashboard,
So that I can demonstrate platform performance to investors.

**Acceptance Criteria:**

**Given** `GET /api/v1/platform/analytics/gmv/` is called by a platform admin
**When** the response is returned
**Then** it returns the sum of all active tenants' `DailyRevenueSummary.amount_usd` for the requested period

**Given** the `TenantHealthSnapshot` model is populated daily
**When** inspected
**Then** it includes per-tenant: `store`, `date`, `gmv`, `order_count`, `subscription_status`, `is_healthy` flag

**Given** `GET /api/v1/platform/analytics/unit-economics/` is called
**When** the response is returned
**Then** it returns: `cost_per_tenant` (infra cost / active tenant count) and `revenue_per_tenant` (subscription revenue / active tenant count)
**And** this data is readable only by `platform_admin` role — HTTP 403 for all other roles

### Story 8.7: First Order Milestone + Investor Demo Moment

As a platform admin,
I want the platform dashboard to celebrate and permanently record the moment each merchant places their first ever order,
So that the thesis validation milestone is visible, timestamped, and emotionally resonant during investor demonstrations.

**Acceptance Criteria:**

**Given** an order for a store transitions to `confirmed` status for the very first time (no prior confirmed orders exist for that store)
**When** the transition completes
**Then** a `StoreFirstOrderEvent(store, order, occurred_at)` record is created via `transaction.on_commit` Celery task — never inside the order transition itself
**And** this record is created exactly once per store — idempotent, never duplicated even if retried

**Given** a `StoreFirstOrderEvent` is created for a store
**When** the platform admin dashboard next loads or polls (every 30 seconds)
**Then** a "🎉 First order placed!" banner appears in the tenant row for that store, showing: store name, time of first order, and order total
**And** the banner persists permanently in the platform dashboard — it does not disappear after being seen

**Given** the platform admin dashboard is open during a live investor demonstration
**When** a merchant's first order comes in while the dashboard is being viewed
**Then** the tenant health grid updates within 30 seconds showing the first-order milestone highlighted — no manual refresh required

**Given** `GET /api/v1/platform/stores/{id}/` is called
**When** the store has a `StoreFirstOrderEvent`
**Then** the response includes `first_order_at` timestamp and `first_order_amount` — surfaced prominently in the platform admin store detail view

**Given** the platform admin views the full store list
**When** filtering or sorting
**Then** stores can be sorted by `first_order_at` ascending — enabling "time to first order" reporting as a key onboarding health metric

---

## Epic 9: SaaS Plans + Subscription Management

Merchants subscribe to a plan that enforces feature limits server-side. Trial, grace period, suspension, and cancellation are fully automated via Celery Beat.

### Story 9.1: Plan Model

As a platform admin,
I want to define subscription plans with feature limits and pricing,
So that merchants are offered distinct tiers with clearly enforced capabilities.

**Acceptance Criteria:**

**Given** the `Plan` model is created
**When** the schema is inspected
**Then** it has all 10 required fields: `name`, `product_limit`, `staff_limit`, `analytics_tier`, `ai_access` (boolean), `custom_domain` (boolean), `api_rate_limit`, `monthly_price_kes`, `monthly_price_usd`, and a `features` JSON field for plan-gated feature flags

**Given** `GET /api/v1/platform/plans/` is called
**When** the response is returned
**Then** all active plans are listed with their limits and pricing
**And** this endpoint is publicly accessible (used by the merchant onboarding flow)

### Story 9.2: StoreSubscription Lifecycle

As a merchant,
I want my subscription to automatically progress from trial through active, handle late payments with a grace period, and suspend access only after the grace period expires,
So that I have fair warning before losing access.

**Acceptance Criteria:**

**Given** a new store is provisioned
**When** the `StoreSubscription` is created
**Then** it starts in `trial` status with `trial_ends_at = now() + 14 days`

**Given** a `StoreSubscription` transitions through its lifecycle
**When** transitions are `trial→active`, `active→past_due`, `past_due→suspended`, `suspended→cancelled`
**Then** each is enforced via a transition method — never direct field assignment
**And** `past_due` allows a 7-day grace period before suspension
**And** `cancelled` retains store data for 90 days before anonymisation

**Given** a `StoreSubscription` in `suspended` status
**When** any storefront request arrives for that store
**Then** HTTP 503 is returned with a "Store suspended" message
**And** the store admin can still log in to view billing and reactivate

### Story 9.3: M-Pesa Subscription Renewal

As a merchant,
I want my subscription renewed automatically via M-Pesa when my period ends,
So that I don't have to manually pay each month.

**Acceptance Criteria:**

**Given** the Celery Beat `send_subscription_renewal_reminder` task fires 3 days before period end
**When** it runs
**Then** a reminder email is dispatched to the `billing.reminders` queue with the renewal amount and due date

**Given** the subscription renewal STK Push is initiated
**When** `initiate_payment()` is called for renewal
**Then** it uses a separate Daraja callback endpoint (`/api/v1/billing/mpesa-callback/`) from the customer checkout callback
**And** the renewal task runs in the `billing.reminders` Celery queue — never `payments.reconciliation`

**Given** a renewal STK Push is confirmed
**When** the webhook callback is processed
**Then** `StoreSubscription.status` transitions to `active` and `current_period_end` is extended by one billing cycle

**Given** a renewal STK Push times out or is rejected
**When** the callback is processed
**Then** `StoreSubscription.status` transitions to `past_due`
**And** a 7-day grace period begins before suspension is triggered

### Story 9.4: Plan Limit Enforcement

As a store owner,
I want to be informed immediately when I try to exceed my plan's limits,
So that I know to upgrade rather than silently losing data or functionality.

**Acceptance Criteria:**

**Given** `enforce_plan_limit(store, feature, current_count)` is called in `apps/saas/services.py`
**When** `current_count >= plan.feature_limit` (e.g. `product_limit`, `staff_limit`)
**Then** HTTP 403 is returned with `PLAN_LIMIT_EXCEEDED` and a message indicating the current plan and limit

**Given** a bulk create operation is attempted (e.g. importing 50 products)
**When** adding all items would exceed the plan limit
**Then** `enforce_plan_limit()` is called before the bulk insert and the entire import is rejected with `PLAN_LIMIT_EXCEEDED`

**Given** a store upgrades to a higher plan
**When** `enforce_plan_limit()` is called after the upgrade
**Then** the new higher limit is evaluated — no cache invalidation needed (limit read from `request.store.subscription.plan` per request)

### Story 9.5: AI Scaffold (501 Endpoints)

As a platform engineer,
I want `apps/ai/` to exist from day one with correct structure and plan-gated 501 endpoints,
So that activating AI requires only implementation, not restructuring.

**Acceptance Criteria:**

**Given** `apps/ai/` exists with `models.py`, `services.py`, `views.py`
**When** any AI endpoint is called (e.g. `GET /api/v1/ai/recommendations/`)
**Then** HTTP 501 is returned with `{"detail": "AI_NOT_LIVE"}`

**Given** the store's plan has `ai_access=False`
**When** any AI endpoint is called
**Then** HTTP 403 is returned with `PLAN_FEATURE_UNAVAILABLE` — evaluated before the 501 handler

**Given** `./manage.py spectacular --validate` is run
**When** validated
**Then** all AI endpoints appear in the OpenAPI schema with their 501 and 403 responses documented

### Story 9.6: Merchant Onboarding Runbook

As a platform operator,
I want a documented runbook for onboarding a new merchant from zero to live in under 24 hours,
So that third-merchant onboarding — the core thesis validation — can happen reliably.

**Acceptance Criteria:**

**Given** the provisioning runbook exists at `docs/runbooks/merchant-onboarding.md`
**When** followed by any operator
**Then** it covers: store creation via API, domain assignment, Nginx config update, SSL certificate, subscription activation, and first-order smoke test
**And** the total steps can be completed in under 24 hours by an operator following the runbook for the first time

**Given** the runbook specifies the `scripts/preflight.sh` step
**When** preflight is run post-provisioning
**Then** it validates the new domain is resolvable and the store returns HTTP 200

**Given** the provisioning runbook is followed for a new tenant
**When** the `nginx/conf.d/tenants/{store_slug}.conf` file is created
**Then** a helper script `scripts/add-tenant-domain.sh <store_slug> <domain>` generates the correct Nginx config and reloads Nginx automatically — no manual SSH file editing required
**And** the script is idempotent (running it twice for the same domain does not create duplicate config)

### Story 9.7: Automated Subscription Suspension + PII Anonymisation Pipeline

As a platform operator,
I want subscription suspension and data anonymisation to happen automatically on schedule without any manual intervention,
So that the platform enforces its own business rules reliably.

**Acceptance Criteria:**

**Given** the Celery Beat schedule includes `enforce_subscription_states` running daily
**When** the task runs
**Then** all `StoreSubscription` records in `past_due` status where `grace_period_ends_at < now()` are transitioned to `suspended`
**And** the corresponding `Store.status` is set to `suspended` in the same atomic operation
**And** a `StoreStatusChanged` event is logged for each suspended store

**Given** a store transitions to `suspended`
**When** a storefront request arrives for that store
**Then** HTTP 503 is returned — verified by the existing Story 1.2 AC, now also verified to trigger from this automated path

**Given** a `StoreSubscription` is in `cancelled` status and `cancelled_at + 90 days < now()`
**When** the daily `enforce_subscription_states` task runs
**Then** the anonymisation pipeline is triggered: all customer PII records for that store are soft-deleted and anonymised via the safedelete hook
**And** the `Store` record itself is anonymised (name → "Deleted Store {uuid}", domain → null)
**And** a `PIIAnonymisationLog(store, triggered_at, record_count)` entry is created for Kenya DPA 2019 audit purposes

**Given** the anonymisation pipeline fails partway through (e.g. DB timeout)
**When** the task retries via exponential backoff
**Then** already-anonymised records are not double-processed (idempotent via `anonymised_at` timestamp check)
**And** after max retries, the failure is sent to DLQ and a Sentry alert is raised for manual review

---

## Epic 10: Customer Loyalty + Engagement

Repeat customers earn points and stamp rewards. A unified account shows all orders, reservations, and jobs across stores. WhatsApp notifications keep customers engaged without app downloads.

### Story 10.1: LoyaltyAccount (Points Balance + History)

As a repeat customer,
I want to earn points on every purchase at any store that has loyalty enabled,
So that my patronage is rewarded automatically.

**Acceptance Criteria:**

**Given** a store has loyalty enabled and a customer completes an order
**When** the order transitions to `confirmed`
**Then** a `LoyaltyAccount` record is retrieved or created for that customer + store combination
**And** points are credited based on the store's configured points-per-currency-unit rate

**Given** `GET /api/v1/loyalty/account/` is called by an authenticated customer
**When** the response is returned
**Then** it includes: `points_balance`, `points_history` (paginated list of credit/debit events with timestamps)

**Given** a customer earns points at Store A
**When** they view their balance at Store B
**Then** only Store B's `LoyaltyAccount` is returned — points are store-scoped, never cross-tenant

### Story 10.2: StampCard (Auto-Reward on Threshold)

As a customer,
I want to automatically receive a reward when I reach the stamp threshold,
So that loyalty rewards feel effortless and instant.

**Acceptance Criteria:**

**Given** a `StampCard` is configured by a store owner with `threshold` (e.g. 10 stamps) and `reward` (e.g. "Free coffee")
**When** a customer's stamp count reaches the threshold
**Then** the reward is automatically triggered via a `post_save` signal + `transaction.on_commit` Celery task
**And** a WhatsApp or SMS notification is dispatched to the customer with the reward details

**Given** a reward is triggered
**When** the `StampCard` resets
**Then** the stamp count returns to 0 and a new stamp cycle begins

### Story 10.3: WhatsApp Notification Dispatch

As a store owner,
I want to send customers transactional and engagement notifications via WhatsApp without requiring them to download an app,
So that communication reaches them where they already are.

**Acceptance Criteria:**

**Given** a notification event is triggered (order confirmed, loyalty reward, reservation confirmed, renewal reminder)
**When** the notification task runs on the `engagement.notifications` Celery queue
**Then** a WhatsApp message is dispatched to the customer's phone via the configured WhatsApp Business API integration

**Given** a WhatsApp dispatch fails (API error or invalid number)
**When** the task retries
**Then** exponential backoff is applied and after max retries the failure is sent to DLQ with the customer ID and event type

**Given** a customer has not opted in to WhatsApp notifications
**When** a notification would be dispatched
**Then** the task checks opt-in status before sending — no messages to opted-out customers

### Story 10.4: Unified Customer Account

As a customer who shops at multiple joat_stores-powered stores,
I want a single login to see all my orders, reservations, and jobs across every store,
So that I have one place to track everything.

**Acceptance Criteria:**

**Given** a customer authenticates with their unified account credentials
**When** `GET /api/v1/customer/profile/` is called
**Then** it returns: all orders (across all stores), all reservations, all contracting jobs, and the loyalty balance per store

**Given** the unified account is accessed
**When** data is returned
**Then** each record is clearly labeled with its originating store name
**And** tenant isolation is maintained — customers can only view their own records, never other customers'

**Given** a customer's unified account is deleted
**When** the soft-delete + PII anonymisation runs
**Then** their PII is anonymised across all store records simultaneously

### Story 10.5: WhatsApp Ordering Bridge

As a customer,
I want to order from a restaurant via WhatsApp by typing item names and receiving a PIN to use when I arrive,
So that I can order without opening a browser.

**Acceptance Criteria:**

**Given** a customer sends a WhatsApp message to the store's WhatsApp Business number with menu item names
**When** the bot processes the message
**Then** a `PendingOrder` is created with the matched items and a 6-digit PIN
**And** the bot replies with: the order summary and the PIN ("Your order is ready. Show PIN 482910 to your waiter.")

**Given** an item name in the WhatsApp message does not match any menu item
**When** the bot processes it
**Then** the bot replies with: "I didn't recognize '[item]'. Here's our menu: [link to public menu URL]"

**Given** a `PendingOrder` created via WhatsApp
**When** the waiter enters the PIN on the waiter screen
**Then** it converts to a `DineInOrder` identically to a web-created `PendingOrder`

### Story 10.6: "Powered by joat_stores" Viral Footer

As a platform operator,
I want the joat_stores brand to appear subtly on storefronts of lower-tier plans,
So that customer traffic on those storefronts generates organic platform awareness.

**Acceptance Criteria:**

**Given** a store is on a plan with `features.viral_footer=True`
**When** any storefront page renders
**Then** a "Powered by joat_stores" footer link is visible, linking to the merchant signup page

**Given** a store upgrades to a plan with `features.viral_footer=False`
**When** the storefront renders
**Then** the footer is hidden — no code change or redeployment required

**Given** `features.viral_footer` is evaluated
**When** the storefront renders
**Then** it is read from `request.store.subscription.plan` — never hardcoded per store

---

## Epic 11: AI + Personalization

Menu recommendations, peak hour predictions, and NLP search — all gated behind `plan.features.has_ai`. Built on the `AIEvent` data captured from day one.

### Story 11.1: Recommendation Engine

As a customer browsing a menu,
I want to see personalized item recommendations based on what I and similar customers have ordered before,
So that I discover items I'm likely to enjoy without having to search.

**Acceptance Criteria:**

**Given** a customer with at least 3 `AIEvent` records of type `order_completed` is browsing
**When** `GET /api/v1/ai/recommendations/?store_id={id}` is called
**Then** up to 5 recommended `MenuItem` IDs are returned, ranked by predicted preference
**And** recommendations are generated from the customer's own `AIEvent` history within the current store

**Given** the requesting store's plan has `ai_access=False`
**When** the recommendations endpoint is called
**Then** HTTP 403 is returned with `PLAN_FEATURE_UNAVAILABLE` — evaluated before any model inference

**Given** a customer has fewer than 3 order events
**When** recommendations are requested
**Then** the endpoint returns the store's top 5 most-ordered items as a fallback — never an empty array

### Story 11.2: Peak Hour Predictions

As a restaurant owner,
I want to see predicted busy hours for the coming week based on historical patterns,
So that I can staff correctly.

**Acceptance Criteria:**

**Given** at least 4 weeks of `HourlyOrderSummary` data exists for a store
**When** `GET /api/v1/ai/peak-hours/predict/` is called
**Then** a 24-slot array for each day of the coming week is returned with predicted order counts
**And** the prediction is clearly labeled as "estimated" in the response

**Given** the store's plan has `ai_access=False`
**When** the endpoint is called
**Then** HTTP 403 with `PLAN_FEATURE_UNAVAILABLE` is returned

**Given** insufficient historical data exists (< 4 weeks)
**When** the endpoint is called
**Then** HTTP 422 is returned with `INSUFFICIENT_DATA_FOR_PREDICTION` — never a fabricated result

### Story 11.3: NLP Menu Search

As a customer,
I want to search a menu using natural language (e.g. "something spicy and vegetarian under 500"),
So that I find what I want faster than scrolling through the full menu.

**Acceptance Criteria:**

**Given** `GET /api/v1/restaurant/menu/search/?q=something+spicy+vegetarian` is called
**When** the NLP search runs
**Then** a ranked list of `MenuItem` results is returned matching the query intent — not just keyword match

**Given** the store's plan has `ai_access=False`
**When** the endpoint is called
**Then** HTTP 403 with `PLAN_FEATURE_UNAVAILABLE` is returned

**Given** the search query matches no items
**When** the endpoint is called
**Then** an empty array is returned with a `"suggestion"` field: "Try searching for [example terms from this menu]"

**Given** the endpoint is called
**When** it responds
**Then** `StoreCursorPagination` is applied — no unbounded list response

---

## Epic 12: Production Hardening

Every PR runs a full CI gate. Deployments are automated on merge. Daily backups run with 7-day rotation. The platform passes OWASP Top 10 and Kenya DPA 2019 compliance.

### Story 12.1: GitHub Actions CI/CD Pipeline

As a developer,
I want every pull request to run a full automated quality gate and every merge to main to deploy automatically,
So that broken code never reaches production.

**Acceptance Criteria:**

**Given** a pull request is opened or updated
**When** the CI pipeline runs
**Then** it executes in order: `flake8` (Python linting), `black --check` (formatting), `isort --check` (import order), TypeScript strict compile (`tsc --noEmit`), `pytest` (full suite including `pytest -k "cross_tenant"`)
**And** any single step failure blocks the PR from merging

**Given** a commit is merged to `main`
**When** the CD pipeline runs
**Then** it deploys to the VPS via SSH, runs `scripts/preflight.sh`, and executes `docker compose up --build -d`
**And** on deployment failure, the pipeline sends a Sentry alert and does not proceed

**Given** a new API endpoint is added in a PR
**When** CI runs
**Then** `./manage.py spectacular --validate` is included in the CI gate and must pass

### Story 12.2: Daily Backup + Redis AOF Persistence

As a platform operator,
I want daily database backups with 7-day rotation and Redis data persisted across restarts,
So that data loss from any failure is bounded to at most 24 hours.

**Acceptance Criteria:**

**Given** Celery Beat triggers `scripts/backup.sh` daily
**When** the script runs
**Then** `pg_dump` produces a gzip-compressed file at `/backups/$(date +%Y-%m-%d).sql.gz`
**And** backups older than 7 days are deleted

**Given** the backup script runs
**When** `pg_dump` fails
**Then** an error is logged via structlog and a Sentry alert is raised — no silent failure

**Given** Redis is configured in `docker-compose.yml`
**When** the configuration is inspected
**Then** `appendonly yes` and `appendfsync everysec` are set in the Redis config
**And** the AOF file is stored on a named Docker volume (not an ephemeral layer)

### Story 12.3: OWASP Top 10 + Kenya DPA 2019 Compliance

As a platform security officer,
I want documented evidence that the platform addresses OWASP Top 10 and Kenya DPA 2019 requirements,
So that we pass a pre-production security review without surprises.

**Acceptance Criteria:**

**Given** the OWASP checklist at `docs/security/owasp-checklist.md`
**When** reviewed before production launch
**Then** all 10 OWASP categories are addressed with a documented control for each

**Given** PII fields (phone, email, address) in any model
**When** stored in the database
**Then** `django-encrypted-fields` is applied at field level — never encrypted in serializer logic

**Given** a customer account is deleted
**When** soft-delete runs
**Then** PII is anonymised via the safedelete hook: phone → random hash, email → `deleted_{uuid}@anon.joat`, name → "Deleted User"
**And** the anonymisation completes within the 72-hour Kenya DPA 2019 breach notification window requirement

**Given** any admin access to customer PII
**When** the access occurs
**Then** `AdminPIIAccessLog` is created (covered in Story 1.6 — verified here as a compliance gate)

### Story 12.4: Sentry + Structlog Full Integration

As a platform operator,
I want all unhandled exceptions and async task failures captured in Sentry and all logs emitted via structlog with PII masking,
So that I can diagnose production issues without exposing customer data.

**Acceptance Criteria:**

**Given** Sentry SDK is initialized in `config/settings/production.py`
**When** any unhandled exception occurs in Django, Celery worker, or Celery Beat
**Then** a Sentry event is captured with the full traceback

**Given** a Celery task fails after max retries
**When** it is sent to the DLQ
**Then** a Sentry alert is raised with task name, queue, and last exception

**Given** any code path emits a log statement
**When** it goes through structlog
**Then** it is structured JSON with `timestamp`, `level`, `logger`, `event`, and relevant context fields
**And** the PII scrubber processor has masked any phone or email values before emission

**Given** `print()` or bare `logging.info()` calls exist in the codebase
**When** `flake8` runs in CI
**Then** these calls are flagged as lint errors and block the PR

### Story 12.5: Store Admin PWA (Offline Inventory)

As a store manager on a slow mobile connection,
I want to count and update inventory on my phone even when offline and have it sync when I reconnect,
So that stock counts are accurate even in low-connectivity environments.

**Acceptance Criteria:**

**Given** the store admin Next.js app is accessed on a mobile browser
**When** the service worker registers
**Then** the inventory count page is cached for offline use

**Given** a store manager updates inventory counts while offline
**When** they tap Save
**Then** the updates are stored in IndexedDB locally with a `pending_sync` flag

**Given** the device reconnects to the network
**When** the sync runs
**Then** all `pending_sync` inventory updates are sent to the API and the `pending_sync` flag is cleared
**And** if a conflict is detected (server value changed since last sync), the manager is shown both values and prompted to choose

**Given** the store admin is loading on a budget Android device (Tecno, Infinix) on 3G
**When** the page renders
**Then** all tap targets are minimum 48×48px and the page is usable without horizontal scrolling at 320px width

### Story 12.6: Data Export + Merchant Daily View

As a store owner,
I want to see the most critical information — today's orders, revenue, and pending actions — the moment I open the admin, without any navigation,
So that I can run my store in 30 seconds of checking.

**Acceptance Criteria:**

**Given** a store owner or manager logs into the admin
**When** the dashboard loads
**Then** the first screen shows without navigation: today's order count, today's revenue, pending orders requiring action, and low-stock alerts
**And** this view is rendered on the server (SSR) — no skeleton or loading state for above-fold content

**Given** `GET /api/v1/store/export/` is called
**When** the store's plan has `features.raw_export=False`
**Then** HTTP 403 is returned with `EXPORT_NOT_AVAILABLE_ON_PLAN`

**Given** the store's plan has `features.raw_export=True` (enterprise)
**When** the export is requested
**Then** a CSV export of orders, products, and customer data (PII masked for non-owner roles) is returned
**And** the export is logged in `AdminPIIAccessLog`
