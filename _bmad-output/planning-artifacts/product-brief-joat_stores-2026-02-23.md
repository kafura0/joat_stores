---
stepsCompleted: [1, 2, 3, 4, 5, 6]
status: COMPLETE
inputDocuments: []
date: 2026-02-23
author: KAFURAHA
---

# Product Brief: joat_stores

<!-- Content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

joat_stores is a self-hosted, multi-tenant headless commerce engine built to power
independent storefront domains from a single, unified backend. Its first two tenants —
a tech store and a clothing store — serve as the live proof-of-concept for a platform
designed to onboard unlimited merchants without per-store SaaS fees, vendor lock-in,
or infrastructure compromise.

Built on Django + DRF with a Next.js storefront layer, joat_stores is architected from
day one as investable commerce infrastructure: tenant-isolated, horizontally scalable,
and SaaS-billing ready.

---

## Core Vision

### Problem Statement

Merchants launching online stores face a painful dilemma: use expensive hosted platforms
(Shopify, WooCommerce) and accept high fees and zero infrastructure ownership, or build
custom systems and face months of engineering overhead with no clear scaling path.
Portfolio operators — those running multiple stores — face this cost multiplied per brand.

### Problem Impact

- Shopify charges $79–$299/month per store, per tenant, forever
- Custom Django/WooCommerce builds have no multi-tenancy, no shared auth, no unified ops
- Merchants lose margin to platform fees before they've even scaled
- Developers rebuilding commerce logic from scratch on every project waste months

### Why Existing Solutions Fall Short

| Platform | Gap |
|----------|-----|
| Shopify | No infrastructure ownership, expensive at scale, closed API |
| WooCommerce | No multi-tenancy, no headless-first design, plugin bloat |
| Saleor/Medusa | Framework lock-in, steep learning curve, over-engineered for small starts |
| Custom builds | No shared infrastructure, duplicated effort per store, no SaaS path |

### Proposed Solution

joat_stores is a platform-first commerce engine:
- Single Django backend powers N independent storefronts via domain-based tenant resolution
- Each storefront is fully isolated at query, auth, and data levels
- Next.js frontends are independently deployable per brand
- Redis + Celery handle async workloads (orders, notifications, inventory sync)
- SaaS billing module scaffolded for future merchant onboarding monetization
- Runs on existing VPS infrastructure with zero conflict to live services

### Key Differentiators

1. **Infrastructure ownership** — no per-store SaaS fees, runs on your metal
2. **True multi-tenancy** — not just separate deployments, but isolated tenants on shared core
3. **Investor-ready architecture** — designed with 90-day roadmap, monetization model,
   and horizontal scaling path from day one
4. **AI-extension ready** — placeholder module for recommendations, pricing, segmentation
5. **Starting with real stores** — tech store + clothing store as live validation,
   not greenfield theory

---

## Target Users

### Primary Users

---

#### Persona 1: The Platform Operator — "KAFURAHA"
**Role:** Platform Admin / Multi-Store Owner
**Context:** Owns and operates two physical retail stores (tech + fashion) with
existing inventory. Technically capable, building for long-term infrastructure
ownership rather than renting from Shopify. Manages both stores directly, may
delegate store-level ops to staff.

**Goals:**
- Get both stores generating online revenue quickly (90-day horizon)
- Maintain full infrastructure ownership and zero per-store SaaS fees
- Build something fundable and scalable — not a one-off website
- Onboard future merchants to monetize the platform

**Pain Points:**
- Hosted platforms (Shopify) are expensive at multi-store scale
- Off-the-shelf solutions don't offer real tenant isolation
- No existing solution that fits both "get online fast" and "investor-ready platform"

**Success Moment:** Both stores processing live orders. A third merchant onboarded
without touching the core engine. Platform pitched to an investor with a live demo.

---

#### Persona 2: The Tech Store Shopper — "Daniel, 26"
**Role:** End Customer — Tech Store
**Context:** Urban male, 18–35, tech-savvy, purchases gadgets, accessories,
electronics. Discovered the store through social media or word of mouth.
Compares prices, reads specs, values fast shipping confirmation.

**Goals:**
- Browse available stock quickly, filter by category/price
- Checkout with minimal friction (guest or saved account)
- Get instant order confirmation and tracking updates

**Pain Points:**
- Can't currently buy online — has to visit physically or call
- No product discovery layer (search, filters, specs)

**Success Moment:** Finds a product in 30 seconds, checks out in under 2 minutes,
receives email confirmation immediately.

---

#### Persona 3: The Fashion Store Shopper — "Amara, 28"
**Role:** End Customer — Clothing Store
**Context:** Female, 18–40, fashion-forward, shops for clothing and accessories.
Discovery-driven behavior — browses collections, responds to visuals. Highly
sensitive to variant availability (size, color). Likely influenced by
Instagram/social channels.

**Goals:**
- Browse collections with rich visual presentation
- Filter by size, color, category without dead ends (out-of-stock UX)
- Save items, return later, complete purchase on mobile

**Pain Points:**
- Can't shop remotely — limited to in-store visits
- No way to check size availability before travelling to store

**Success Moment:** Sees a full-look image, selects size/color, confirms
availability in real-time, completes checkout on mobile in under 3 minutes.

---

### Secondary Users

#### Store Manager / Staff
**Role:** Store-level Admin per tenant
**Context:** Trusted staff member managing day-to-day — adding products, updating
inventory, processing orders, handling customer queries. Does NOT have access to
other stores or platform-level settings.

**Goals:**
- Add/update products with variants, images, pricing quickly
- View and action incoming orders
- Update stock levels after physical sales

---

#### Future Merchant (SaaS Tenant)
**Role:** Prospective store owner onboarded to the platform
**Context:** Small business owner in a comparable market who discovers joat_stores
as a managed commerce infrastructure offering — cheaper than Shopify, more
controlled than WooCommerce, with managed hosting.

**Goals:**
- Launch a storefront without managing infrastructure
- Pay a flat subscription rather than Shopify's % transaction fees
- Get a branded storefront under their own domain

---

### User Journey

#### Daniel (Tech Shopper) — Discovery to Purchase
1. Discovers store via social link → lands on techstore.joat.com
2. Browses category (e.g. "Phones") → filters by price
3. Views product detail (specs, images, stock status)
4. Adds to cart → guest checkout or account login
5. Pays → receives order confirmation email (Celery async)
6. Order appears in store admin dashboard for fulfillment

#### Amara (Fashion Shopper) — Browse to Checkout
1. Clicks Instagram link → lands on fashionstore.joat.com
2. Browses new arrivals / collections
3. Selects item → chooses size + color variant
4. Cart persists across session (Redis-backed)
5. Checks out on mobile → order confirmed
6. Store admin notified → picks and packs from existing stock

#### KAFURAHA (Platform Admin) — Operational Flow
1. Logs into platform admin → sees all stores, tenants, health
2. Manages subscriptions, user roles, system settings
3. Reviews platform-wide analytics (orders, revenue per store)
4. Onboards new merchant → creates tenant, assigns domain, sets plan limits

---

## Success Metrics

### User Success Metrics

| User | Success Signal | Measurable Indicator |
|------|---------------|----------------------|
| Tech Shopper | Product found fast | Search-to-cart < 60 seconds |
| Tech Shopper | Frictionless checkout | Cart-to-order < 3 minutes |
| Fashion Shopper | Variant clarity | 0 "wrong size" returns in month 1 |
| Fashion Shopper | Mobile conversion | >60% orders completed on mobile |
| Store Admin | Operational efficiency | Product listed in < 5 minutes |
| Store Admin | Order management | Order actioned within 2 hours of receipt |
| Platform Admin | Tenant onboarding | New store live within 24 hours of signup |

---

### Business Objectives

#### 90-Day (Launch Phase)
- Both stores live and processing real transactions
- Existing stock fully catalogued and searchable online
- Zero downtime to existing VPS services during launch
- First 50 online orders fulfilled successfully
- Platform admin dashboard operational

#### 6-Month (Growth Phase)
- Combined monthly online revenue > physical walk-in equivalent
- Customer account retention rate > 40% (repeat purchases)
- 1 additional merchant onboarded as proof-of-SaaS-concept
- Celery async jobs (order emails, inventory sync) running reliably
- Automated daily backups confirmed operational

#### 12-Month (Scale Phase)
- 3+ active merchant tenants on the platform
- Monthly Recurring Revenue (MRR) from SaaS subscriptions established
- Platform cost-per-tenant < $15/month (infra efficiency)
- Investor-ready metrics dashboard live
- AI engine placeholder integrated with first recommendation feature

---

### Key Performance Indicators

#### Commerce KPIs (Per Store)
| KPI | Target (Month 3) | Target (Month 12) |
|-----|-----------------|-------------------|
| Monthly Orders | 50+ | 300+ |
| Average Order Value | Baseline established | +15% vs baseline |
| Cart Abandonment Rate | < 70% | < 55% |
| Order Fulfilment Time | < 48 hours | < 24 hours |
| Customer Return Rate | — | > 30% |

#### Platform KPIs (SaaS Layer)
| KPI | Target (Month 6) | Target (Month 12) |
|-----|-----------------|-------------------|
| Active Tenants | 2 (own stores) | 5+ |
| MRR | $0 (internal) | $500+ |
| Tenant Onboarding Time | < 24 hours | < 4 hours |
| API Uptime | 99.5% | 99.9% |
| Avg API Response Time | < 300ms | < 150ms |

#### Investor-Facing Metrics
- **TAM Signal:** Demonstrate platform powers N stores on single infra
- **Unit Economics:** Cost per tenant vs revenue per tenant
- **Retention:** Merchant churn rate < 5% monthly
- **Scalability Proof:** Load test showing 10x tenant capacity on same VPS
- **Growth Rate:** Month-over-month GMV growth across all tenants

---

## MVP Scope

### Core Features (90-Day Build — What We're Building)

#### Backend — Django + DRF (ecommerce-core)
- [x] Custom User model with role hierarchy (Platform Admin, Store Owner,
      Store Manager, Customer)
- [x] Store (Tenant) model with domain mapping
- [x] Store-resolution middleware (domain header + X-Store-ID fallback)
- [x] JWT authentication (access + refresh tokens, short-lived)
- [x] Per-store query isolation enforced at queryset level
- [x] Apps: core, users, stores, products, inventory, cart, orders, payments
- [x] Product + ProductVariant + ProductAttribute models
- [x] Inventory tracking per store
- [x] Cart (store-isolated, Redis-backed persistence)
- [x] Order lifecycle (created → confirmed → fulfilled → completed)
- [x] Payment record model (provider-agnostic scaffold)
- [x] Soft deletes + audit fields on all business models
- [x] DRF permission classes (store-scoped)
- [x] Rate limiting (DRF throttle classes)
- [x] Structured logging
- [x] Healthcheck endpoint (/health/)
- [x] Django Admin (platform-level + store-scoped visibility)
- [x] Celery worker + beat (order notifications, async tasks)
- [x] Redis (cache + Celery broker)

#### Supplier Communication Module (MVP Inclusion)
- [x] Supplier model (name, contact, email, product lines)
- [x] InventoryAlert model (threshold, status, supplier linkage)
- [x] Automatic low-stock detection via Celery beat task
- [x] Supplier notification system (email via Celery async task)
- [x] Restock request record (requested qty, status, supplier response)
- [x] Store admin view: stock alert dashboard per store
- [x] n8n webhook integration point (for supplier automation workflows)

#### SaaS Scaffold (Architecture Only — No Billing Yet)
- [x] StoreSubscription model
- [x] Plan model (Basic / Growth / Pro) with feature flags
- [x] Usage limits scaffold (product limit, staff limit, orders/month)
- [x] Stripe webhook endpoint scaffold (no live integration)

#### AI Engine Placeholder
- [x] ai_engine/ app created with extension point stubs
- [x] No logic implemented — architecture only

#### Frontend — Next.js (2 Storefronts)
- [x] tech-store storefront (product catalog, cart, checkout, account)
- [x] fashion-store storefront (collection browse, variant selector,
      mobile-optimized checkout)
- [x] Shared component library (ProductCard, CartDrawer, CheckoutForm)
- [x] Store theme system (per-store config)
- [x] API abstraction layer (store-aware fetch client)
- [x] JWT token handling (httpOnly cookies)
- [x] Guest checkout + account checkout
- [x] Cart persistence (Redis-backed via API)

#### Infrastructure
- [x] Docker Compose (ecommerce-core, redis, celery, celery-beat,
      tech-store, fashion-store)
- [x] Internal Docker network (no external port exposure except proxy)
- [x] Nginx config blocks (api.domain.com, techstore.com,
      fashionstore.com)
- [x] Non-root Docker containers
- [x] Environment variable validation on startup
- [x] Wait-for-db startup pattern
- [x] PostgreSQL on isolated database (new DB, not existing)
- [x] Volume management (db data, media, static)
- [x] Production Django settings structure
- [x] Gunicorn configuration

---

### Out of Scope for MVP

| Feature | Reason Deferred | Target Phase |
|---------|----------------|--------------|
| Live Stripe SaaS billing | Architecture scaffolded; integration requires merchant contracts | Month 4–6 |
| Mobile app (iOS/Android) | Web-first; mobile browser optimized at launch | Post-Series A |
| Multi-currency support | Single currency per store at launch | Month 4 |
| Multi-language / i18n | English first; framework supports extension | Month 5 |
| Advanced analytics dashboard | Basic order metrics only at launch | Month 4 |
| AI recommendations (live) | Placeholder app created; no ML logic | Month 6+ |
| Marketplace / multi-vendor | Single vendor per store at launch | Year 2 |
| Load balancer / horizontal scale | Single VPS sufficient for MVP load | When MRR justifies infra spend |
| Supplier EDI / portal login | Email-based comms at launch | Month 4 |
| Product reviews / ratings | Nice-to-have, not core journey | Month 4 |

---

### 90-Day Build Roadmap

#### Month 1 — Foundation (Days 1–30)
**Goal:** Working multi-tenant API, Docker infra, zero conflicts with existing VPS

| Week | Deliverable |
|------|------------|
| W1 | Repo structure, Docker Compose, VPS isolation audit, Nginx config |
| W2 | Django project: core, users, stores apps + tenant middleware |
| W3 | Products, inventory, cart apps + store isolation enforcement |
| W4 | Orders, payments scaffold, JWT auth, admin panel |

**Gate:** API returns store-isolated product data. Two tenants resolve correctly
by domain. Existing VPS services unaffected.

---

#### Month 2 — Commerce Features (Days 31–60)
**Goal:** Full shopping flow working end-to-end on both storefronts

| Week | Deliverable |
|------|------------|
| W5 | tech-store Next.js frontend: catalog, product detail, cart |
| W6 | fashion-store Next.js frontend: collections, variants, mobile UX |
| W7 | Checkout flow, payment record creation, order confirmation emails (Celery) |
| W8 | Redis cart persistence, account creation, order history + supplier alert system |

**Gate:** Daniel can buy a gadget. Amara can buy clothing in her size.
Order confirmation email received within 60 seconds. Low-stock alert
triggers supplier notification email automatically.

---

#### Month 3 — Harden & Launch (Days 61–90)
**Goal:** Production-ready, monitored, backed up, investor-demonstrable

| Week | Deliverable |
|------|------------|
| W9 | Security hardening: CORS, rate limiting, secure cookies, env validation |
| W10 | SaaS subscription scaffold, StoreSubscription model, Plan model |
| W11 | AI engine placeholder, structured logging, healthchecks, n8n supplier webhook |
| W12 | Load testing, backup strategy, deployment checklist, go-live |

**Gate:** Both stores live. Platform admin dashboard operational.
Investor demo: onboard 3rd tenant in under 24 hours.

---

### MVP Success Criteria (Go/No-Go Gates)

| Gate | Criteria | Decision |
|------|----------|----------|
| Technical | API serves 2 isolated stores correctly | Proceed to frontend |
| Commerce | End-to-end order flow working on both stores | Proceed to hardening |
| Supplier | Low-stock event triggers supplier email automatically | Proceed to launch |
| Security | Pen-test checklist passed, cross-tenant access blocked | Proceed to launch |
| Business | 50 orders processed, 0 critical bugs | Proceed to SaaS phase |
| Investor | Live demo: 3rd tenant onboarded in < 24 hours | Proceed to fundraise |

---

### Future Vision (Post-MVP)

**6–12 Months:**
- Live Stripe SaaS billing — charge merchants subscription fees
- Merchant self-service onboarding portal
- Advanced analytics per store (revenue, funnel, cohorts)
- AI product recommendations (first model: collaborative filtering)
- Multi-currency per store
- Supplier portal login (self-service restock confirmations)

**Year 2:**
- Mobile app (React Native, shared API)
- Marketplace mode (multi-vendor per store)
- White-label option for agencies
- Horizontal scaling with managed Postgres + Redis cluster
- Expand to 50+ tenants on distributed infra

**The Platform Vision:**
joat_stores becomes the infrastructure layer for independent commerce in
emerging markets — the Shopify alternative built for operators who want
ownership, not rent.
