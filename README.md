# joat_stores


> **A multi-tenant, AI-augmented, headless commerce operating system designed to empower African SMEs with scalable digital retail infrastructure.**

---

## What This Is

joat_stores is **commerce infrastructure** — a self-hosted, **B2B2C** multi-tenant headless commerce engine.

The platform operator (you) hosts the infrastructure. Store owners (SMEs) launch branded online stores on top. Customers purchase from those stores. Each layer is fully isolated:

- **B (Business — Store Owners)** → Manage products, orders, staff, subscriptions
- **B (Platform — You)** → Provision stores, set pricing, monitor across tenants
- **C (Customers)** → Browse storefronts, order, pay via M-Pesa, earn loyalty points

Built for Kenyan merchants first. Designed to scale across Africa.

---

## Why It Exists

| The Problem | The Reality |
|---|---|
| Shopify pricing | $79–$299/month per store — unviable for African SMEs |
| WooCommerce | Too technical, no multi-tenancy, no headless-first design |
| Instagram DMs + WhatsApp | No inventory, no analytics, no real checkout |
| Custom builds | Months of engineering, no scaling path, no shared infra |
| Payment integrations | M-Pesa is an afterthought on Western platforms |

joat_stores solves all five simultaneously.

---

## Core Identity

One Django backend powers N independent storefronts via domain-based tenant resolution. Each store is fully isolated at the query, auth, and data levels. Next.js frontends are independently deployable per brand. The platform runs on your own infrastructure — zero per-store SaaS fees, zero vendor lock-in.

```
[techstore.joat.com]   [fashionstore.joat.com]   [merchant3.com]   ...N stores
        ↓                        ↓                        ↓
  ███████████████████████████████████████████████████████████████
  █              joat_stores API (Django + DRF)                  █
  █  Tenant Resolver → Auth → Commerce → Analytics → AI         █
  ███████████████████████████████████████████████████████████████
        ↓                        ↓                        ↓
  [PostgreSQL]              [Redis]               [Celery]
```

---

## Feature Overview

### 🏗 Multi-Tenant Platform Core

- Domain-based store resolution middleware
- Full tenant isolation at queryset, serializer, and permission layers
- No cross-tenant data access — enforced at every layer
- Store configuration and theme customization per tenant
- Feature flags tied to subscription plan
- Subscription tier enforcement (Basic / Growth / Pro)
- Platform Admin panel with full multi-store visibility

### 🎨 Theme Engine (Shopify-Level Storefront Theming)

Every store gets a fully customizable theme without touching code:

- **Design Token System** — 30+ CSS custom properties (colors, typography, spacing, border radius, shadows)
- **5 Preset Packs** — Modern, Classic, Minimal, Bold, Vibrant — apply with one click
- **Layout Templates** — 3 header variants (Centered, Split, Minimal) + 3 footer variants (Columns, Simple, Minimal), mapped per preset
- **Custom CSS Injection** — merchant-written CSS injected at runtime via inline `<style>`
- **Announcement Bar** — toggleable banner with custom text and accent colour
- **Admin Theme Config Page** — full visual editor at `/settings` with colour pickers, font dropdowns, live preview button
- **REST API** — `GET/PATCH /themes/`, `GET /themes/presets/`, `POST /themes/apply-preset/`

### 🛒 Commerce Engine (B2B2C Customer Purchases)

**Products**
- Product catalog with categories, attributes, and variants
- Dynamic attribute system (size, colour, material — per store)
- SKU management and inventory tracking
- Media management (images per variant)
- Soft delete system with audit fields

**Orders**
- Full order lifecycle: created → confirmed → fulfilled → completed
- Denormalized `items_snapshot` (JSON) — no separate line-items table
- Status transitions with timestamps
- Payment confirmation hooks
- Refund handling
- Delivery tracking integration-ready

**Cart**
- Store-isolated, Redis-backed persistent cart
- Guest cart and authenticated cart merge
- Coupon and discount support
- Abandoned cart tracking

### 💳 Payments

- **M-Pesa integration** (primary — STK Push, C2B, B2C)
- Card payments (provider-agnostic scaffold - Story 2.6)
- Webhook verification and idempotency
- Payment records with provider reference tracking
- Fraud detection logic scaffold
- *Future:* Wallet system, store credit, split payments

### 👥 Users & Roles (B2B2C)

| Role | Scope | B2B2C Layer |
|---|---|---|
| Platform Admin | Full platform — all stores, all tenants | Platform |
| Store Owner | Single store — full access | Business |
| Store Manager | Single store — operational access | Business |
| Customer | Store-scoped — own orders and profile | Consumer |

- JWT authentication (short-lived access + refresh tokens)
- Object-level permission enforcement
- Feature access gated per subscription plan
- `IsStoreManager` + `HasStore` permission classes replace manual store checks

### 📊 Analytics Engine (Core Differentiator)

**Store-Level Analytics**

| Category | Metrics |
|---|---|
| Sales | Revenue (daily/weekly/monthly), trend graph, AOV, top products, top categories |
| Customers | Growth rate, LTV, purchase frequency, geographic distribution, repeat rate |
| Products | Best sellers, underperforming products, low stock alerts, inventory turnover |
| Conversion | Cart abandonment rate, checkout completion rate, payment success rate |

**Platform-Level Analytics (SaaS Admin)**

- Total stores and active subscriptions
- MRR (Monthly Recurring Revenue)
- Platform GMV (Gross Merchandise Volume)
- Store churn rate
- Revenue per subscription tier
- Feature usage tracking

All analytics read from pre-aggregated `DailyRevenueSummary` + `HourlyOrderSummary` — never live ORM aggregates.

### 🤖 AI Engine (Architecture-Ready)

| Module | Capability |
|---|---|
| Recommendation Engine | Collaborative filtering, "customers also bought," cross-sell |
| Dynamic Pricing | Sales velocity-based pricing suggestions, demand forecasting |
| Inventory Forecasting | Predict stock-outs, suggest reorder quantities |
| Customer Segmentation | High-value, at-risk churn, discount-sensitive buyer segments |

### 🍽️ Restaurant Module

- Digital menu management with sections, modifiers, modifier groups
- Public menu URL (QR-code friendly)
- HMAC-signed QR table tokens (anti-tamper)
- TableSession state machine with waiter assignment
- Dine-in ordering: customer scans → browses → orders → pays at table
- Kitchen ticket generation (denormalized, printer-ready)
- PendingOrder — waiter intermediary screen
- Pre-order with advance M-Pesa payment
- Reservation booking
- Takeaway order type
- Bill split (shared, percentage, item-level)
- Age-restricted item flagging (FR4 cross-epic tenant-type lock)

### 🍸 Bar Module

- Open/close tab state machine
- Round ordering (multiple drinks on one tab)
- Happy-hour pricing with time-window snapshots
- Age-restricted item enforcement + AgeRestrictionLog
- Tab split settlement via M-Pesa

### 🔧 Contracting Module

- Service catalog per store (contracting tenant-type)
- Service booking with availability calendar
- Quote request → quote acceptance/rejection workflow
- Job milestones with completion photos
- Invoice generation with WhatsApp-shareable PDF
- Invoice payment collection

### ⚡ Async & Background Jobs (Celery + Redis)

Dedicated queues: `order.notifications`, `inventory.alerts`, `billing.reminders`, `payments.reconciliation`, `analytics.reports`

- Order confirmation emails
- Low-stock alert detection and supplier notifications
- Inventory sync tasks
- Scheduled reporting (daily/hourly aggregation)
- Dead-letter queue + exponential backoff retry
- Worker health monitoring endpoint

### 🔒 Security

- JWT + httpOnly secure cookies
- Role-based access control (RBAC) via JWT `role` claim — never `is_staff`/`is_superuser`
- Explicit `permission_classes` on every view — no DRF defaults relied upon
- Request throttling (per-store plan-based rate limits)
- CORS restrictions with domain whitelist
- Encrypted secrets via environment variables
- Structured audit logging (`AdminPIIAccessLog`)
- OWASP Top 10 + Kenya DPA 2019 compliance

### 🏪 Supplier Communication Module

- Supplier model with contact and product line linkage
- Inventory alert thresholds per product per store
- Automatic low-stock detection via Celery Beat
- Supplier notification emails (async)
- Restock request records with status tracking

### 💳 SaaS Subscription Management

- Plan model with feature flags and resource limits (Basic / Growth / Pro)
- StoreSubscription lifecycle: trial → active → past_due → suspended → cancelled
- M-Pesa subscription renewal
- Automated suspension + PII anonymisation on cancellation
- Plan limit enforcement at API layer

### 🎯 Customer Loyalty & Engagement

- Points-based loyalty accounts with transaction history
- Stamp cards — automatic reward on threshold
- WhatsApp notification dispatch
- Unified customer profile (RFM segmentation)
- WhatsApp ordering bridge

### 🐳 Infrastructure

- Docker Compose (Django, Postgres, Redis, Celery, Celery Beat, Flower, Nginx)
- Internal Docker network — no external port exposure except Nginx proxy
- Nginx reverse proxy with per-store domain config
- Non-root containers, environment variable validation on startup
- PostgreSQL with volume management
- Redis AOF persistence
- Health check endpoint (`/health/`)
- Gunicorn + Uvicorn with production Django settings

---

## SaaS Monetization

| Plan | Products | Staff | Analytics | AI | Price |
|---|---|---|---|---|---|
| Basic | 50 | 1 | Basic | — | Affordable |
| Growth | 500 | 5 | Advanced | — | Mid-tier |
| Pro | Unlimited | Unlimited | Full | ✓ | Premium |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Django 5.2 LTS + Django REST Framework |
| Frontend | Next.js 16.x App Router (TypeScript strict) |
| Database | PostgreSQL 17.x |
| Cache / Sessions | Redis 8.6 |
| Async Jobs | Celery 5.6.2 + Celery Beat |
| Proxy | Nginx |
| Containerization | Docker + Docker Compose |
| Auth | JWT (simplejwt + custom store_id claim) |
| Payments | M-Pesa (Daraja API), card scaffold |

---

## Roadmap (Status: June 2026)

**Phase 1 — MVP ✅ (Month 1–3)**
- Multi-store engine live with 2+ tenant storefronts
- M-Pesa payments operational (retail + F&B)
- Basic analytics dashboard
- Restaurant dine-in + bar tab live
- Platform admin operational
- Third tenant onboarded in < 24 hours (investor demo)

**Phase 2 — Theme Engine + Security ✅ (Month 3–5)**
- Full theme customization (design tokens, 5 presets, 3 header/3 footer variants)
- Admin theme config page at `/settings`
- Security audit: explicit permission classes on all 37+ views across 6 apps
- Custom CSS injection + announcement bar
- `seed_demo` fixed, Docker ports exposed, TenantMiddleware hardened

**Phase 3 — Scale (Next)**
- Multi-provider card payments (Stripe/Flutterwave)
- Self-service merchant onboarding
- AI engine to production (trained recommendation model)
- POS integration
- Wallet system + store credit
- 5+ active merchant tenants

---

## Target Market

Kenyan SMEs ready to move from Instagram DMs and WhatsApp orders to real, owned, analytics-driven digital commerce:

- Fashion retailers and clothing boutiques
- Electronics and accessories sellers
- Instagram / TikTok sellers going multi-channel
- Physical shops transitioning online
- Portfolio operators running multiple brands
- Restaurants and bars replacing manual operations with digital infrastructure

---

## Strategic Goal

Build the **Kenyan-first multi-vertical commerce operating system** — retail, restaurants, and bars on a single platform — optimized for local payments, mobile-first UX, African-market pricing, and AI-powered growth intelligence.

Not just stores. Infrastructure.

---

## Future Recommendations

### 🎯 Product
- **Multi-provider card payments (Story 2.6)** — integrate Stripe or Flutterwave for card payments (currently a 501 scaffold)
- **Wallet system** — store credit, split payments, customer wallets
- **POS integration** — connect physical POS terminals with online inventory
- **Marketplace mode** — allow third-party vendors to sell on a store's platform
- **Self-service onboarding** — merchant registration without platform admin intervention
- **SSE real-time kitchen updates** — push updates to restaurant displays

### 🛠️ Engineering
- **End-to-end test suite** — Playwright or Cypress for critical checkout paths
- **Rate limit by subscription tier** — enforce plan-based API throttling limits
- **Horizontal scaling** — separate read replicas, Celery worker autoscaling
- **Full-text search** — Elasticsearch or Meilisearch for product search beyond PostgreSQL SearchVector
- **WebSocket support** — real-time order status updates for customer dashboard

### 🤖 AI (Scaffold → Production)
- **Train recommendation model** — move from collaborative-filtering scaffold to a trained model with real customer data
- **Dynamic pricing engine** — sales velocity and demand-based price suggestions
- **Inventory forecasting** — predict stock-outs and suggest reorder quantities
- **Customer segmentation** — RFM-based cohorts with automated marketing triggers

### 🚀 Go-to-Market
- **Production deployment** — deploy to Render + Vercel (configs in `render.yaml`)
- **Seed with real merchants** — onboard 2–3 pilot stores
- **Landing page** — joatstores.com with merchant signup
- **Demo environment** — public demo store with sample data

---

## Project Development Progress

> **Status:** MVP + Theme Engine (Phase 1–3) + Security Hardening **complete** (2026-06-20). All 12 MVP epics (83 stories) implemented, plus full theme customization system (design tokens, 5 presets, layout variants, custom CSS, announcement bar, admin config page) and security audit (explicit permission classes on 37+ views across 6 apps). B2B2C tenant model fully operational.

### Phase 0 — Planning & Architecture

| Artifact | Status | Location |
|---|---|---|
| Product Brief | ✅ Complete | `_bmad-output/planning-artifacts/product-brief-joat_stores-2026-02-23.md` |
| Product Requirements Document (PRD) | ✅ Complete | `_bmad-output/planning-artifacts/prd.md` |
| Architecture Decision Document | ✅ Complete | `_bmad-output/planning-artifacts/architecture.md` |
| UX Design Specification | ✅ Complete | `_bmad-output/planning-artifacts/ux-design-specification.md` |
| Epics & User Stories | ✅ Complete | `_bmad-output/planning-artifacts/epics.md` |
| Project Context for AI Agents | ✅ Complete | `_bmad-output/project-context.md` |
| Implementation Readiness Report | ✅ Complete — READY | `_bmad-output/planning-artifacts/implementation-readiness-report-2026-03-03.md` |

**Planning scope:** 101 functional requirements, 22 non-functional requirements, 83 user stories across 12 epics, 7 user journeys.

### Architecture Decisions Locked

| Decision | Choice |
|---|---|
| Backend | Django 5.2 LTS + DRF + Python 3.14.3 |
| Frontend | Next.js 16.x App Router (TypeScript strict) |
| Multi-tenancy | Shared DB, shared schema — store_id FK isolation at 5 layers |
| Payments | M-Pesa Daraja STK Push (primary rail across all verticals) |
| Auth | djangorestframework-simplejwt + custom store_id JWT claim |
| Async | Celery 5.6.2 + Redis 8.6 + DLQ from day one |
| Deployment | Docker Compose on VPS — no Kubernetes at MVP |
| CI/CD | GitHub Actions — lint + test + SSH deploy on merge to main |

### Implementation Progress

| Epic | Scope | Stories | Status |
|---|---|---|---|
| Epic 1 | Multi-Tenant Platform Foundation + Auth | 9 | ✅ Done |
| Epic 2 | Multi-Provider Payments Engine (M-Pesa) | 6 | ✅ Done |
| Epic 3 | Restaurant Full-Service | 13 | ✅ Done |
| Epic 4 | Retail Store Commerce | 10 | ✅ Done |
| Epic 5 | Bar Tab Management | 5 | ✅ Done |
| Epic 6 | Contracting Module | 6 | ✅ Done |
| Epic 7 | Reliable Async Operations (Celery) | 4 | ✅ Done |
| Epic 8 | Merchant Analytics Dashboard | 7 | ✅ Done |
| Epic 9 | SaaS Plans + Subscription Management | 7 | ✅ Done |
| Epic 10 | Customer Loyalty + Engagement | 6 | ✅ Done |
| Epic 11 | AI + Personalization | 3 | ✅ Done |
| Epic 12 | Production Hardening | 6 | ✅ Done |

**Total: 82 stories implemented across 12 epics. Story 2.6 (multi-provider card routing) deferred to Phase 2.**

#### Epic 1: Multi-Tenant Platform Foundation + Auth

| Story | Description | Status |
|---|---|---|
| 1.1 | Monorepo scaffold + app bootstrapping | ✅ Done |
| 1.1b | Docker Compose — all services + Celery baseline | ✅ Done |
| 1.1c | Minimal CI pipeline — linting + tests on PR | ✅ Done |
| 1.2 | Core Store model + TenantMiddleware | ✅ Done |
| 1.3 | Tenant isolation layers (queryset, serializer, permissions, admin, pagination) | ✅ Done |
| 1.4 | Atomic store provisioning API + SaaS stubs | ✅ Done |
| 1.5 | JWT auth + RBAC (4 roles) | ✅ Done |
| 1.6 | PII audit log + OpenAPI schema | ✅ Done |
| 1.7 | Storefront Next.js shell + tenant branding | ✅ Done |
| 1.8 | Admin Next.js shell + authenticated layout | ✅ Done |

#### Epic 2: Multi-Provider Payments Engine

| Story | Description | Status |
|---|---|---|
| 2.0 | Phone number normalization + validation service | ✅ Done |
| 2.1 | Daraja client — OAuth token cache | ✅ Done |
| 2.2 | M-Pesa STK Push initiation + idempotency | ✅ Done |
| 2.3 | Daraja webhook processing + receipt idempotency | ✅ Done |
| 2.4 | STK Push timeout — expired status | ✅ Done |
| 2.5 | Payment reconciliation + reversal | ✅ Done |
| 2.6 | Multi-provider card routing | Deferred to Phase 2 |

#### Epic 3: Restaurant Full-Service

| Story | Description | Status |
|---|---|---|
| 3.1 | Menu management API | ✅ Done |
| 3.2 | Public menu URL | ✅ Done |
| 3.3 | HMAC QR table token generation + validation | ✅ Done |
| 3.4 | Table + TableSession state machine + waiter assignment | ✅ Done |
| 3.5 | QR scan errors + wrong-table guard | ✅ Done |
| 3.6 | Dine-in order + denormalized kitchen ticket | ✅ Done |
| 3.6b | Customer dine-in order confirmation + live status screen | ✅ Done |
| 3.7 | PendingOrder waiter convert screen | ✅ Done |
| 3.8 | Pre-order + advance payment | ✅ Done |
| 3.9 | Reservation model | ✅ Done |
| 3.10 | Takeaway order type | ✅ Done |
| 3.11 | Restaurant bill payment + split bill | ✅ Done |
| 3.12 | FR4 cross-epic tenant-type lock test | ✅ Done |

#### Epic 4: Retail Store Commerce

| Story | Description | Status |
|---|---|---|
| 4.1 | Product catalog — categories, variants, inventory, images | ✅ Done |
| 4.2 | Redis cart — 30-day TTL, guest + auth | ✅ Done |
| 4.3 | Order lifecycle state machine | ✅ Done |
| 4.3b | Merchant daily-view + zero-navigation dashboard | ✅ Done |
| 4.4 | Guest checkout + M-Pesa payment | ✅ Done |
| 4.5 | Google OAuth2 PKCE — authenticated checkout | ✅ Done |
| 4.6 | Order confirmation email + low-stock alerts | ✅ Done |
| 4.7 | Card payment scaffold | ✅ Done |
| 4.8 | Post-payment browser recovery | ✅ Done |
| 4.9 | In-app browser detection + cart fallback | ✅ Done |

#### Epic 5: Bar Tab Management

| Story | Description | Status |
|---|---|---|
| 5.1 | Bar tenant-type activation + tab state machine | ✅ Done |
| 5.2 | Round ordering on open tab | ✅ Done |
| 5.3 | Age-restricted items + AgeRestrictionLog | ✅ Done |
| 5.4 | Happy-hour pricing snapshot | ✅ Done |
| 5.5 | Tab split settlement via M-Pesa | ✅ Done |

#### Epic 6: Contracting Module

| Story | Description | Status |
|---|---|---|
| 6.1 | Contracting tenant-type + service catalog | ✅ Done |
| 6.2 | Service booking + availability calendar | ✅ Done |
| 6.3 | Quote request + quote acceptance | ✅ Done |
| 6.4 | Job milestones + completion photos | ✅ Done |
| 6.5 | Invoice generation + WhatsApp-shareable PDF | ✅ Done |
| 6.6 | Invoice payment collection | ✅ Done |

#### Epic 7: Reliable Async Operations

| Story | Description | Status |
|---|---|---|
| 7.1 | DLQ + exponential backoff hardening on all tasks | ✅ Done |
| 7.2 | Celery Beat — full schedule | ✅ Done |
| 7.3 | Worker health endpoint | ✅ Done |
| 7.4 | Celery Flower — production config | ✅ Done |

#### Epic 8: Merchant Analytics Dashboard

| Story | Description | Status |
|---|---|---|
| 8.1 | Pre-aggregated summary models + daily generation | ✅ Done |
| 8.2 | AIEvent append-only capture | ✅ Done |
| 8.3 | Per-store analytics API | ✅ Done |
| 8.4 | Restaurant analytics — peak hours + table turn rate | ✅ Done |
| 8.5 | Bar analytics | ✅ Done |
| 8.6 | Platform analytics — TenantHealthSnapshot | ✅ Done |
| 8.7 | First-order milestone + investor demo moment | ✅ Done |

#### Epic 9: SaaS Plans + Subscription Management

| Story | Description | Status |
|---|---|---|
| 9.1 | Plan model (feature flags + resource limits) | ✅ Done |
| 9.2 | StoreSubscription lifecycle state machine | ✅ Done |
| 9.3 | M-Pesa subscription renewal | ✅ Done |
| 9.4 | Plan limit enforcement | ✅ Done |
| 9.5 | AI scaffold — 501 endpoints | ✅ Done |
| 9.6 | Merchant onboarding runbook | ✅ Done |
| 9.7 | Automated subscription suspension + PII anonymisation pipeline | ✅ Done |

#### Epic 10: Customer Loyalty + Engagement

| Story | Description | Status |
|---|---|---|
| 10.1 | LoyaltyAccount — points balance + history | ✅ Done |
| 10.2 | StampCard — auto-reward on threshold | ✅ Done |
| 10.3 | WhatsApp notification dispatch | ✅ Done |
| 10.4 | Unified customer account (CustomerProfile RFM) | ✅ Done |
| 10.5 | WhatsApp ordering bridge | ✅ Done |
| 10.6 | "Powered by joat stores" viral footer | ✅ Done |

#### Epic 11: AI + Personalization

| Story | Description | Status |
|---|---|---|
| 11.1 | Recommendation engine (collaborative filtering) | ✅ Done |
| 11.2 | Peak-hour predictions (7-day moving average) | ✅ Done |
| 11.3 | NLP menu search (PostgreSQL SearchVector) | ✅ Done |

#### Epic 12: Production Hardening

| Story | Description | Status |
|---|---|---|
| 12.1 | GitHub Actions CI/CD pipeline + SSH deploy | ✅ Done |
| 12.2 | Daily backup — Redis AOF persistence + pg_dump | ✅ Done |
| 12.3 | OWASP Top 10 + Kenya DPA 2019 compliance | ✅ Done |
| 12.4 | Sentry + structlog full integration | ✅ Done |
| 12.5 | Store admin PWA — offline inventory | ✅ Done |
| 12.6 | Data export — merchant daily view (CSV) | ✅ Done |

### Planning Artifacts

- [x] Product Brief
- [x] Market & domain research
- [x] PRD (101 FRs, 22 NFRs)
- [x] UX Design Specification
- [x] Architecture
- [x] Epics & Stories (83 stories, 12 epics)
- [x] Implementation readiness verification
- [x] OWASP Top 10 + Kenya DPA 2019 compliance checklist (`_bmad-output/implementation-artifacts/12-3-owasp-dpa-compliance-checklist.md`)
- [x] Merchant onboarding runbook (`_bmad-output/implementation-artifacts/9-6-merchant-onboarding-runbook.md`)

---

*Built by KAFURAHA*
