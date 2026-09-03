---
title: JOAT Stores
created: 2026-09-03
updated: 2026-09-03
status: final
---

# PRD: JOAT Stores

Multi-tenant SaaS e-commerce platform for Kenyan SMEs — bars, restaurants, and retail stores.

## 0. Document Purpose

This PRD defines the full launch requirements for JOAT Stores, a multi-tenant SaaS platform serving Kenyan SMEs. First client: a bar in Nairobi. Structured for PM, architect, and developer stakeholders. Features grouped by domain with globally-numbered FRs. Assumptions tagged inline and indexed. UX design lives in the existing MD3 glassmorphism token system; this PRD builds on it, not duplicates it.

## 1. Vision

JOAT Stores is a multi-tenant SaaS e-commerce platform purpose-built for Kenyan SMEs — starting with bars, expanding to restaurants, retail, and contracting businesses. The platform replaces fragmented paper-based systems and expensive imported POS solutions with a mobile-first, M-Pesa-native tool that a bar owner can set up in 10 minutes and use from day one.

The competitive moat is not features — it's trust, localization, and operational intelligence. Kenyan bar owners don't need another dashboard; they need to know "did I make money today?" and "who's stealing from me?" delivered via WhatsApp where they already communicate. The platform charges subscription fees (KES 2,500–15,000/month) with transaction-based revenue upside, targeting 10 bar clients in year 1 with KES 500,000–800,000 ARR.

## 2. Target Users

### 2.1 Jobs To Be Done

**Bar Owner (Primary):**
- Track daily revenue without counting cash manually for 2 hours
- Monitor which products sell during happy hour vs late night
- Detect staff theft (voided orders, comped drinks, missing cash)
- Reconcile M-Pesa payments against expected revenue at end-of-day
- Manage tabs for groups ordering rounds over hours

**Waiter/Staff:**
- Open tabs quickly for walk-in customers
- Add rounds without leaving the order screen
- Process M-Pesa payments without fumbling with Safaricom portal
- Close tabs fast during rush hour

**Platform Admin (KAFURAHA):**
- Onboard new bar clients with pre-loaded menu templates
- Monitor tenant health and subscription status
- Support clients without accessing their private data

### 2.2 Non-Users (v1)

- Customers ordering via website (v1 is staff-facing only for bars)
- Multi-location bar chains (single-location in v1)
- Bars without M-Pesa (cash-only bars need manual EOD only)

### 2.3 Key User Journeys

**UJ-1. Bar Owner Onboarding (sign-up → first tab closed)**
- **Persona + context:** James, bar owner in Westlands, has 50+ drinks on menu, currently uses paper tabs and manual M-Pesa reconciliation
- **Entry state:** Receives onboarding email with credentials and PWA link
- **Path:** Login → guided menu setup (pre-loaded Tusker/White Cap template) → configure one happy hour window → open test tab → add round → request bill → settle via M-Pesa
- **Climax:** First successful M-Pesa settlement with correct happy hour pricing applied automatically
- **Resolution:** Owner sees revenue on dashboard, receives WhatsApp confirmation. **Edge case:** M-Pesa STK Push fails → fallback to cash payment with manual close

**UJ-2. Waiter Taking an Order (order entry → payment collected)**
- **Persona + context:** Grace, waiter at James's bar, handles 30+ tabs per shift
- **Entry state:** Customer walks in, asks for a tab
- **Path:** Open tab (walk-in, no auth) → add Tusker Lager (happy hour: KES 350 → KES 250) → add Batch Cocktail → customer says "close tab" → request bill → STK Push to customer phone → customer enters PIN → payment confirmed → tab auto-settles
- **Climax:** Payment confirmed, tab status changes to SETTLED, Grace sees confirmation
- **Resolution:** Tab closed, revenue logged, inventory counts down. **Edge case:** Customer's phone is off → staff records cash payment manually

**UJ-3. End-of-Day Reconciliation (last order → books balanced)**
- **Persona + context:** James, closing up at 11pm, needs to reconcile before going home
- **Entry state:** All tabs closed for the night
- **Path:** Tap "Run EOD" → system shows: 89 tabs settled, KES 47,200 total revenue, KES 38,100 M-Pesa, KES 9,100 cash, 0 open tabs, variance KES 0 → confirm and close
- **Climax:** Owner sees clean reconciliation report, knows exactly what happened tonight
- **Resolution:** EOD report sent via WhatsApp, data aggregated for trend analysis. **Edge case:** Variance > 2% → system flags discrepancy and asks owner to verify cash count

**UJ-4. Platform Admin Onboarding a New Client**
- **Persona + context:** KAFURAHA, platform admin, onboarding James's bar
- **Entry state:** Client has signed up, needs store created
- **Path:** Platform admin → Add Store → enter name/domain/type/owner email → upload logo → create → system generates temp password → sends onboarding email with PWA link + admin link + credentials → admin sees onboarding success dialog with all details
- **Climax:** Client receives email with everything needed to start
- **Resolution:** Client logs in, follows guided setup. **Edge case:** Email fails to deliver → admin can manually share credentials

## 3. Glossary

- **Tab** — An open running order for a customer. Contains multiple TabRounds. Status: OPEN → BILL_REQUESTED → SETTLED → CLOSED.
- **TabRound** — A single round of drinks added to a tab. System snapshots pricing (including happy hour) at add-time.
- **TabShare** — A payment portion of a tab. Supports split-bill (multiple M-Pesa payments) or single payment.
- **Happy Hour** — Time-based pricing rule. Discount applied automatically when TabRound is added during the happy hour window.
- **EOD Reconciliation** — End-of-day process comparing M-Pesa settled amounts against expected revenue from closed tabs.
- **BarDailyReconciliation** — Daily artifact recording: tab_count, total_revenue, total_collected, discrepancy, payment_method_breakdown, reconciled_by.
- **Store** — A tenant (bar, restaurant, or retail business). All data scoped to store_id via TenantModel.
- **TenantMiddleware** — Resolves request.store from Host header or X-Store-ID header (platform_admin only).
- **M-Pesa STK Push** — Safaricom's Lipa Na M-Pesa Online API. Initiates payment request to customer's phone.
- **Daraja** — Safaricom's M-Pesa API platform (sandbox and production).
- **PWA** — Progressive Web App. Installable web application with offline capability.
- **DailyRevenueSummary** — Pre-aggregated daily analytics: total_revenue, order_count, aov, top_products.
- **HourlyOrderSummary** — Pre-aggregated hourly analytics: order_count, revenue per hour.

## 4. Features

### 4.1 Multi-Tenant Store Management
**Description:** Every domain model inherits TenantModel (UUID PK + store FK + soft-delete). TenantMiddleware resolves request.store from Host header or X-Store-ID header. JWT claims include store_id and role. Four roles: platform_admin, store_owner, store_manager, customer.

**FR-1: Tenant Isolation Enforcement**
Store users resolve tenant exclusively from JWT store_id claim. X-Store-ID header accepted only for platform_admin role. Middleware rejects non-admin requests with X-Store-ID header via 403.

**Consequences (testable):**
- Store owner with JWT for Store A cannot access Store B data even with forged X-Store-ID header
- Platform admin can access any store via X-Store-ID header
- Cross-tenant isolation tests pass (pytest -m cross_tenant)

**FR-2: Store Provisioning**
Platform admin creates store with: name, domain, tenant_type, owner_email, logo. System generates temporary password, sends onboarding email with PWA link, admin link, and credentials.

**Consequences (testable):**
- Store created with correct tenant_type and domain
- Owner user created with store FK
- Trial subscription created automatically
- Onboarding email sent via Celery within 60 seconds
- Onboarding dialog shows owner email, temp password, PWA link, admin link

**FR-3: Store Logo Upload**
Platform admin can upload store logo (jpg, png, webp, max 5MB) during store creation. Store owner can change logo from admin dashboard. Logo appears in storefront header and onboarding email.

**Consequences (testable):**
- Logo uploaded to Supabase storage (or local media in dev)
- Logo URL saved to StoreSettings.logo_url
- Onboarding email renders logo inline (200x200px)
- Storefront header displays uploaded logo

### 4.2 Product Catalog
**Description:** Products with categories, variants, pricing, images. Restaurant/Bar uses MenuSection/MenuItem instead of ProductCategory/Product.

**FR-4: Product Image Upload**
Store owner can upload up to 5 images per product (jpg, png, webp, max 5MB each). First image is default. Images can be reordered. Alt text auto-populated from product name.

**Consequences (testable):**
- Product creation form includes image upload section
- Images uploaded to storage and linked to ProductImage model
- Product list shows default image thumbnail (48x48px)
- Product detail shows image gallery
- Max 5 images enforced at API level

**FR-5: Pre-loaded Bar Menu Templates**
New bar tenants receive pre-loaded menu with Kenyan beverages (Tusker, White Cap, BATCH cocktails, spirits, mixers, snacks). Templates seeded via management command.

**Consequences (testable):**
- `seed_bar_menu` command creates MenuSection and MenuItem records
- Menu sections: Beers, Spirits, Cocktails, Soft Drinks, Snacks
- Items include KES pricing, age_restricted flag for alcohol
- Owner can edit/delete template items after onboarding

### 4.3 Tab Management
**Description:** Open tabs for walk-in customers, add rounds, request bill, settle via M-Pesa or cash. Tab state machine: OPEN → BILL_REQUESTED → SETTLED → CLOSED.

**FR-6: Tab Lifecycle**
Staff opens tab (walk-in, no customer auth), adds TabRounds with items, system snapshots pricing at add-time (including happy hour), staff requests bill, customer pays via M-Pesa or cash, tab auto-settles.

**Consequences (testable):**
- Tab created with status OPEN
- TabRound added with items_snapshot JSON (prices frozen at add-time)
- Happy hour discount applied automatically if within window
- Tab transitions to BILL_REQUESTED when bill requested
- Tab transitions to SETTLED when payment confirmed
- Tab transitions to CLOSED after settlement

**FR-7: Cash Payment Flow**
Staff can close a tab by marking it as paid cash. Endpoint: POST /api/v1/bar/tabs/{id}/pay-cash/. Marks all TabShares as PAID, transitions tab to SETTLED.

**Consequences (testable):**
- Cash payment endpoint exists and works
- Tab status changes to SETTLED
- Revenue logged with payment_method="cash"
- EOD reconciliation includes cash payments

**FR-8: Happy Hour Pricing**
Owner configures happy hour windows (e.g., 6pm-8pm daily). System applies discount automatically when TabRound is added during window. Pricing frozen at add-time — doesn't change if happy hour ends while tab is open.

**Consequences (testable):**
- Happy hour configuration saved (start_time, end_time, discount_percent)
- TabRound added during happy hour gets discounted price
- TabRound added outside happy hour gets regular price
- Price snapshot stored in TabItem — not recalculated at settlement

**FR-9: Age Restriction Gate**
Alcohol items flagged as age_restricted. System requires age acknowledgement before first alcohol add per tab. AgeRestrictionLog records acknowledgement.

**Consequences (testable):**
- Menu items with age_restricted=true show age gate
- First alcohol item on tab requires age acknowledgement
- AgeRestrictionLog created with staff_id and timestamp
- Subsequent alcohol adds on same tab bypass gate

### 4.4 Payment Processing (M-Pesa)
**Description:** M-Pesa STK Push for customer payments. C2B for paybill/till. Webhook callbacks for payment confirmation. Reconciliation of payments against tabs.

**FR-10: M-Pesa STK Push**
Staff initiates STK Push to customer's phone. Customer enters PIN. Payment confirmed via webhook. Tab auto-settles.

**Consequences (testable):**
- STK Push initiated via Daraja API
- CheckoutRequestID stored on MpesaTransaction
- Webhook callback received and processed
- Payment status updated to CONFIRMED
- Tab status updated to SETTLED
- Timeout handling: if no callback in 120s, mark as TIMEOUT

**FR-11: M-Pesa Callback Security**
C2B validation endpoint verifies Daraja HMAC signature before processing. MPESA_WEBHOOK_SECRET required in production (ImproperlyConfigured if missing). Callback endpoint uses AllowAny with authentication_classes=[] but validates signature.

**Consequences (testable):**
- Valid callback with correct HMAC processed successfully
- Invalid callback rejected with 403
- Missing MPESA_WEBHOOK_SECRET in production raises ImproperlyConfigured
- Callback flood (DoS) handled via rate limiting

**FR-12: Payment Reconciliation**
Celery task reconciles payments: checks for STK Push timeouts, confirms pending payments, flags discrepancies. Runs every 60 seconds.

**Consequences (testable):**
- STK Push timeouts detected and marked
- Pending payments confirmed when callback arrives late
- Discrepancies flagged for manual review
- Task runs reliably in Celery worker

### 4.5 End-of-Day Reconciliation
**Description:** Daily reconciliation report comparing M-Pesa settled amounts against expected revenue. New BarDailyReconciliation model.

**FR-13: EOD Reconciliation Report**
System generates daily report: total tabs settled, total revenue, total collected (M-Pesa + cash), discrepancy amount, payment method breakdown. Triggered automatically at midnight via Celery Beat or manually by staff.

**Consequences (testable):**
- BarDailyReconciliation record created with correct aggregates
- Discrepancy calculated: total_revenue - total_collected
- Payment method breakdown JSON: {"mpesa": X, "cash": Y}
- Report accessible via API: GET /api/v1/bar/reconciliation/?date=YYYY-MM-DD
- WhatsApp summary sent to store owner

**FR-14: WhatsApp Daily Summary**
System sends daily summary to store owner via WhatsApp at 10pm EAT. Format: "Yesterday: KES 47,200 revenue, 89 orders, top seller: Tusker Lager (42 units)."

**Consequences (testable):**
- Celery Beat task triggers at 22:00 EAT
- WhatsApp message sent via Twilio/Meta API
- Message includes: revenue, order count, top 3 items, vs yesterday comparison
- Failed sends logged and retried once

### 4.6 Storefront (PWA)
**Description:** Customer-facing PWA for menu browsing and ordering. Service worker for offline caching. Installable to home screen.

**FR-15: PWA Install Flow**
Customers can install the storefront as a PWA. Service worker caches shell (CSS, fonts, logo) with stale-while-revalidate. Manifest.json with display: standalone.

**Consequences (testable):**
- Service worker registered at /storefront/public/sw.js
- Manifest.json present with correct start_url and display mode
- Offline: cached shell loads, API calls fail gracefully
- Install prompt appears on supported browsers

**FR-16: QR Code Ordering**
Bar tables have QR codes encoding store_id + table_id + HMAC. Customers scan QR → see menu → order → pay. "Call waiter" button for walk-ins who don't want to self-order.

**Consequences (testable):**
- QR code URL resolves to menu view with correct store/table
- Menu shows available items with current happy hour status
- "Call waiter" button sends notification to admin dashboard
- PendingOrder model supports pre-arrival ordering with 6-digit PIN

### 4.7 Admin Dashboard
**Description:** Store owner dashboard for managing menu, tabs, staff, and viewing analytics. Material Design 3 glassmorphism design with light/dark mode.

**FR-17: Real-time Dashboard KPIs**
Dashboard shows: today's M-Pesa revenue, open tabs count with total exposure, drinks-per-hour velocity, staff performance (orders per waiter per shift).

**Consequences (testable):**
- KPIs update without page refresh (polling or WebSocket)
- Open tabs count matches active Tab records
- Revenue matches sum of SETTLED tabs for today
- Staff performance shows orders-per-waiter

**FR-18: Product Management**
Owner can add/edit/delete products with images, pricing, categories. Bulk import from CSV. Product search and filtering.

**Consequences (testable):**
- Product CRUD operations work via API
- Product images upload and display
- CSV import parses and creates products
- Search returns relevant results

**FR-19: Staff Management**
Owner can add staff with PIN login (not full auth — just waiter identification on rounds). Staff performance tracked per shift.

**Consequences (testable):**
- Staff records created with name and PIN
- Waiter identifies themselves when opening tab
- Orders attributed to correct staff member
- Staff performance report shows orders-per-waiter

### 4.8 Platform Administration
**Description:** Platform admin dashboard for managing tenants, subscriptions, and monitoring health.

**FR-20: Platform Metrics**
Platform admin sees: total stores, active subscriptions, total revenue, orders, health status, recent signups, plan distribution.

**Consequences (testable):**
- Metrics API returns all KPIs
- Dashboard renders 12 KPI cards across 3 rows
- Stores table shows all tenants with status
- Health panel shows database, Redis, Celery, worker status

**FR-21: Subscription Management**
Platform admin can create/edit plans. Plans: Free, Starter, Growth, Pro. Each plan has: price, features, limits. Subscription billing enforced (stores suspended after 7-day grace period).

**Consequences (testable):**
- Plan CRUD operations work
- Subscription created on store provisioning
- Billing check runs daily via Celery Beat
- Stores past grace period get suspended
- Suspended stores cannot serve orders

### 4.9 Notifications
**Description:** Celery-based notification system for order updates, inventory alerts, billing reminders, payment reconciliation.

**FR-22: Order Notifications**
Staff receives notification when order status changes. Customer receives M-Pesa confirmation. Store owner receives daily summary.

**Consequences (testable):**
- Celery task sends notification within 5 seconds of status change
- Notifications queued in order.notifications queue
- Failed notifications logged and retried

**FR-23: Inventory Alerts**
System monitors stock levels. Low-stock items trigger WhatsApp notification to owner.

**Consequences (testable):**
- Inventory threshold configured per product
- Alert triggered when stock falls below threshold
- WhatsApp message sent with product name and current stock
- Alert queued in inventory.alerts queue

### 4.10 Customer Hub
**Description:** Cross-tenant customer lookup for loyalty and marketing. Customers can see which stores they've interacted with.

**FR-24: Customer Store Discovery**
Authenticated customers can discover stores they've interacted with via email/phone lookup.

**Consequences (testable):**
- Hub endpoint returns stores for authenticated customer
- Customer data is anonymized (no PII leakage)
- Results scoped to customer's interactions only

### 4.11 Subscription & Billing
**Description:** Tiered subscription model with feature gating and usage limits.

**FR-25: Subscription Tiers**
- Free: 1 store, 100 transactions/month, basic M-Pesa only
- Starter (KES 2,500/mo): tabs, reconciliation, happy hour
- Growth (KES 7,500/mo): multi-staff, analytics, inventory
- Pro (KES 15,000/mo): API access, white-label, priority support

**Consequences (testable):**
- Free tier limited to 100 transactions/month
- Starter unlocks tabs + reconciliation features
- Growth unlocks staff management + analytics
- Pro unlocks API access + white-label
- Upgrade prompts trigger at transaction limit or feature gate

**FR-26: Subscription Billing**
Monthly billing cycle. M-Pesa STK Push for payment. 7-day grace period after expiry. Suspension after grace period.

**Consequences (testable):**
- Billing check runs daily via Celery Beat
- STK Push initiated 3 days before expiry
- Grace period: 7 days after expiry
- Suspension: store cannot serve orders after grace period
- Re-activation: payment received during suspension

## 5. Non-Goals (Explicit)

- **Multi-location bar chains** — v1 is single-location per tenant
- **Card payments (Stripe/Flutterwave)** — Kenyan bar customers pay M-Pesa or cash. Story 2.6 is a 501 scaffold.
- **Restaurant features** — table reservations, kitchen display, order queuing. Bar has tabs, not tables.
- **Contracting features** — irrelevant to bar vertical
- **AI recommendations** — bar customers know what they want
- **Loyalty program** — bars need fast service and cold beer, not points
- **E-commerce storefront** — WhatsApp IS the storefront for bars
- **Push notifications (FCM)** — staff don't need push notifications
- **WhatsApp/USSD integration** — deferred to v2/v3 due to complexity
- **Offline-first** — deferred to v2/v3 due to sync complexity
- **Staff tip tracking** — deferred to v2
- **Stock depletion per pour** — deferred to v2
- **Supplier integration** — deferred to v3
- **KRA iTax integration** — deferred to v3
- **AI-powered demand forecasting** — deferred to v3

## 6. MVP Scope

### 6.1 In Scope

- Tab management (open/add rounds/request bill/settle)
- M-Pesa STK Push payment
- Cash payment (manual close by staff)
- Happy hour pricing (auto-discount)
- Age restriction gate
- Pre-loaded Kenyan bar menu templates
- Product image upload (up to 5 per product)
- Store logo upload
- EOD reconciliation report (raw SQL, no model in v1)
- WhatsApp daily summary (via Twilio, week 3-4)
- Store provisioning with onboarding email
- Platform admin dashboard (metrics, stores, plans)
- PWA storefront (basic menu display)
- QR code ordering (basic)
- Tenant isolation fix (X-Store-ID for platform_admin only)
- Celery worker enabled in render.yaml
- Sentry error monitoring
- UptimeRobot health checks

### 6.2 Out of Scope for MVP

- **Subscription billing enforcement** — models exist, no payment collection (week 3-4)
- **Staff management with PIN login** — week 3-4
- **Real-time order tracking** — month 2
- **WhatsApp as storefront** — month 2-3
- **Inventory alerts** — month 2
- **Multi-store analytics** — month 2
- **Card payments** — never for bar vertical
- **Restaurant features** — different vertical
- **Contracting features** — different vertical
- **AI features** — different vertical
- **Loyalty program** — different vertical

## 7. Success Metrics

**Primary:**
- **SM-1:** Bar owner can open tab → add rounds → settle via M-Pesa → close tab in under 2 minutes. Validates FR-6, FR-10.
- **SM-2:** Daily reconciliation matches within 2% variance for 95%+ of days. Validates FR-13.
- **SM-3:** Zero critical incidents (lost tabs, payment failures, cross-tenant data leaks) during operating hours. Validates FR-1, FR-10, FR-11.

**Secondary:**
- **SM-4:** Bar owner receives WhatsApp daily summary without manual follow-up, saving 30+ min/day vs previous process. Validates FR-14.
- **SM-5:** New bar client can set up menu and close first tab within 10 minutes of onboarding. Validates FR-2, FR-5.
- **SM-6:** 60% of free-tier clients convert to paid within 3 months. Validates FR-25.

**Counter-metrics (do not optimize):**
- **SM-C1:** Order processing speed — don't optimize for speed at expense of accuracy. A payment that completes instantly but incorrectly is worse than one that takes 30 seconds and is correct.
- **SM-C2:** Revenue per client — don't maximize revenue extraction from early clients. Trust-building matters more than short-term revenue.

## 7.5 Non-Functional Requirements (from Review)

| NFR | Description | Value |
|-----|-------------|-------|
| NFR-23 | API rate limiting per store | 100-2000 req/min based on plan |
| NFR-24 | Audit logging for admin actions | 100% of admin mutations |
| NFR-25 | Data retention for M-Pesa transactions | 12 months minimum |
| NFR-26 | JWT secret rotation frequency | Quarterly (90 days) |
| NFR-27 | Consent management | Explicit opt-in required |
| NFR-28 | DSAR response time | 30 days maximum |
| NFR-29 | Backup encryption | AES-256 for database backups |
| NFR-30 | Incident response time | 72 hours (DPA 2019 §42) |
| NFR-31 | Request body size limit | 2.5MB general, 5MB for file uploads |
| NFR-32 | Session timeout | 1 hour for Django admin sessions |
| NFR-33 | CORS pre-flight caching | 24 hours (86400 seconds) |

## 7.6 API Surface (from Review)

| Method | Endpoint | Purpose | Notes |
|--------|----------|---------|-------|
| POST | `/api/v1/bar/tabs/{id}/pay-cash/` | Close tab with cash payment | FR-7 |
| GET | `/api/v1/bar/reconciliation/` | EOD reconciliation report | FR-13, query param: date |
| POST | `/api/v1/auth/staff-pin/` | Staff PIN authentication | FR-19 |
| GET | `/api/v1/storefront/qr-verify/` | QR code verification | FR-16 |
| POST | `/api/v1/bar/tabs/{id}/request-bill/` | Request bill for tab | FR-6 |
| GET | `/api/v1/health/celery/` | Celery worker health check | Addendum A2 |
| POST | `/api/v1/hub/dsar-request/` | Customer data access request | Kenya DPA 2019 §26 |
| DELETE | `/api/v1/hub/consent/{type}/` | Consent withdrawal | Kenya DPA 2019 §30 |

## 8. Open Questions

1. **OQ-1:** Should EOD reconciliation be automatic at midnight or manual by staff? Affects BarDailyReconciliation write path and notification flow.
2. **OQ-2:** What Supabase plan is needed when 500MB limit is approached? Current projection: ~2 years with 10 active stores.
3. **OQ-3:** Should the platform charge transaction fees (0.5% on M-Pesa) in addition to subscriptions? Revenue upside but adds complexity.
4. **OQ-4:** What happens when Render free tier worker crashes during peak hours? Need heartbeat monitoring and alerting.
5. **OQ-5:** How to handle M-Pesa API rate limits during peak hours for multiple tenants?
6. **OQ-6:** Should the bar menu template be configurable per region (Nairobi vs Mombasa drink preferences)?
7. **OQ-7:** What is the exact Twilio/Meta API cost per WhatsApp message for daily summaries?
8. **OQ-8:** How to handle M-Pesa recurring billing? M-Pesa doesn't support tokenized recurring charges like Stripe. Options: (a) new STK Push each cycle (bad UX), (b) M-Pesa Recurring Checkout API (if available), (c) manual "mark as paid" admin action.
9. **OQ-9:** Should the happy hour model support overnight windows (10pm-2am)? Current implementation fails for `start_time > end_time`.
10. **OQ-10:** What is the Render region for data residency? Currently `oregon` (US) — Kenya DPA 2019 may require Kenya/EAC hosting.
11. **OQ-11:** How to handle QR code HMAC secret rotation? Need 24h expiry on QR tokens.
12. **OQ-12:** Should we add `@require_age_acknowledgement` decorator at API level (not just UI prompt)?

## 9. Assumptions Index

- ASSUMPTION: Bar customers pay via M-Pesa or cash only (no cards) — inline from §4.4
- ASSUMPTION: First client is a single bar location, not a chain — inline from §5
- ASSUMPTION: Staff takes orders (not customer self-ordering via phone) — inline from §6.1
- ASSUMPTION: Kenyan bar owners check WhatsApp daily, not email — inline from §4.5
- ASSUMPTION: M-Pesa STK Push works reliably for 95%+ of transactions — inline from §4.4
- ASSUMPTION: Supabase free tier (500MB) is sufficient for 2+ years with 10 active stores — inline from §8 OQ-2
- ASSUMPTION: Render free tier is sufficient for MVP (1 bar client) — inline from §6.1
- ASSUMPTION: Happy hour pricing is a simple time-based discount, not complex rules engine — inline from §4.3 FR-8
- ASSUMPTION: Pre-loaded menu templates work for most Kenyan bars (Tusker, White Cap are universal) — inline from §4.2 FR-5
- ASSUMPTION: WhatsApp daily summary is sufficient for EOD reporting (no full dashboard needed) — inline from §4.5 FR-14
