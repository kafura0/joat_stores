---
stepsCompleted: [step-01-init, step-02-discovery, step-02b-vision, step-02c-executive-summary, step-03-success, step-04-journeys, step-05-domain, step-06-innovation, step-07-project-type, step-08-scoping]
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-joat_stores-2026-02-23.md
briefCount: 1
researchCount: 0
brainstormingCount: 0
projectDocsCount: 0
workflowType: 'prd'
author: KAFURAHA
date: 2026-02-24
classification:
  productType: "Commerce Infrastructure Platform"
  primaryLabel: "SaaS B2B Platform"
  secondaryLabel: "Headless Commerce Engine"
  domain: "E-Commerce / General"
  complexity: "Medium-High"
  complexityDrivers:
    - "Cross-tenant query isolation (every model, every endpoint, every test)"
    - "Async job reliability with monitoring (Celery + Redis)"
    - "Dual independent frontend applications (brand-isolated storefronts)"
    - "VPS zero-conflict deployment (hard infrastructure constraint)"
    - "Investor-demonstrable architecture (SaaS scaffold + observability)"
  projectContext: "Greenfield"
  uxSurfaces:
    - "Consumer storefront (Daniel / Amara journeys)"
    - "Store-scoped admin dashboard (Store Manager)"
    - "Platform admin dashboard (KAFURAHA)"
    - "Future merchant onboarding flow"
  criticalPRDControls:
    - "Tenant isolation AC on every data model"
    - "VPS pre-flight infrastructure AC"
    - "Minimal merchant onboarding spec"
    - "Async reliability + monitoring requirements"
    - "End-to-end checkout journeys with mobile AC"
  investorReadinessRequirements:
    - "Observability data model must be specced now (not retrofitted)"
    - "Third-merchant onboarding = core thesis validation feature"
    - "Unit economics tracking (cost-per-tenant vs revenue-per-tenant)"
---

# Product Requirements Document - joat_stores

**Author:** KAFURAHA
**Date:** 2026-02-24

---

## Executive Summary

joat_stores is a self-hosted, multi-tenant headless commerce operating system purpose-built for African SMEs. Starting in Kenya, the platform serves three primary verticals from a single infrastructure: **retail stores** (fashion, electronics, physical shops going online), **restaurants** (full-service, quick service, delivery), and **bars** (tab-based F&B operations with age-restricted menus and happy hour pricing). Each business operates as an isolated tenant on shared infrastructure, accessed via its own branded domain.

The platform replaces fragmented informal operations — Instagram DMs, WhatsApp orders, spreadsheet inventory, cash-only payments — with professional, analytics-driven digital commerce that merchants own outright. No per-store SaaS fees. No vendor lock-in. M-Pesa as a first-class payment rail across all three verticals.

A single Django + DRF backend resolves N independent storefronts and menus via domain-based tenant routing. Each tenant is a configurable **tenant type**: `retail`, `restaurant`, or `bar`. Tenant type activates the relevant feature modules — retail gets product variants, persistent cart, and shipping-ready order lifecycle; restaurants get modifier groups, QR-based dine-in with table management, takeaway, delivery order types, and kitchen order flow; bars get tab management, round ordering, age-restricted items, and happy hour pricing. Core infrastructure — auth, M-Pesa payments, analytics, async jobs, AI scaffold — is shared and tenant-type-agnostic.

**Target Users:** Kenyan SME owners across retail, restaurant, and bar verticals; store and venue managers; platform operator (KAFURAHA); future merchant tenants.

**90-Day Objective:** Retail stores live and processing orders. At least one F&B tenant live with dine-in and M-Pesa. 50+ transactions fulfilled. Third tenant onboarded live in under 24 hours for investor demo.

**Strategic Goal:** Become the Kenyan-first multi-vertical commerce operating system — retail, restaurants, and bars on a single platform — optimized for local payments, mobile-first UX, African-market pricing, and AI-powered growth intelligence.

---

### What Makes This Special

**1. M-Pesa-Native Across All Verticals** — STK Push at retail checkout, restaurant bill payment, and bar tab settlement. One payment integration, all three verticals.

**2. Multi-Vertical Tenant Architecture** — One platform, three business types. Tenant type is a configuration that activates the right module set — not a separate codebase per vertical. Adding a fourth vertical in future requires a new tenant type config, not a rebuild.

**3. Analytics as the Core Product** — Every merchant gets full business visibility: sales trends, AOV, customer LTV, inventory/menu performance, order conversion. F&B adds peak hour analysis, table turn rate, and menu item conversion. Bars add tab completion rate and round size analytics.

**4. AI-Augmented Infrastructure (Architecture-Ready)** — Recommendation engine, dynamic pricing, inventory/ingredient forecasting, customer segmentation. Scaffolded for all three verticals from day one.

**Core Insight:** Kenyan SMEs — whether selling clothes, serving food, or running a bar — are active operators right now. They lack infrastructure, not demand. joat_stores gives them the operating system their businesses already deserve.

**Why Now:** M-Pesa ubiquity, Next.js and Django maturity, Shopify price increases, and the accelerating move from informal digital selling to owned storefronts create a precise market window for a locally-optimized, self-hosted, multi-vertical commerce platform.

---

## Project Classification

| Attribute | Value |
|---|---|
| Product Type | Multi-Vertical Commerce Infrastructure Platform |
| Primary Classification | SaaS B2B Platform |
| Secondary Classification | Headless Commerce Engine + F&B Operating System |
| Domain | E-Commerce + Food & Beverage / General |
| Complexity | Medium-High |
| Project Context | Greenfield |
| Tenant Types | `retail`, `restaurant`, `bar` |

**Complexity Drivers:**
- Cross-tenant query isolation enforced at every layer (middleware, queryset, serializer, permissions)
- Async job reliability with monitoring (Celery + Redis — silent failure is a launch risk)
- Multi-vertical tenant type system (retail vs F&B module activation per tenant)
- Dual+ independent frontend applications (brand-isolated Next.js storefronts)
- VPS zero-conflict deployment (hard constraint — existing live services must not be disrupted)
- Investor-demonstrable architecture (SaaS scaffold, AI placeholder, observability data model)

**Critical PRD Controls:**
- Tenant isolation acceptance criteria required on every data model
- VPS pre-flight infrastructure acceptance criteria required
- Minimal merchant onboarding flow must be specced with acceptance criteria
- Async reliability + monitoring requirements (dead-letter queue, worker health, retry logic)
- End-to-end checkout and dine-in journeys with mobile-specific acceptance criteria

---

## Success Criteria

### User Success

**Retail Shoppers**

| Persona | Success Moment | Measurable Target |
|---|---|---|
| Tech Shopper | Finds product, reads specs, buys | Search-to-cart < 60 seconds |
| Tech Shopper | Frictionless checkout | Cart-to-confirmed order < 3 minutes |
| Tech Shopper | Payment confirmation | M-Pesa STK Push received < 10 seconds after checkout |
| Fashion Shopper | Variant clarity before purchase | Zero "wrong size" returns in Month 1 |
| Fashion Shopper | Completes purchase on mobile | >60% of orders completed on mobile browser |
| Fashion Shopper | Cart survives session close | Cart persists across browser close + reopen |

**Restaurant Diners**

| Success Moment | Measurable Target |
|---|---|
| Scans QR, sees full menu | Menu load time < 2 seconds on 3G |
| Selects items with modifiers, places order | Table order placed < 3 minutes from QR scan |
| Receives order status update | Kitchen acknowledgement visible < 30 seconds |
| Pays via M-Pesa at table | STK Push to bill settled < 60 seconds |
| Zero order confusion between tables | 0 cross-table order misfires in Month 1 |

**Bar Customers**

| Success Moment | Measurable Target |
|---|---|
| Opens tab, adds rounds without re-authenticating | Tab round added < 2 taps |
| Happy hour pricing auto-applied | Price change visible on menu at scheduled time ±1 minute |
| Tab settled via M-Pesa | Full tab payment flow < 90 seconds |

**Store / Venue Managers**

| Success Moment | Measurable Target |
|---|---|
| Product or menu item listed | Listed and live < 5 minutes |
| Incoming order actioned | Order acknowledged < 2 hours (retail), < 5 minutes (F&B) |
| Stock / menu availability updated | Inventory change reflected on storefront < 30 seconds |
| Low-stock alert received | Supplier notification sent < 5 minutes of threshold breach |

**Platform Operator (KAFURAHA)**

| Success Moment | Measurable Target |
|---|---|
| Full platform visibility | Single dashboard: all stores, all tenants, all health |
| New tenant onboarded | Tenant live from signup < 24 hours (MVP), < 4 hours (Month 6) |
| Investor demo executed | 3rd tenant onboarded live during demo without code changes |
| Zero cross-tenant data leaks | 0 cross-tenant data incidents in first 90 days |

---

### Business Success

**90-Day (Launch Gate)**

| Metric | Target |
|---|---|
| Live tenants | 2 retail stores + 1 F&B tenant |
| Orders / transactions processed | 50+ across all tenants |
| Critical bugs at go-live | 0 |
| Existing VPS service disruptions | 0 during deployment |
| Investor demo | Passed — 3rd tenant onboarded live |

**6-Month (Growth Gate)**

| Metric | Target |
|---|---|
| Active tenants | 2 own stores + 1+ external merchant |
| Combined monthly online revenue | Exceeds equivalent physical walk-in revenue |
| Customer return rate | >40% repeat purchases (retail) |
| MRR from SaaS subscriptions | First paying external merchant live |
| Celery async job delivery rate | 99%+ on order emails and alerts |
| Automated backups | Confirmed operational daily |

**12-Month (Scale Gate)**

| Metric | Target |
|---|---|
| Active tenants | 5+ across retail + F&B verticals |
| MRR | $500+ from merchant subscriptions |
| Platform cost per tenant | <$15/month infra cost |
| API uptime | 99.9% |
| Avg API response time | <150ms |
| Tenant onboarding time | <4 hours self-service |
| AI engine | First recommendation feature live |

**Investor-Facing Metrics**

| Signal | Target |
|---|---|
| TAM demonstration | Platform powers N stores + F&B venues on single VPS |
| Unit economics | Cost-per-tenant vs revenue-per-tenant tracked in real time |
| Merchant retention | Churn rate <5% monthly |
| Scalability proof | Load test: 10x tenant capacity on same VPS |
| GMV growth | Month-over-month GMV growth across all tenants tracked |

---

### Technical Success

| Requirement | Target |
|---|---|
| API response time (p95) | <300ms at MVP, <150ms at Month 12 |
| API uptime | 99.5% at MVP, 99.9% at Month 12 |
| Tenant isolation | Zero cross-tenant data access — enforced at queryset + permission layer |
| M-Pesa payment success rate | >98% STK Push delivery on valid numbers |
| Celery task delivery | >99% — dead-letter queue + retry required |
| Cart persistence | Cart survives session expiry — Redis-backed, 30-day TTL |
| QR dine-in menu load | <2 seconds on 3G mobile |
| Mobile checkout completion | Full flow operable on 3G, 320px viewport minimum |
| Security | OWASP Top 10 addressed, cross-tenant access blocked, pen-test checklist passed |
| VPS deployment | Zero conflicts with existing services — pre-flight audit required |
| Worker health | Celery worker status exposed on `/health/` — alerting on queue depth |

---

### Measurable Outcomes

| Outcome | Signal | Deadline |
|---|---|---|
| Both retail stores live | First real customer order processed | Day 90 |
| F&B tenant live | First dine-in table order via QR + M-Pesa | Day 90 |
| Analytics providing value | Operator checking dashboard for business decisions | Week 8 |
| Supplier alert working | Low-stock email auto-triggered without manual intervention | Week 8 |
| Platform investor-ready | Live demo: 3rd tenant onboarded without code changes | Day 90 |
| SaaS monetization path | First external merchant paying subscription | Month 6 |
| AI first feature live | Product/menu recommendations visible on storefront | Month 12 |

---

## Product Scope

### MVP — Minimum Viable Product (90 Days)

**Retail Module**
- Multi-tenant store engine (domain routing, full tenant isolation)
- Product catalog: categories, attributes, variants, inventory, media
- Cart (Redis-backed, persistent, guest + authenticated)
- Order lifecycle: created → confirmed → fulfilled → completed
- M-Pesa STK Push + card payment scaffold
- Customer accounts + guest checkout
- Email order confirmation (Celery async)
- Low-stock alerts + supplier notification system
- Store-scoped admin dashboard (products, orders, inventory)
- Platform admin dashboard (all tenants, health, analytics overview)
- Basic analytics: revenue, orders, top products, AOV

**Restaurant Module**
- Restaurant tenant type with F&B feature activation
- Menu management: sections, items, modifiers, modifier groups (min/max rules)
- Order types: dine-in (QR per table), takeaway, delivery
- QR code generation per table — encodes store + table context
- Table session management: open, add rounds, request bill
- Kitchen order view: real-time order list per table, filterable by status
- M-Pesa bill payment at table (STK Push)
- Restaurant analytics: peak hours, table turn rate, menu item performance

**Bar Module**
- Bar tenant sub-type (extends F&B module)
- Open tab management per customer/table
- Round ordering on existing open tab
- Age-restricted item flagging — enforced at order creation
- Happy hour pricing: time-based price rules per menu item (scheduled)
- Tab settlement via M-Pesa

**Platform Infrastructure**
- Docker Compose full stack (API, Redis, Celery, Celery Beat, storefronts)
- Nginx reverse proxy with per-tenant domain config
- VPS zero-conflict deployment (pre-flight port + service audit)
- SaaS scaffold: StoreSubscription, Plan model, usage limits, feature flags
- AI engine placeholder (extension stubs only — no logic at MVP)
- JWT auth, RBAC, rate limiting, CORS, structured logging, healthchecks
- Automated daily backups

---

### Growth Features (Month 4–6)

- Live SaaS billing (Stripe) for external merchants
- Merchant self-service onboarding portal (no SSH required)
- Advanced analytics: funnel, cohorts, LTV curves, peak hour heatmaps
- Multi-currency per store
- Delivery zone management with fee calculation
- Supplier portal (self-service restock confirmations)
- Table reservations with confirmation flow (restaurant)
- Loyalty points / store credit system (retail)
- AI recommendation engine — Phase 1 (collaborative filtering)
- Automated weekly/monthly merchant performance email reports

---

### Vision (Month 7–12 and Beyond)

- AI dynamic pricing suggestions (demand-based, velocity-based)
- AI inventory / ingredient forecasting (predict stock-outs, suggest reorder)
- AI customer segmentation (high-value, at-risk, discount-sensitive)
- POS integration (physical till sync for retail + F&B)
- Marketplace mode (multi-vendor per tenant)
- React Native mobile app (shared API)
- Horizontal scaling (managed Postgres + Redis cluster)
- White-label option for agencies
- 50+ tenants on distributed infrastructure
- Expansion beyond Kenya to other African markets

---

## User Journeys

### Journey 1 — Daniel, 26 · Tech Store Shopper · Discovery to Purchase

*Daniel runs a small IT repair shop in Nairobi's CBD. He needs a replacement charging board for a customer's laptop. A colleague shares a link to the tech store on WhatsApp at 2pm on a Tuesday.*

**Opening Scene:** Daniel taps the link from WhatsApp on his phone — Chrome on Android, 4G. He lands on `techstore.joat.com`. The page loads in under 2 seconds. He sees a clean storefront: featured products, a search bar, category tiles. He types "charging board" into search.

**Rising Action:** Results appear in under a second — 4 products. He filters by price (under KES 2,000). Two results remain. He taps the first: a product detail page with images, a spec list (voltage, compatibility), stock status ("In Stock — 3 left"), and a clear Add to Cart button. He confirms compatibility in 30 seconds.

**Climax:** He taps Add to Cart. Cart drawer slides open. He taps Checkout. Name, phone, pickup address filled in under 90 seconds — no account required. He selects M-Pesa. STK Push arrives on his phone within 8 seconds. He approves with his PIN.

**Resolution:** Order confirmed screen. SMS confirmation arrives. Email with order number and collection details lands in under 60 seconds. Total time from link tap to confirmed order: 4 minutes 20 seconds.

*Requirements: fast search, price filtering, spec display, stock status, guest checkout, M-Pesa STK Push, async order confirmation email, cart drawer UX.*

---

### Journey 2 — Amara, 28 · Fashion Store Shopper · Browse to Checkout (Mobile + Edge Case)

*Amara is a teacher in Westlands. She discovers the fashion store via an Instagram reel. She clicks the link in bio at 9pm on her bed, WiFi, iPhone Safari. She's been burned by wrong sizes before.*

**Opening Scene:** She lands on `fashionstore.joat.com`. Visual-first homepage — full-bleed collection hero, editorial photography. She scrolls. She taps a dress.

**Rising Action:** Product detail page — multiple images, size guide link (opens modal, no navigation away). She selects Size 10. Real-time stock count: "2 left." She selects Colour: Dusty Rose. Stock updates: "1 left." She adds to cart. Her daughter calls — she puts the phone down for 20 minutes.

**Edge Case:** She reopens Safari. Cart is still there — item, size, and colour intact. Redis-backed persistence saved her session.

**Climax:** She proceeds to checkout. One-tap Google Sign-In. Delivery address auto-populated. Home Delivery selected — KES 250 fee shown immediately. M-Pesa STK Push approved in 12 seconds.

**Resolution:** Confirmation email arrives with dress image, size, colour, and delivery window. Two days later: order-shipped email notification.

*Requirements: variant stock per combination, cart persistence (Redis, 30-day TTL), size guide modal, delivery fee calculation, Google Sign-In, shipping status notifications.*

---

### Journey 3 — Brian, 32 · Restaurant Diner · QR Dine-In at Lunch

*Brian and two colleagues walk into a restaurant for lunch. Tables have QR code stickers. No paper menus.*

**Opening Scene:** Brian scans the QR with his iPhone camera — no app download. Browser opens directly to `restaurant.joat.com/table/7`. Branded menu loads instantly. Sections: Starters, Mains, Grills, Beverages, Desserts. Breakfast items are hidden — lunch service only.

**Rising Action:** He taps Grilled Chicken Platter. Modifier modal: *"Choose your side (required): Fries / Rice / Salad"* and *"Add extras (optional): Sauce / Vegetables / Avocado."* He selects Rice + Avocado. His colleagues order from their own phones on the same table session.

**Climax:** Three orders placed. Kitchen receives consolidated ticket: *"Table 7 — 3 orders, 1:07pm."* Kitchen display shows each item with table context. Chef acknowledges — status on Brian's phone updates to "In the Kitchen." Food arrives 18 minutes later. Brian requests the bill — all three orders consolidated, split-pay available.

**Resolution:** Each person pays their share via M-Pesa STK Push. Table status updates to Available in admin dashboard. Zero paper, zero miscommunication.

*Requirements: QR per-table URL routing, multi-user table session, modifier groups (required/optional, min/max), kitchen order view, order status updates, consolidated bill with split-pay, table status management, time-based menu scheduling.*

---

### Journey 4 — Zara, 24 · Bar Customer · Friday Night Tab

*Zara and four friends arrive at a bar tenant on Friday at 8pm. Happy hour until 9pm. QR codes on every table.*

**Opening Scene:** Zara scans the QR. Menu loads — cocktails, beers, spirits, snacks. Happy Hour tags visible — cocktails KES 550 instead of KES 800. Countdown timer shows 57 minutes remaining.

**Rising Action:** She opens a tab for the table. First round: 4 cocktails, 1 mocktail. Bar order queue updates instantly. Round 2 at 8:45pm — happy hour pricing still applies. Round 3 at 9:01pm — prices automatically revert to standard rate. Zara sees the change and orders anyway.

**Climax:** 11pm — Close Tab. Full summary: all rounds, all items, KES 6,200 total. Split 5 ways: KES 1,240 each. All five pay via M-Pesa STK Push from their own phones. All 5 payments confirmed in under 3 minutes.

**Resolution:** Tab closed. Table Available. Bar analytics logged: 3 hours occupancy, 3 rounds, KES 6,200 GMV, 5 M-Pesa transactions, 1 happy-hour-to-standard transition event.

*Requirements: tab creation + open session, round ordering without re-auth, happy hour time-based pricing with live cutoff update, split-pay on tab, bar analytics (occupancy, GMV, rounds), age-restricted item enforcement.*

---

### Journey 5 — Wanjiru · Store Manager · Monday Morning Operations

*Wanjiru manages the fashion store for KAFURAHA. Three tasks: list a new product, action weekend orders, update stock from a physical sale.*

**Opening Scene:** She logs in — store admin dashboard, her store only. No other stores visible. Today's summary: 7 new orders, 2 pending fulfilment, 1 low-stock alert.

**Product Listing:** Add Product → fills name, description, uploads 4 images (drag-and-drop), sets category, adds variants (Size 8/10/12/14 × Colour Black/White/Red), sets stock per variant, sets price. Publishes. Product live on storefront in < 30 seconds.

**Order Actioning:** Order #1042 — paid, marked Fulfilled. Order #1043 — M-Pesa STK Push not completed (pending). Flagged for follow-up. Automated reminder email dispatched to customer via Celery.

**Stock Update:** Physical sale occurred Saturday — Size 12 Black, 1 unit. She updates inventory in dashboard. Storefront reflects the change immediately.

**Resolution:** Low-stock alert for Size 10 White — supplier notification email already auto-sent. Alert logged with supplier name and send timestamp.

*Requirements: store-scoped admin (no cross-tenant visibility), product + variant creation with media, order management + status transitions, M-Pesa payment status tracking, inventory update with real-time storefront sync, supplier alert log.*

---

### Journey 6 — KAFURAHA · Platform Operator · Investor Demo Day (Day 88)

*Two stores live, processing orders. A potential investor is in the office. 30 minutes to prove the platform thesis.*

**Opening Scene:** Platform Admin dashboard — all active tenants visible: Tech Store, Fashion Store, Mama Njeri's Kitchen (restaurant). All green health status. Combined GMV this month: KES 48,000. 47 orders across all tenants.

**The Demo:** She shows platform analytics: GMV trend, tenant health, MRR (KES 0 — own stores, honest). Then: *"Watch me onboard a fourth tenant."* New Tenant form: business name, domain (salon.joat.com), type (retail), plan (Basic). Store Owner account created. Tenant live — blank storefront on its own domain. One product added. Orders immediately possible. Time elapsed: 9 minutes.

**Climax:** Investor asks: *"Could this be a restaurant instead?"* She changes tenant type to `restaurant` via config. Feature set updates — menu management, table QR, kitchen view now active. No code change. No deployment. 2 minutes.

**Resolution:** 11 minutes total. Four tenants, three verticals. Investor asks for unit economics. Platform analytics shows infra cost per tenant, GMV per tenant, projected MRR at 20 tenants. Meeting extends to 2 hours.

*Requirements: platform admin multi-tenant overview, tenant creation via UI (no SSH), tenant type switching via config, per-tenant analytics, unit economics tracking, live demo without code changes.*

---

### Journey 7 — Kamau · Future Merchant · Self-Service Onboarding (Month 6)

*Kamau runs a sneaker resale business. Heard about joat_stores from a friend. Visits the landing page on his phone.*

**Opening Scene:** Pricing page — Basic plan, KES 1,500/month. He clicks Start Free Trial. Creates account with email + phone. SMS verification code received.

**Rising Action:** 4-step onboarding: business name → domain (kamausneakers.joat.com auto-suggested) → tenant type (retail) → plan selection (Basic trial, no payment until Day 14). Dashboard loads with onboarding checklist: Add first product / Set up M-Pesa / Customize theme.

**Climax:** All three checklist items completed in 25 minutes. Store live at kamausneakers.joat.com. He shares the link on Instagram. First order arrives 3 hours later.

**Resolution:** Day 14 — M-Pesa subscription auto-renews. Month 2 — upgrades to Growth plan. joat_stores: +KES 3,000 MRR. Kamau's monthly online revenue: KES 85,000. He refers three other resellers.

*Requirements: self-service onboarding portal, domain auto-suggestion, trial period management, subscription billing via M-Pesa, in-app onboarding checklist, store theme customization.*

---

### Journey Requirements Summary

| Journey | Key Capabilities Revealed |
|---|---|
| Daniel — Tech Shopper | Search, filtering, spec display, guest checkout, M-Pesa, async email |
| Amara — Fashion Shopper | Variant stock per combination, cart persistence, size guide, delivery fee, Google Sign-In |
| Brian — Restaurant Diner | QR routing, multi-user table session, modifier groups, kitchen view, split-pay, time-based menus |
| Zara — Bar Customer | Tab management, round ordering, happy hour pricing, split-pay, bar analytics |
| Wanjiru — Store Manager | Store-scoped admin, product + variant creation, order actioning, inventory sync, supplier alerts |
| KAFURAHA — Platform Operator | Multi-tenant dashboard, tenant creation via UI, tenant type config, unit economics, live demo |
| Kamau — Future Merchant | Self-service onboarding, domain management, trial billing, onboarding checklist, M-Pesa subscription |

---

## Extended Functional Requirements (FR71–FR101)

*Added post-elicitation based on confirmed product owner requirements: multi-country operations (Jamaica + Kenya), pre-arrival restaurant flow, contracting vertical, loyalty, and AI.*

### Multi-Country + Multi-Provider Payments
- **FR71:** `Store` model shall have `country` (ISO 3166-1 alpha-2), `currency` (ISO 4217), `timezone`, and `payment_methods[]` fields; these are set at provisioning and configurable by store owner
- **FR72:** Payment service shall route to the correct provider based on `store.payment_methods` — `mpesa` → Daraja, `card` → Stripe or Flutterwave, `cash` → manual staff confirmation
- **FR73:** Card payment via Stripe and Flutterwave shall be live (not a 501 scaffold) for stores with `card` in `payment_methods`; Jamaican stores default to card
- **FR91:** Stripe integration shall have E2E sandbox tests with JMD-denominated amounts before Epic 2 acceptance; currency handling must be verified in CI

### Restaurant Full-Service
- **FR74:** Public menu URL `/{store_slug}/menu/` shall be accessible without QR scan or table session — shareable on WhatsApp, Instagram, anywhere
- **FR75:** `PendingOrder` model shall store pre-arrival item selections linked to a customer phone number and 6-digit PIN; PIN delivered via SMS/WhatsApp
- **FR76:** Customer shall be able to pre-order and pay in full before arriving; kitchen ticket shall fire only when waiter confirms seating on the waiter screen
- **FR77:** `Reservation` model shall support time slot booking with party size; statuses: PENDING → CONFIRMED → SEATED → NO_SHOW; confirmation sent via WhatsApp/SMS
- **FR78:** `TableSession.assigned_waiter` shall be a FK to staff; waiter name shall appear on kitchen ticket; waiter reassignment shall update the field without migrating order ownership
- **FR92:** Waiter-facing order management screen shall allow pulling up a `PendingOrder` by phone number or PIN and one-tap converting it to a `DineInOrder` with table assignment
- **FR94:** Public menu page shall pass Lighthouse CI performance gate: < 1.5s First Contentful Paint on simulated 3G (1.6 Mbps)
- **FR101:** `PendingOrder.expires_at` = `created_at + 24 hours`; Celery Beat hourly purge task deletes unconverted expired orders

### Contracting Vertical
- **FR79:** `contracting` tenant type shall activate service catalogue, booking calendar, quote flow, job tracking, and invoice generation
- **FR80:** `Service` model shall have: name, description, base_price, duration_estimate, category, and time slot availability calendar
- **FR81:** `QuoteRequest → Quote → Job` workflow shall require explicit customer acceptance before job status advances; customer receives quote via WhatsApp/SMS link
- **FR82:** `JobMilestone` model shall support completion photo upload; milestone status shall update to COMPLETED when photo is attached and staff confirms
- **FR83:** `Invoice` shall be auto-generated from completed `Job` with store branding; settled via `initiate_payment()` (M-Pesa or card)
- **FR97:** `Invoice` shall export as a branded PDF (store logo, line items, totals, validity, payment reference); PDF link shall be WhatsApp-shareable

### Customer Loyalty + Engagement
- **FR84:** `LoyaltyAccount` per customer per store shall track points balance and full transaction history; points awarded at configurable rate per order value
- **FR85:** `StampCard` per customer shall have a configurable completion threshold; reward shall trigger automatically when threshold is reached
- **FR86:** WhatsApp notification dispatch shall use Celery `engagement.notifications` queue; notifications sent for: order confirmed, reservation confirmed, job update, loyalty reward earned
- **FR87:** Unified customer account shall allow a single login to view all orders, reservations, and jobs across all stores owned by the same platform operator
- **FR93:** WhatsApp ordering bridge (Phase 2): bot shall create a `PendingOrder` from customer message and return a 6-digit PIN for waiter retrieval; model ready at MVP, bot layer deferred
- **FR98:** "Powered by joat_stores" footer shall appear on all storefronts on Basic plan; togglable off on Growth/Pro; footer links to merchant signup (viral acquisition loop)

### AI + Personalization
- **FR88:** `RecommendationEngine` shall use `AIEvent` history to generate personalised menu item suggestions per customer; gated on `plan.features.has_ai`
- **FR89:** Peak hour predictions derived from `HourlyOrderSummary` shall appear in merchant analytics as staffing suggestions; available on Growth+ plans
- **FR90:** NLP menu search `GET /api/v1/restaurant/menu/search/?q=` shall accept natural language queries and return ranked `MenuItem` results; gated on `plan.features.has_ai`

### Platform + Analytics
- **FR95:** `DailyRevenueSummary` shall store both `amount_local` (store currency) and `amount_usd` (USD-normalised using daily exchange rate); platform GMV aggregation uses `amount_usd` only
- **FR96:** Store admin PWA shall function offline for inventory count updates; changes queued and synced automatically when connection resumes
- **FR99:** Data export shall be plan-gated: Basic gets summary CSV (30-day window), Growth gets full CSV (90-day), Pro/Enterprise gets raw JSON export (unlimited)
- **FR100:** Merchant daily view shall show three numbers on one screen with zero navigation: today's order count, today's revenue, and count of pending actions (unconfirmed orders, low-stock alerts, unread messages)

---

## Domain-Specific Requirements

### Compliance & Regulatory

**Kenya Data Protection Act 2019 (DPA)**
- All personal data (name, phone, email, address, purchase history) requires lawful basis — consent at account creation, legitimate interest for order fulfilment
- Data subjects have right to access, correction, and deletion — implementable by platform admin
- Cross-border data transfers restricted — VPS must be Kenya-hosted or EAC-region hosted
- Data breach notification required within 72 hours to the ODPC
- Privacy policy required — linked from all storefronts and checkout flows

**M-Pesa / Safaricom Daraja API Compliance**
- Daraja API registration required — business must be a registered Kenyan entity with Safaricom
- Sandbox testing mandatory before production access
- STK Push requires explicit user consent flow — no silent debit
- Webhook endpoints must be HTTPS with valid SSL certificate
- API credentials (Consumer Key, Consumer Secret) stored encrypted — never in source code
- Transaction logs retained minimum 12 months for reconciliation and dispute resolution
- Reversal API must be implemented for failed fulfilment scenarios

**Age-Restricted Items (Bar Operations)**
- Alcoholic beverages are age-restricted in Kenya (18+)
- Items flagged `age_restricted=True` must display a compliance warning at menu view
- Order creation for age-restricted items requires age acknowledgement (checkbox, logged per order)
- In-person verification at service is the operator's responsibility; platform provides digital acknowledgement only

**Food Safety (Restaurant/Bar)**
- Allergen information must be displayable per menu item (peanuts, gluten, dairy, etc.)
- `contains_allergens` flag required on menu item model
- No mandatory regulatory reporting at MVP — allergen display is best-practice

---

### Technical Constraints

**Payment Security**
- joat_stores does NOT store raw card numbers — card payments via tokenised provider (Stripe/Flutterwave); platform stores payment reference IDs and status only
- M-Pesa phone numbers masked in logs (last 4 digits only)
- All payment webhooks verified via signature/token before processing
- Payment endpoints rate-limited independently from general API throttle

**Data Privacy — Technical Controls**
- Customer PII encrypted at rest in Postgres
- API responses must never expose PII across tenant boundaries
- Deletion requests: soft-delete + anonymise PII fields (name → "Deleted User", email → hash, phone → null)
- Audit log of all admin access to customer PII

**Multi-Tenant Security**
- All database queries MUST include `store_id` filter — enforced at queryset level
- Middleware rejects requests with missing or mismatched store context
- Cross-tenant permission checks: `object.store_id == request.store.id` on every object access
- JWT tokens scoped to store context — `store_id` claim in token payload

**Low-Bandwidth / Mobile-First (Kenya Market)**
- All API responses paginated — no unbounded list endpoints
- Image uploads: server-side compression to WebP, max 800KB per image
- Storefront target: < 200KB total page weight on first load
- QR dine-in menu: progressive loading — sections first, items lazy-loaded on expand
- All interactive flows must complete on 3G (1–2 Mbps)
- No autoplay video on any storefront page

---

### Integration Requirements

| Integration | Purpose | Requirement |
|---|---|---|
| Safaricom Daraja API | M-Pesa STK Push, C2B, B2C, reversal | HTTPS webhook, encrypted credentials, sandbox-first |
| Email provider (SendGrid / AWS SES) | Order confirmations, alerts, reports | Celery async, retry on failure, bounce handling |
| Google Sign-In | Customer OAuth | OAuth2 PKCE flow, no password stored for Google users |
| n8n (optional) | Supplier automation webhooks | Webhook endpoint on internal network only |
| Stripe (Phase 2) | SaaS merchant billing | Webhook signature verification, idempotency keys |

---

### Risk Mitigations

| Risk | Domain Driver | Mitigation |
|---|---|---|
| M-Pesa STK Push not received | Network/carrier timeout | Auto-retry after 30s, manual re-trigger in checkout, 10-minute payment window before order expires |
| Cross-tenant data leak | Multi-tenancy | Queryset isolation at model level + integration test suite covering cross-tenant access attempts |
| Customer PII exposed in logs | DPA 2019 | Structured logging with PII masking — phone/email replaced with hashed references in all log output |
| Age-restricted order without acknowledgement | Bar compliance | Order creation API validates `age_acknowledged=True` when any `age_restricted=True` item present |
| ODPC breach notification missed | DPA 2019 | Incident response runbook — breach alert triggers 72-hour notification window |
| Low-bandwidth checkout abandonment | Kenya market | Max 3-step checkout, no full-page reloads, form state preserved on network drop |
| Daraja credential exposure | Payment security | Credentials in environment variables only, never committed to source, rotated quarterly |
| Payment reconciliation failure | M-Pesa reliability | 12-month transaction log, daily Celery beat reconciliation job flags mismatched statuses |

---

## Innovation & Novel Patterns

### Detected Innovation Areas

**1. M-Pesa as Primary UX — Not a Bolt-On**

Every existing e-commerce platform treats M-Pesa as an integration afterthought — a plugin, a webhook, a third-party module. joat_stores inverts this: the entire payment UX is designed around STK Push as the *default and natural* experience. Checkout, restaurant bill settlement, bar tab closure, and SaaS subscription renewal all originate from the same M-Pesa-first design pattern. This is architecturally novel for headless commerce — no existing headless framework (Medusa, Saleor, Vendure) offers this as a first-class design primitive.

**2. Multi-Vertical Tenant Type Architecture**

A single infrastructure platform where tenant type (`retail` / `restaurant` / `bar`) is a *configuration* that activates the appropriate feature module — not a separate codebase, not a separate product. A merchant can switch verticals without a new deployment. The platform operator can onboard a bar as easily as a clothing store. This creates a "commerce operating system" rather than a "commerce application" — verticals are parameters, not products.

**3. Analytics as the Primary Value Proposition**

In Western commerce platforms, analytics is added after the store is built. In joat_stores, analytics is the core differentiator — the reason an African SME chooses this over WhatsApp. For merchants with zero current data visibility, the first time they see their revenue trend, top-selling product, and cart abandonment rate is transformative. Analytics drives merchant acquisition and retention; the storefront is the delivery mechanism.

**4. QR Dine-In + M-Pesa Table Settlement**

No existing restaurant technology in Kenya combines QR-based multi-user table ordering, kitchen display routing, and M-Pesa tab settlement in a single SME-accessible platform without POS hardware. The combination of QR ordering UX (from high-tech restaurant markets) with M-Pesa settlement (local payment rail) — designed for 3G mobile-first context — is genuinely novel for the East African F&B market.

**5. AI-Augmented Commerce for African SMEs**

Shopify Audiences, Klaviyo, and Dynamic Yield exist for Western merchants. Nothing equivalent exists for Kenyan SMEs at accessible pricing. joat_stores scaffolds AI intelligence — recommendations, dynamic pricing, inventory forecasting, customer segmentation — as a native infrastructure layer available to any Growth/Pro tenant. Democratising AI commerce intelligence for emerging markets at SaaS pricing.

---

### Market Context & Competitive Landscape

| Competitor | What They Do | What They Miss |
|---|---|---|
| Shopify | Full commerce platform, global | No M-Pesa native, $79+/store/month, no multi-vertical, no African SME pricing |
| WooCommerce | WordPress commerce plugin | No multi-tenancy, no headless, M-Pesa plugins unreliable |
| Saleor / Medusa | Open-source headless commerce | No M-Pesa, no F&B vertical, steep learning curve |
| iKhokha / Pesapal | African payment solutions | Payment-only, no commerce engine, no storefront, no analytics |
| Lightspeed / Square | Restaurant POS + commerce | Hardware-dependent, USD pricing, no M-Pesa, not in Kenya |
| Instagram / WhatsApp | Informal selling channel | No checkout, no inventory, no analytics, no ownership |

**The gap:** Multi-vertical, M-Pesa-native, analytics-first, self-hosted commerce infrastructure at African-market pricing. No current product fills all four attributes for the Kenyan SME market.

---

### Validation Approach

| Innovation | Validation Method | Success Signal |
|---|---|---|
| M-Pesa-first UX | Measure checkout completion rate vs card | M-Pesa completion rate > card rate for Kenyan users |
| Multi-vertical tenant switching | Investor demo: switch tenant type live, no code | Demo < 5 minutes, zero errors |
| Analytics as retention driver | Track dashboard engagement — do merchants log in for analytics? | >60% check dashboard weekly within 30 days |
| QR dine-in + M-Pesa | Restaurant pilot: time from QR scan to M-Pesa confirmation | End-to-end < 4 minutes, zero order misfires |
| AI recommendations | Click-through rate on "Customers also bought" | >3% CTR (industry benchmark: 2–4%) |

---

### Risk Mitigation

| Innovation Risk | Likelihood | Mitigation |
|---|---|---|
| Daraja API downtime | Medium | Graceful fallback to card; retry queue for failed STK Push; status monitoring |
| Tenant type switching creates data conflicts | Low | Tenant type locked after first order; migration path documented |
| Analytics adoption low | Medium | Weekly automated email digest with key metrics; WhatsApp summary (Phase 2) |
| QR dine-in UX unfamiliar | Low | Printed "How to order" card at each table; staff training guide |
| AI cold-start problem (no order history) | High | Cold-start fallback: "Popular in your category" using anonymised platform aggregates |

---

## SaaS B2B Platform — Specific Requirements

### Project-Type Overview

joat_stores is a multi-tenant SaaS B2B platform where the platform operator (KAFURAHA) serves merchant tenants across retail and F&B verticals. Each merchant operates an isolated tenant on shared infrastructure. The platform monetises through subscription tiers with usage-based feature limits. The architecture supports unlimited tenant growth without infrastructure modification.

---

### Tenant Model

**Tenancy Architecture:** Shared database, shared schema, tenant isolation via `store_id` foreign key on all business models.

**Tenant Resolution:** Domain-based routing via Nginx + Django middleware. `X-Store-ID` header as fallback for API clients. Store resolved on every request.

**Tenant Lifecycle:**

| State | Trigger | System Behaviour |
|---|---|---|
| `pending` | Signup initiated | Tenant record created, storefront inactive |
| `active` | Onboarding complete + first product added | Storefront live, domain resolving |
| `suspended` | Payment failure / policy violation | Storefront returns 503, admin access retained |
| `cancelled` | Merchant cancels | Data retained 90 days, then anonymised per DPA |

**Tenant Type Configuration:** `tenant_type` field on Store model activates feature modules. Values: `retail`, `restaurant`, `bar`. Locked after first order is placed.

**Tenant Isolation Enforcement Points:**
1. Middleware — resolves `request.store`; rejects unknown stores with 404
2. Base queryset — `TenantQuerySet.for_store(store)` filters all queries
3. Serializer — `store` field auto-populated from request context
4. Permission class — `IsStoreScoped` verifies `obj.store == request.store`
5. Admin — `StoreAdmin` base class limits queryset for Store Owner/Manager roles

---

### RBAC Matrix

| Role | Scope | Description |
|---|---|---|
| `platform_admin` | All stores | Full platform access — tenant management, all data, platform analytics, billing |
| `store_owner` | Own store | Full store access — products, orders, staff, settings, analytics |
| `store_manager` | Own store | Operational access — products, orders, inventory; no billing/staff management |
| `customer` | Own profile + orders | Account, order history, cart — within a specific store only |

**Permission Matrix:**

| Action | Platform Admin | Store Owner | Store Manager | Customer |
|---|---|---|---|---|
| Create / delete tenant | ✅ | ❌ | ❌ | ❌ |
| View all tenants | ✅ | ❌ | ❌ | ❌ |
| Manage store settings | ✅ | ✅ | ❌ | ❌ |
| Manage staff accounts | ✅ | ✅ | ❌ | ❌ |
| Add / edit products | ✅ | ✅ | ✅ | ❌ |
| View / action orders | ✅ | ✅ | ✅ | Own only |
| Update inventory | ✅ | ✅ | ✅ | ❌ |
| View store analytics | ✅ | ✅ | ✅ (read) | ❌ |
| View platform analytics | ✅ | ❌ | ❌ | ❌ |
| Manage subscription / billing | ✅ | ✅ | ❌ | ❌ |
| Place orders | ❌ | ❌ | ❌ | ✅ |

**Feature Access per Plan:**

| Feature | Basic | Growth | Pro |
|---|---|---|---|
| Products | 50 | 500 | Unlimited |
| Staff accounts | 1 | 5 | Unlimited |
| Analytics | Basic | Advanced | Full + AI |
| AI recommendations | ❌ | ❌ | ✅ |
| Custom domain | ❌ | ✅ | ✅ |
| API rate limit | 100 req/min | 500 req/min | 2000 req/min |

---

### Subscription Tiers

**Plan Model fields:** `name`, `product_limit`, `staff_limit`, `analytics_tier`, `ai_access`, `custom_domain`, `api_rate_limit`, `monthly_price_kes`, `monthly_price_usd`

**StoreSubscription states:** `trial` → `active` → `past_due` → `suspended` → `cancelled`

**Billing Flow (MVP — M-Pesa):**
- 14-day trial, no payment required
- Celery beat triggers STK Push renewal 3 days before period end
- 7-day grace period before suspension on non-payment

**Billing Flow (Phase 2 — Stripe):**
- Credit card via Stripe payment methods
- Stripe webhooks update subscription status with idempotency keys

**Usage Limit Enforcement:**
- Product limit: checked on create — 403 with upgrade prompt at limit
- Staff limit: checked on invite
- API rate limit: DRF throttle reads plan limit from `request.store.subscription`

---

### Integration List

| Integration | Type | Priority | Auth | Notes |
|---|---|---|---|---|
| Safaricom Daraja API | Payment | MVP | OAuth2 | STK Push, C2B, B2C, reversal — sandbox required |
| SendGrid / AWS SES | Email | MVP | API Key | Order confirmations, alerts — Celery async |
| Google Sign-In | Auth | MVP | OAuth2 PKCE | Customer accounts — no password stored |
| n8n | Automation | MVP optional | Webhook | Supplier automation — internal network only |
| Stripe | Billing | Phase 2 | API Key + Webhooks | Merchant SaaS billing |
| Flutterwave | Payment alt | Phase 2 | API Key | Card backup — scaffold ready |
| WhatsApp Business API | Notifications | Phase 2 | API Key | Order status + merchant analytics digest |

---

### Technical Architecture Considerations

**API Design:**
- Versioned from day one: `/api/v1/` prefix
- Store context via middleware — all endpoints auto-scoped; no `store_id` in URL paths
- Response envelope: `{data, meta, errors}` on all endpoints
- Cursor-based pagination on all list endpoints
- OpenAPI schema via drf-spectacular

**Async Architecture (Celery):**
- Task categories: `order.notifications`, `inventory.alerts`, `billing.reminders`, `analytics.reports`, `payments.reconciliation`
- Retry policy: exponential backoff, max 5 retries, dead-letter queue after max
- Beat: daily reconciliation, weekly merchant digest, renewal reminder 3 days prior
- Worker health: `/health/workers/` — queue depth + last heartbeat per worker

**Caching Strategy (Redis):**
- Cart: per-store + per-user key, 30-day TTL
- JWT: 15-minute access token, 7-day refresh with rotation
- Storefront catalog: per-store cache, 5-minute TTL, invalidated on product/inventory update
- Rate limit counters: sliding window per store + per IP

**Horizontal Scalability (Future-Ready):**
- All state externalised to Postgres + Redis — API containers stateless
- Read replicas: supported via `DATABASE_READ_URL` env var, no code change required
- Separate Celery queues per task category — scale workers independently
- MVP: single VPS sufficient; no refactoring required to scale

---

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach: Revenue + Investor Validation MVP**

This is not a "learning MVP" — it's a **proof-of-revenue MVP**. The 90-day build must deliver real transactions from real customers on real stores. The investor thesis requires a live, functioning platform with measurable GMV and a demonstrated third-tenant onboarding. There is no value in a prototype or staging environment — the MVP is production.

**MVP Philosophy:** *Ship the minimum that processes real money, proves tenant isolation, and demonstrates the platform can onboard a new vertical in under 24 hours.*

**MVP Success Gates (Go / No-Go):**

| Gate | Criteria | Decision |
|---|---|---|
| Technical | API serves 3 isolated tenants (2 retail + 1 F&B) correctly | Proceed to Phase 2 |
| Commerce | End-to-end retail order + M-Pesa on both stores | Proceed to hardening |
| F&B | QR dine-in + M-Pesa table settlement working | Proceed to launch |
| Supplier | Low-stock event auto-triggers supplier email | Proceed to launch |
| Security | Cross-tenant access blocked; pen-test checklist passed | Proceed to launch |
| Business | 50+ transactions, 0 critical bugs | Proceed to SaaS phase |
| Investor | Live demo: 3rd tenant onboarded < 24 hours | Proceed to fundraise |

**Resource Requirements:** Solo developer (KAFURAHA), existing VPS, Daraja sandbox account, email provider, domain names.

---

### MVP Feature Set — Must-Have (Phase 1, 90 Days)

| Feature | Must-Have? | Rationale |
|---|---|---|
| Multi-tenant domain routing | ✅ | Core thesis |
| Per-store query isolation | ✅ | Security — non-negotiable |
| JWT auth + RBAC | ✅ | Protects tenant data |
| Product catalog (retail) | ✅ | Can't sell without products |
| Cart + checkout | ✅ | Can't process orders without it |
| M-Pesa STK Push | ✅ | Primary payment rail |
| Order lifecycle | ✅ | Can't fulfil without it |
| Order confirmation email (Celery) | ✅ | Customer trust for real sales |
| Restaurant tenant type + QR dine-in | ✅ | Validates multi-vertical thesis |
| Kitchen order view | ✅ | Required for F&B operations |
| Basic analytics dashboard | ✅ | Core differentiator |
| Low-stock alerts + supplier emails | ✅ | Live inventory requirement |
| Platform admin dashboard | ✅ | Required for investor demo |
| Docker + Nginx deployment | ✅ | VPS launch requirement |
| SaaS subscription scaffold | ✅ | Architecture for investor story |
| AI engine placeholder | ✅ | Architecture for investor story |

**Pulled into MVP (previously deferred — confirmed by product owner):**

| Feature | Previously | Now | Reason |
|---|---|---|---|
| Multi-currency (KES + JMD + USD) | Phase 2 | ✅ MVP | Jamaican restaurant is a live merchant |
| Card payments (Stripe + Flutterwave) | Phase 2 scaffold | ✅ MVP live | Jamaica has no M-Pesa |
| Table reservations | Phase 2 | ✅ MVP | Pre-arrival booking is core to both restaurants |
| WhatsApp notifications | Phase 2 | ✅ MVP | Primary customer communication channel |
| Pre-arrival menu browsing + PendingOrder | Not planned | ✅ MVP | Key differentiator for both restaurant locations |
| Contracting tenant type | Not planned | ✅ Epic 6 | Live contracting business requires it |
| Customer loyalty (points + stamp card) | Not planned | ✅ Epic 10 | Repeat customer strategy confirmed |

**Explicitly Deferred:**

| Feature | Deferred To | Reason |
|---|---|---|
| Live Stripe SaaS billing | Phase 2 | Scaffold sufficient at MVP |
| Merchant self-service onboarding | Phase 2 | Manual admin onboarding acceptable < 5 merchants |
| Advanced analytics (LTV, funnels) | Phase 2 | Basic metrics sufficient for validation |
| Delivery zone management | Phase 2 | Flat fee acceptable at MVP |
| AI recommendations (live) | Phase 3 | Scaffold only at MVP |
| Mobile app | Post-Series A | Mobile browser optimised |
| POS integration | Phase 3 | Online-first at MVP |
| WhatsApp ordering bot (FR93) | Phase 2 | PendingOrder model ready; bot layer deferred |

---

### Phase 2 — Growth (Month 4–6)

**Gate:** 50+ orders, first external merchant inquiry, investor demo passed.

- Live Stripe SaaS billing for external merchants
- Merchant self-service onboarding portal
- Advanced analytics: funnel, cohorts, LTV, peak hour heatmaps
- Delivery zone management with fee calculation
- AI recommendation engine Phase 1 (collaborative filtering)
- Table reservations (restaurant)
- Loyalty points / store credit (retail)
- Multi-currency (KES + USD)
- WhatsApp Business API notifications
- Weekly automated merchant performance digest
- Supplier portal (self-service restock)

---

### Phase 3 — Scale & Expansion (Month 7–12+)

**Gate:** MRR > $500, 5+ active merchant tenants, AI Phase 1 complete.

- AI dynamic pricing + inventory forecasting + customer segmentation
- POS integration (physical till sync)
- Marketplace mode (multi-vendor per tenant)
- React Native mobile app
- Horizontal scaling (managed Postgres + Redis cluster)
- White-label for agencies
- Geographic expansion: Uganda, Tanzania, Rwanda
- 50+ tenants on distributed infrastructure

---

### Risk Mitigation Strategy

**Technical Risks:**

| Risk | Probability | Mitigation |
|---|---|---|
| Daraja API integration complexity | High | Sandbox-first; Week 7 buffer for M-Pesa edge cases |
| VPS port conflicts | Medium | Pre-flight audit script before any `docker compose up` |
| Celery worker silent failure | Medium | Dead-letter queue + health endpoint + Celery Flower from Day 1 |
| Tenant isolation queryset gap | Low | Cross-tenant access test cases in CI pipeline |
| Redis cart data loss on restart | Low | Redis AOF persistence + restart policy in Compose |

**Market Risks:**

| Risk | Probability | Mitigation |
|---|---|---|
| Low QR dine-in adoption | Medium | Pilot with known F&B contact; paper backup always available |
| Merchants prefer WhatsApp over dashboard | High | Weekly email digest (no login required) as Phase 2 delivery channel |
| STK Push friction for older customers | Medium | Card payment scaffold available as fallback |

**Resource Risks (Solo Developer):**

| Risk | Mitigation |
|---|---|
| 90-day timeline slip | Week-by-week gate — if Week 4 missed, restaurant module deferred to Phase 2 |
| Scope creep | Strict deferred list — new requests go to Phase 2 log, not MVP backlog |
| Burnout | Week 12 reserved for hardening only, no new features |
